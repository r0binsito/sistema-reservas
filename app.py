import os
import re
import secrets
import ssl
import certifi
from datetime import datetime, time, date, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

import pytz
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from sqlalchemy import func, desc
from flask import Flask, request, redirect, url_for, render_template, session, flash, g, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized, oauth_error
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail

from models import db, Negocio, Cliente, Reserva, Usuario, Horario, Servicio

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

app = Flask(__name__)
# Solo aplicar ProxyFix en producción (Railway)
if os.getenv("RAILWAY_ENVIRONMENT"):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

database_url = os.getenv("DATABASE_URL", "sqlite:///reservas.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "reserfy-dev-key-2026")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False
app.config["WTF_CSRF_ENABLED"] = False  # ← AQUÍ

# Google OAuth
if not os.getenv("RAILWAY_ENVIRONMENT"):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

base_url = os.getenv("BASE_URL", "http://localhost:5000")
redirect_url = f"{base_url}/auth/google/authorized"

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_url=redirect_url
)

@app.before_request
def forzar_estado_oauth():
    if request.endpoint == 'google.authorized':
        if 'google_oauth_state' not in session:
            session['google_oauth_state'] = request.args.get('state', '')

app.register_blueprint(google_bp, url_prefix="/auth")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

@app.context_processor
def inject_plan_info():
    if current_user.is_authenticated:
        negocio = current_user.negocio
        plan = negocio.plan or "trial"
        limites = get_limites(negocio)

        # Calcular uso actual
        from datetime import timezone
        inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, tzinfo=None)

        uso = {
            "reservas_mes": Reserva.query.filter(
                Reserva.negocio_id == negocio.id,
                Reserva.fecha_hora >= inicio_mes,
                Reserva.estado != "cancelada"
            ).count(),
            "clientes": Cliente.query.filter_by(negocio_id=negocio.id).count(),
            "servicios": Servicio.query.filter_by(negocio_id=negocio.id, activo=True).count(),
        }

        trial_expirado = False
        dias_restantes = None
        if plan == "trial" and negocio.trial_expira:
            delta = negocio.trial_expira.replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)
            if delta.days < 0:
                trial_expirado = True
            else:
                dias_restantes = delta.days

        return dict(
            plan_actual=plan,
            plan_limites=limites,
            plan_uso=uso,
            trial_expirado=trial_expirado,
            dias_restantes=dias_restantes
        )
    return dict(
        plan_actual=None,
        plan_limites=None,
        plan_uso=None,
        trial_expirado=False,
        dias_restantes=None
    )


def get_dashboard_stats(negocio_id):
    """Obtiene estadísticas avanzadas para el dashboard según el plan."""
    # Obtener el negocio para usar su timezone
    negocio = db.session.get(Negocio, negocio_id)
    tz_negocio = pytz.timezone(negocio.timezone) if negocio else pytz.utc

    # Fecha/hora actual en timezone del negocio
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz_negocio).replace(tzinfo=None)

    # Inicio del mes actual (en timezone del negocio, convertido a UTC para comparar)
    inicio_mes_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_utc = tz_negocio.localize(inicio_mes_local).astimezone(pytz.utc).replace(tzinfo=None)

    # Inicio del mes anterior
    if now_local.month == 1:
        inicio_mes_anterior_local = now_local.replace(year=now_local.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        inicio_mes_anterior_local = now_local.replace(month=now_local.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior_utc = tz_negocio.localize(inicio_mes_anterior_local).astimezone(pytz.utc).replace(tzinfo=None)

    stats = {}

    # === PRÓXIMA CITA DEL DÍA ===
    # Calcular inicio y fin del día actual en timezone del negocio, luego convertir a UTC
    hoy_inicio_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_fin_local = hoy_inicio_local + timedelta(days=1)

    # Convertir a UTC para comparar con la base de datos
    hoy_inicio_utc = tz_negocio.localize(hoy_inicio_local).astimezone(pytz.utc).replace(tzinfo=None)
    hoy_fin_utc = tz_negocio.localize(hoy_fin_local).astimezone(pytz.utc).replace(tzinfo=None)
    now_utc_naive = now_utc.replace(tzinfo=None)

    proxima_reserva = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= now_utc_naive,
        Reserva.fecha_hora < hoy_fin_utc,
        Reserva.estado != "cancelada"
    ).order_by(Reserva.fecha_hora).first()

    if proxima_reserva:
        cliente = db.session.get(Cliente, proxima_reserva.cliente_id)
        # Convertir hora a timezone local para mostrar
        hora_local = pytz.utc.localize(proxima_reserva.fecha_hora).astimezone(tz_negocio)
        stats['proxima_cita'] = {
            'cliente': cliente.nombre if cliente else 'Cliente',
            'hora': hora_local.strftime('%I:%M %p'),
            'servicio': proxima_reserva.servicio
        }
    else:
        stats['proxima_cita'] = None

    # === TASA DE ASISTENCIA (Pro/Elite) ===
    total_reservas = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= inicio_mes_utc,
        Reserva.estado != "cancelada"
    ).count()

    completadas = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= inicio_mes_utc,
        Reserva.estado == "completada"
    ).count()

    if total_reservas > 0:
        stats['tasa_asistencia'] = round((completadas / total_reservas) * 100)
    else:
        stats['tasa_asistencia'] = 100  # Sin reservas = 100%

    # === TOP SERVICIOS (Pro/Elite) ===
    top_servicios = db.session.query(
        Reserva.servicio,
        func.count(Reserva.id).label('total')
    ).filter(
        Reserva.negocio_id == negocio_id,
        Reserva.estado != "cancelada",
        Reserva.fecha_hora >= inicio_mes_utc
    ).group_by(Reserva.servicio).order_by(desc('total')).limit(3).all()

    stats['top_servicios'] = [{'nombre': s[0], 'cantidad': s[1]} for s in top_servicios] if top_servicios else []

    # === CRECIMIENTO DE CLIENTES (Pro/Elite) ===
    clientes_mes_actual = db.session.query(Cliente).filter(
        Cliente.negocio_id == negocio_id
    ).count()

    # Clientes del mes anterior (aproximación)
    clientes_mes_anterior_query = db.session.query(func.count(Reserva.cliente_id.distinct())).filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= inicio_mes_anterior_utc,
        Reserva.fecha_hora < inicio_mes_utc
    )
    clientes_mes_anterior = max(0, clientes_mes_actual - clientes_mes_anterior_query.scalar())

    if clientes_mes_anterior > 0:
        stats['crecimiento_clientes'] = round(((clientes_mes_actual - clientes_mes_anterior) / clientes_mes_anterior) * 100)
    else:
        stats['crecimiento_clientes'] = 0

    # === INGRESOS DEL MES (Elite) ===
    reservas_con_precio = db.session.query(
        Reserva.servicio,
        func.count(Reserva.id).label('cantidad')
    ).filter(
        Reserva.negocio_id == negocio_id,
        Reserva.estado != "cancelada",
        Reserva.fecha_hora >= inicio_mes_utc
    ).group_by(Reserva.servicio).all()

    servicios_precios = {s.nombre: s.precio for s in Servicio.query.filter_by(negocio_id=negocio_id, activo=True).all()}

    ingresos = 0
    for reserva in reservas_con_precio:
        precio = servicios_precios.get(reserva.servicio, 0) or 0
        ingresos += precio * reserva.cantidad

    stats['ingresos_mes'] = ingresos

    # === TICKET PROMEDIO (Elite) ===
    total_reservas_mes = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.estado != "cancelada",
        Reserva.fecha_hora >= inicio_mes_utc
    ).count()

    if total_reservas_mes > 0 and ingresos > 0:
        stats['ticket_promedio'] = round(ingresos / total_reservas_mes)
    else:
        stats['ticket_promedio'] = 0

    # === CITAS HOY ===
    stats['citas_hoy'] = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= hoy_inicio_utc,
        Reserva.fecha_hora < hoy_fin_utc,
        Reserva.estado != "cancelada"
    ).count()

    return stats

def generar_slug(nombre):
    slug = nombre.lower()
    slug = re.sub(r'[áàäâ]', 'a', slug)
    slug = re.sub(r'[éèëê]', 'e', slug)
    slug = re.sub(r'[íìïî]', 'i', slug)
    slug = re.sub(r'[óòöô]', 'o', slug)
    slug = re.sub(r'[úùüû]', 'u', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())

    slug_base = slug[:50]  # limitar longitud
    slug = slug_base
    contador = 1
    while Negocio.query.filter_by(slug=slug).first():
        slug = f"{slug_base}-{contador}"
        contador += 1
        if contador > 100:  # límite de seguridad
            break

    return slug

def hora_local(negocio, fecha_hora_utc):
    tz = pytz.timezone(negocio.timezone)
    if fecha_hora_utc.tzinfo is None:
        fecha_hora_utc = pytz.utc.localize(fecha_hora_utc)
    return fecha_hora_utc.astimezone(tz)



# ===== LÍMITES POR PLAN =====
LIMITES_PLAN = {
    "trial": {
        "reservas_mes": 999,
        "clientes": 999,
        "servicios": 999,
        "estadisticas": True,
        "marca_agua": False,
    },
    "starter": {
        "reservas_mes": 50,
        "clientes": 30,
        "servicios": 3,
        "estadisticas": False,
        "marca_agua": True,
    },
    "pro": {
        "reservas_mes": 999,
        "clientes": 999,
        "servicios": 999,
        "estadisticas": True,
        "marca_agua": True,
    },
    "elite": {
        "reservas_mes": 999,
        "clientes": 999,
        "servicios": 999,
        "estadisticas": True,
        "marca_agua": False,
    },
}

def get_limites(negocio):
    plan = negocio.plan or "trial"
    # Verificar si el trial expiró
    if plan == "trial" and negocio.trial_expira:
        from datetime import datetime, timezone
        # Normalizamos ambas fechas a "naive" (sin tzinfo) para que sean comparables
        ahora = datetime.now(timezone.utc).replace(tzinfo=None)
        expiracion = negocio.trial_expira.replace(tzinfo=None)
        
        if ahora > expiracion:
            return None  # Trial expirado — bloquear
    return LIMITES_PLAN.get(plan, LIMITES_PLAN["starter"])

def verificar_limite(negocio, tipo):
    limites = get_limites(negocio)
    if limites is None:
        return False, "trial_expirado"

    if tipo == "reservas_mes":
        from datetime import datetime
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        count = Reserva.query.filter(
            Reserva.negocio_id == negocio.id,
            Reserva.fecha_hora >= inicio_mes,
            Reserva.estado != "cancelada"
        ).count()
        return count < limites["reservas_mes"], count

    if tipo == "clientes":
        count = Cliente.query.filter_by(negocio_id=negocio.id).count()
        return count < limites["clientes"], count

    if tipo == "servicios":
        count = Servicio.query.filter_by(negocio_id=negocio.id, activo=True).count()
        return count < limites["servicios"], count

    return True, 0

# --- Index ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        # Solo redirigir si NO viene del onboarding
        if not request.args.get('onboarding'):
            return redirect(url_for('dashboard'))
    if request.method == "POST":
        # ... resto igual
        email = request.form["email"]
        password = request.form["password"]

        if Usuario.query.filter_by(email=email).first():
            return render_template("registro.html", error="Ya existe una cuenta con ese email.", paso=1)

        negocio = Negocio(nombre="Mi negocio", email=email)
        negocio.slug = generar_slug(email.split("@")[0])
        db.session.add(negocio)
        db.session.commit()

        usuario = Usuario(
            email=email,
            password_hash=generate_password_hash(password),
            negocio_id=negocio.id
        )
        db.session.add(usuario)
        db.session.commit()

        login_user(usuario)
        return redirect(url_for("elegir_plan"))

    return render_template("registro.html", paso=1,
    plan_elegido=current_user.negocio.plan if current_user.is_authenticated and current_user.negocio.plan not in ['trial', None] else None)

@app.route("/elegir-plan", methods=["GET", "POST"])
@login_required
def elegir_plan():
    if request.method == "POST":
        plan = request.form.get("plan")
        if plan in ["starter", "pro", "elite"]:
            current_user.negocio.plan = plan
            db.session.commit()
        return redirect(url_for("configurar_negocio"))
    return render_template("elegir_plan.html", paso=2)
    

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Email o contraseña incorrectos")

    return render_template("login.html")

@app.route("/recuperar-password", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "POST":
        email = request.form.get("email")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario:
            token = secrets.token_urlsafe(32)
            usuario.reset_token = token
            usuario.reset_token_expira = datetime.utcnow() + timedelta(hours=2)
            db.session.commit()

            link = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reset-password/{token}"

            enviar_email(
                destinatario=email,
                asunto="Recupera tu contraseña — Reserfy",
                contenido_html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #912A5C, #FA8F3E); padding: 2rem; text-align: center; border-radius: 12px 12px 0 0;">
                        <h1 style="color: white; margin: 0;">🔐 Recuperar contraseña</h1>
                    </div>
                    <div style="background: #f8f8f8; padding: 2rem; border-radius: 0 0 12px 12px;">
                        <p>Hola, recibimos una solicitud para recuperar tu contraseña.</p>
                        <p>Haz clic en el botón para crear una nueva contraseña. Este link expira en <strong>2 horas</strong>.</p>
                        <div style="text-align: center; margin: 2rem 0;">
                            <a href="{link}" style="background: linear-gradient(135deg, #912A5C, #FA8F3E); color: white; padding: 1rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 700;">
                                Crear nueva contraseña →
                            </a>
                        </div>
                        <p style="color: #888; font-size: 0.85rem;">Si no solicitaste esto, ignora este email.</p>
                        <p style="color: #aaa; font-size: 0.78rem;">O copia este link: {link}</p>
                    </div>
                </div>
                """
            )

        # Siempre mostrar el mismo mensaje por seguridad
        return render_template("recuperar_password.html",
            mensaje="Si ese email existe, recibirás un link en los próximos minutos.")

    return render_template("recuperar_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    usuario = Usuario.query.filter_by(reset_token=token).first()

    if not usuario or not usuario.reset_token_expira:
        return render_template("reset_password.html", error="Link inválido o expirado.")

    if datetime.utcnow() > usuario.reset_token_expira:
        return render_template("reset_password.html", error="Este link ha expirado. Solicita uno nuevo.")

    if request.method == "POST":
        password = request.form.get("password")
        confirmar = request.form.get("confirmar")

        if password != confirmar:
            return render_template("reset_password.html",
                token=token, error="Las contraseñas no coinciden.")

        if len(password) < 8:
            return render_template("reset_password.html",
                token=token, error="La contraseña debe tener al menos 8 caracteres.")

        usuario.password_hash = generate_password_hash(password)
        usuario.reset_token = None
        usuario.reset_token_expira = None
        db.session.commit()

        return render_template("reset_password.html", exito=True)

    return render_template("reset_password.html", token=token)

# --- Configurar Negocio ---
@app.route("/configurar-negocio", methods=["GET", "POST"])
@login_required
def configurar_negocio():
    negocio = current_user.negocio
    if request.method == "POST":
        negocio.nombre = request.form.get("nombre", "Mi negocio")
        negocio.tipo = request.form.get("tipo")
        tipo_personalizado = request.form.get("tipo_personalizado")
        
        if negocio.tipo == "Otro" and tipo_personalizado:
            negocio.tipo = tipo_personalizado
            
        negocio.eslogan = request.form.get("eslogan")
        negocio.telefono = request.form.get("telefono")
        negocio.direccion = request.form.get("direccion")
        negocio.slug = generar_slug(negocio.nombre)

        # Logo
        logo_recortado = request.form.get("logo_recortado")
        if logo_recortado and logo_recortado.startswith("data:image"):
            try:
                resultado = cloudinary.uploader.upload(
                    logo_recortado,
                    folder="reserfy/logos",
                    public_id=f"negocio_{negocio.id}",
                    overwrite=True,
                    transformation=[{"width": 400, "height": 400, "crop": "fill"}]
                )
                negocio.logo_url = resultado["secure_url"]
            except Exception as e:
                print(f"Error subiendo logo: {e}")

        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("configurar_negocio.html", 
                           paso=3, 
                           negocio=current_user.negocio,
                           plan_elegido=current_user.negocio.plan)


@oauth_error.connect_via(google_bp)
def google_error(blueprint, message, response):
    return redirect(url_for("login"))


@oauth_authorized.connect_via(google_bp)
def google_authorized(blueprint, token):
    if not token:
        return redirect(url_for("login"))

    resp = blueprint.session.get("/oauth2/v1/userinfo")
    if not resp.ok:
        return redirect(url_for("login"))

    info = resp.json()
    email = info["email"]

    usuario = Usuario.query.filter_by(email=email).first()

    if usuario:
        login_user(usuario)
        return redirect(url_for("dashboard"))

    negocio = Negocio(
        nombre=f"Negocio de {info.get('given_name', email.split('@')[0])}", 
        email=email
    )
    negocio.slug = generar_slug(email.split("@")[0])
    db.session.add(negocio)
    db.session.commit()

    usuario = Usuario(
        email=email,
        password_hash=generate_password_hash(os.urandom(24).hex()),
        negocio_id=negocio.id
    )
    db.session.add(usuario)
    db.session.commit()

    login_user(usuario)
    
    return redirect(url_for("elegir_plan"))

# --- Dashboard protegido ---
@app.route("/dashboard")
@login_required
def dashboard():
    negocio = current_user.negocio

    # Verificar si el onboarding acaba de completarse
    onboarding_just_completed = session.pop('onboarding_just_completed', False)

    # Verificar si faltan configuraciones básicas (para el modal de onboarding)
    faltan_horarios = Horario.query.filter_by(negocio_id=negocio.id).count() == 0
    faltan_servicios = Servicio.query.filter_by(negocio_id=negocio.id, activo=True).count() == 0

    # Obtener estadísticas avanzadas según el plan
    stats = get_dashboard_stats(negocio.id)

    return render_template("dashboard.html",
        onboarding_just_completed=onboarding_just_completed,
        faltan_horarios=faltan_horarios,
        faltan_servicios=faltan_servicios,
        stats=stats,
        plan=negocio.plan or "trial")

# --- Ver clientes SOLO del negocio actual ---
@app.route("/clientes")
@login_required
def ver_clientes():
    clientes = Cliente.query.filter_by(
        negocio_id=current_user.negocio_id
    ).all()

    if not clientes:
        return render_template("nuevo_cliente.html")

    resultado = f"<h2>Clientes de {current_user.negocio.nombre}</h2>"
    for c in clientes:
        resultado += f"ID: {c.id} — {c.nombre} — {c.telefono}<br>"
    return render_template("clientes.html", clientes=clientes)



@app.route("/api/clientes/buscar", methods=["GET"])
@login_required
def api_buscar_clientes():
    query = request.args.get("q", "").strip()

    # Si no hay texto, mandamos lista vacía para que el JS restaure la original
    if not query:
        return jsonify({"clientes": []})

    # Consulta directa a la base de datos (ilike es clave para iniciales)
    clientes = Cliente.query.filter(
        Cliente.negocio_id == current_user.negocio_id,
        db.or_(
            Cliente.nombre.ilike(f"%{query}%"),
            Cliente.telefono.ilike(f"%{query}%"),
            Cliente.email.ilike(f"%{query}%")
        )
    ).limit(15).all()

    return jsonify({
        "clientes": [{
            "id": c.id,
            "nombre": c.nombre,
            "telefono": c.telefono or "",
            "email": c.email or ""
        } for c in clientes]
    })

@app.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_cliente():
    negocio = current_user.negocio
    puede, count = verificar_limite(negocio, "clientes")
    if not puede:
        if count == "trial_expirado":
            return redirect(url_for("upgrade"))
        from flask import flash
        flash(f"Alcanzaste el límite de clientes de tu plan ({LIMITES_PLAN[negocio.plan]['clientes']}). Actualiza tu plan para agregar más.", "error")
        return redirect(url_for("upgrade"))

    if request.method == "POST":
        cliente = Cliente(
            nombre=request.form["nombre"],
            email=request.form.get("email"),
            telefono=request.form.get("telefono"),
            negocio_id=current_user.negocio_id
        )
        db.session.add(cliente)
        db.session.commit()
        return redirect(url_for("ver_clientes"))
    return render_template("nuevo_cliente.html")

@app.route("/servicios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_servicio():
    negocio = current_user.negocio
    puede, count = verificar_limite(negocio, "servicios")
    if not puede:
        if count == "trial_expirado":
            return redirect(url_for("upgrade"))
        from flask import flash
        flash(f"Alcanzaste el límite de servicios de tu plan ({LIMITES_PLAN[negocio.plan]['servicios']}). Actualiza tu plan.", "error")
        return redirect(url_for("upgrade"))

    if request.method == "POST":
        servicio = Servicio(
            nombre=request.form["nombre"],
            duracion_min=int(request.form["duracion_min"]),
            precio=float(request.form["precio"]) if request.form["precio"] else None,
            negocio_id=current_user.negocio_id
        )
        db.session.add(servicio)
        db.session.commit()

        # Verificar si onboarding completado (horario + al menos un servicio activo)
        tiene_horarios = Horario.query.filter_by(negocio_id=current_user.negocio_id).count() > 0
        tiene_servicios = Servicio.query.filter_by(negocio_id=current_user.negocio_id, activo=True).count() > 0

        if tiene_horarios and tiene_servicios:
            session['onboarding_just_completed'] = True

        return redirect(url_for("ver_servicios"))
    return render_template("nuevo_servicio.html")

@app.route("/upgrade")
@login_required
def upgrade():
    negocio = current_user.negocio
    return render_template("upgrade.html", negocio=negocio)

# --- Logout ---
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# --- Perfil del negocio ---
@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil_negocio():
    negocio = current_user.negocio
    if request.method == "POST":
        negocio.nombre = request.form.get("nombre", negocio.nombre)
        negocio.tipo = request.form.get("tipo")
        negocio.eslogan = request.form.get("eslogan")
        negocio.telefono = request.form.get("telefono")
        negocio.direccion = request.form.get("direccion")

        # Procesar imagen recortada de Cropper.js
        logo_recortado = request.form.get("logo_recortado")
        if logo_recortado and logo_recortado.startswith("data:image"):
            try:
                resultado = cloudinary.uploader.upload(
                    logo_recortado,
                    folder="reserfy/logos",
                    public_id=f"negocio_{negocio.id}",
                    overwrite=True,
                    transformation=[
                        {"width": 400, "height": 400, "crop": "fill", "gravity": "face"}
                    ]
                )
                negocio.logo_url = resultado["secure_url"]
            except Exception as e:
                print(f"Error subiendo logo: {e}")

        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("perfil.html", negocio=negocio)

# --- API Routes for Services (AJAX) ---
@app.route("/api/servicios/<int:id>", methods=["GET"])
@login_required
def api_get_servicio(id):
    servicio = Servicio.query.filter_by(
        id=id,
        negocio_id=current_user.negocio_id
    ).first_or_404()
    return jsonify({
        "id": servicio.id,
        "nombre": servicio.nombre,
        "duracion_min": servicio.duracion_min,
        "precio": servicio.precio
    })

@app.route("/api/servicios", methods=["POST"])
@app.route("/servicio/nuevo", methods=["POST"])
@app.route("/api/servicios/nuevo", methods=["POST"])
@login_required
def api_nuevo_servicio():
    """Create a new service via AJAX."""
    try:
        data = request.get_json()

        negocio = current_user.negocio
        puede, count = verificar_limite(negocio, "servicios")

        if not puede:
            if count == "trial_expirado":
                return jsonify({"success": False, "error": "trial_expirado", "redirect": url_for('upgrade')})
            return jsonify({
                "success": False,
                "error": f"Alcanzaste el límite de servicios de tu plan ({LIMITES_PLAN[negocio.plan]['servicios']})."
            })

        servicio = Servicio(
            nombre=data.get('nombre', ''),
            duracion_min=int(data.get('duracion_min', 60)),
            precio=float(data.get('precio')) if data.get('precio') else None,
            negocio_id=current_user.negocio_id
        )
        db.session.add(servicio)
        db.session.commit()

        return jsonify({"success": True, "message": "Servicio creado correctamente", "id": servicio.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/servicios/<int:servicio_id>", methods=["PUT", "POST"])
@app.route("/api/servicios/<int:servicio_id>/editar", methods=["POST"])
@login_required
def api_editar_servicio(servicio_id):
    """Edit a service via AJAX."""
    try:
        servicio = Servicio.query.filter_by(
            id=servicio_id,
            negocio_id=current_user.negocio_id
        ).first_or_404()

        data = request.get_json()

        servicio.nombre = data.get('nombre', servicio.nombre)
        servicio.duracion_min = int(data.get('duracion_min', servicio.duracion_min))
        servicio.precio = float(data.get('precio')) if data.get('precio') else None

        db.session.commit()

        return jsonify({"success": True, "message": "Servicio actualizado correctamente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/servicios/<int:servicio_id>", methods=["DELETE"])
@app.route("/api/servicios/<int:servicio_id>/eliminar", methods=["POST"])
@login_required
def api_eliminar_servicio(servicio_id):
    """Delete a service via AJAX."""
    try:
        servicio = Servicio.query.filter_by(
            id=servicio_id,
            negocio_id=current_user.negocio_id
        ).first_or_404()

        db.session.delete(servicio)
        db.session.commit()

        return jsonify({"success": True, "message": "Servicio eliminado correctamente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


# --- Ver y gestionar servicios (página) ---
@app.route("/servicios")
@login_required
def ver_servicios():
    servicios = Servicio.query.filter_by(
        negocio_id=current_user.negocio_id
    ).all()
    return render_template("servicios.html", servicios=servicios)

# --- Editar servicio ---
@app.route("/servicios/editar/<int:servicio_id>", methods=["GET", "POST"])
@login_required
def editar_servicio(servicio_id):
    servicio = Servicio.query.filter_by(
        id=servicio_id,
        negocio_id=current_user.negocio_id
    ).first_or_404()

    if request.method == "POST":
        servicio.nombre = request.form["nombre"]
        servicio.duracion_min = int(request.form["duracion_min"])
        servicio.precio = float(request.form["precio"]) if request.form["precio"] else None
        db.session.commit()
        return redirect(url_for("ver_servicios"))

    return render_template("editar_servicio.html", servicio=servicio)

# --- Eliminar servicio ---
@app.route("/servicios/eliminar/<int:servicio_id>", methods=["POST"])
@login_required
def eliminar_servicio(servicio_id):
    servicio = Servicio.query.filter_by(
        id=servicio_id,
        negocio_id=current_user.negocio_id
    ).first_or_404()
    db.session.delete(servicio)
    db.session.commit()
    return redirect(url_for("ver_servicios"))

# --- API Horarios (nuevo diseño) ---
@app.route("/api/horarios", methods=["POST"])
@login_required
def api_horarios():
    """API para guardar horarios mediante JSON."""
    try:
        data = request.get_json()
        horarios = data.get('horarios', [])

        if not horarios:
            return jsonify({"success": False, "error": "No se recibieron datos de horarios"}), 400

        # Eliminar horarios existentes del negocio
        Horario.query.filter_by(negocio_id=current_user.negocio_id).delete()

        # Guardar nuevos horarios
        for h in horarios:
            if h.get('activo') and h.get('hora_inicio') and h.get('hora_fin'):
                try:
                    hora_inicio = datetime.strptime(h['hora_inicio'], "%H:%M").time()
                    hora_fin = datetime.strptime(h['hora_fin'], "%H:%M").time()

                    horario = Horario(
                        negocio_id=current_user.negocio_id,
                        dia_semana=h['dia_semana'],
                        hora_apertura=hora_inicio,
                        hora_cierre=hora_fin
                    )
                    db.session.add(horario)
                except (ValueError, KeyError) as e:
                    db.session.rollback()
                    return jsonify({"success": False, "error": f"Error en formato de hora: {str(e)}"}), 400

        db.session.commit()

        # Verificar onboarding
        tiene_horarios = Horario.query.filter_by(negocio_id=current_user.negocio_id).count() > 0
        tiene_servicios = Servicio.query.filter_by(negocio_id=current_user.negocio_id, activo=True).count() > 0

        if tiene_horarios and tiene_servicios:
            session['onboarding_just_completed'] = True

        return jsonify({"success": True, "message": "Horarios guardados correctamente"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# --- Configurar horario del negocio ---
@app.route("/horario/configurar", methods=["GET", "POST"])
@login_required
def configurar_horario():
    if not current_user.is_authenticated:
        return redirect(url_for('registro'))

    # GET: Mostrar el nuevo template con horarios existentes
    if request.method == "GET":
        horarios_existentes = Horario.query.filter_by(negocio_id=current_user.negocio_id).all()
        horarios_por_dia = {h.dia_semana: h for h in horarios_existentes}
        return render_template("horarios.html", horarios_por_dia=horarios_por_dia)

    # POST: Mantener compatibilidad con el formulario legacy
    Horario.query.filter_by(negocio_id=current_user.negocio_id).delete()

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    for i, dia in enumerate(dias):
        if request.form.get(f"activo_{i}"):
            apertura = datetime.strptime(request.form[f"apertura_{i}"], "%H:%M").time()
            cierre = datetime.strptime(request.form[f"cierre_{i}"], "%H:%M").time()
            horario = Horario(
                negocio_id=current_user.negocio_id,
                dia_semana=i,
                hora_apertura=apertura,
                hora_cierre=cierre
            )
            db.session.add(horario)

    db.session.commit()

    # Verificar onboarding
    tiene_horarios = Horario.query.filter_by(negocio_id=current_user.negocio_id).count() > 0
    tiene_servicios = Servicio.query.filter_by(negocio_id=current_user.negocio_id, activo=True).count() > 0

    if tiene_horarios and tiene_servicios:
        session['onboarding_just_completed'] = True

    return redirect(url_for("dashboard"))

def obtener_slots_disponibles(negocio_id, fecha):
    negocio = db.session.get(Negocio, negocio_id)
    tz = pytz.timezone(negocio.timezone)

    dia_semana = fecha.weekday()
    horario = Horario.query.filter_by(
        negocio_id=negocio_id,
        dia_semana=dia_semana
    ).first()

    if not horario:
        return []

    slots = []
    hora_actual = datetime.combine(fecha, horario.hora_apertura)
    hora_cierre = datetime.combine(fecha, horario.hora_cierre)

    while hora_actual < hora_cierre:
        hora_local_aware = tz.localize(hora_actual)
        hora_utc = hora_local_aware.astimezone(pytz.utc).replace(tzinfo=None)
        slots.append((hora_actual, hora_utc))
        hora_actual += timedelta(hours=1)

    reservas_del_dia = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= tz.localize(datetime.combine(fecha, time.min)).astimezone(pytz.utc).replace(tzinfo=None),
        Reserva.fecha_hora <= tz.localize(datetime.combine(fecha, time.max)).astimezone(pytz.utc).replace(tzinfo=None),
        Reserva.estado != "cancelada"
    ).all()

    horas_ocupadas = [r.fecha_hora.replace(second=0, microsecond=0) for r in reservas_del_dia]
    slots_disponibles = [(local, utc) for local, utc in slots if utc not in horas_ocupadas]

    return slots_disponibles

MAIL_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

def enviar_email(destinatario, asunto, contenido_html):
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        mensaje = SGMail(
            from_email=MAIL_SENDER,
            to_emails=destinatario,
            subject=asunto,
            html_content=contenido_html
        )
        response = sg.send(mensaje)
        print(f"✅ Email enviado: {response.status_code}")
    except Exception as e:
        print(f"Error completo: {e}")
        if hasattr(e, 'body'):
            print(f"Body: {e.body}")
        if hasattr(e, 'status_code'):
            print(f"Status: {e.status_code}")

def enviar_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora, nombre_negocio, token, timezone="America/Santo_Domingo"):
    tz = pytz.timezone(timezone)
    if fecha_hora.tzinfo is None:
        fecha_hora_display = tz.localize(fecha_hora)
    else:
        fecha_hora_display = fecha_hora.astimezone(tz)

    link_gestion = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/reserva/{token}/gestionar"
    enviar_email(
        destinatario=email_cliente,
        asunto=f"Reserva confirmada — {nombre_negocio}",
        contenido_html=f"""
            <h2>¡Tu reserva está confirmada!</h2>
            <p>Hola <strong>{nombre_cliente}</strong>,</p>
            <p>Tu cita ha sido agendada con éxito:</p>
            <ul>
                <li><strong>Negocio:</strong> {nombre_negocio}</li>
                <li><strong>Servicio:</strong> {servicio}</li>
                <li><strong>Fecha y hora:</strong> {fecha_hora_display.strftime('%d/%m/%Y a las %I:%M %p')}</li>
            </ul>
            <p>
                <a href="{link_gestion}" style="background:#e74c3c;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;">
                    Cancelar mi reserva
                </a>
            </p>
            <p style="color:#888;font-size:12px;">O copia este link: {link_gestion}</p>
        """
    )

def enviar_notificacion_negocio(negocio, cliente, reserva):
    try:
        tz = pytz.timezone(negocio.timezone)
        if reserva.fecha_hora.tzinfo is None:
            fecha_display = pytz.utc.localize(reserva.fecha_hora).astimezone(tz)
        else:
            fecha_display = reserva.fecha_hora.astimezone(tz)

        enviar_email(
            destinatario=negocio.email,
            asunto=f"📅 Nueva reserva — {cliente.nombre}",
            contenido_html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #912A5C, #FA8F3E); padding: 2rem; text-align: center; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 1.5rem;">📅 Nueva Reserva</h1>
                    <p style="color: rgba(255,255,255,0.85); margin: 0.5rem 0 0;">Tienes una nueva reserva en {negocio.nombre}</p>
                </div>
                <div style="background: #f8f8f8; padding: 2rem; border-radius: 0 0 12px 12px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 0.8rem 0; color: #888; font-size: 0.9rem;">👤 Cliente</td>
                            <td style="padding: 0.8rem 0; font-weight: 600; color: #1A1A1A;">{cliente.nombre}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 0.8rem 0; color: #888; font-size: 0.9rem;">📧 Email</td>
                            <td style="padding: 0.8rem 0; color: #1A1A1A;">{cliente.email or '—'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 0.8rem 0; color: #888; font-size: 0.9rem;">📞 Teléfono</td>
                            <td style="padding: 0.8rem 0; color: #1A1A1A;">{cliente.telefono or '—'}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 0.8rem 0; color: #888; font-size: 0.9rem;">✂️ Servicio</td>
                            <td style="padding: 0.8rem 0; font-weight: 600; color: #1A1A1A;">{reserva.servicio}</td>
                        </tr>
                        <tr>
                            <td style="padding: 0.8rem 0; color: #888; font-size: 0.9rem;">🗓️ Fecha y hora</td>
                            <td style="padding: 0.8rem 0; font-weight: 600; color: #912A5C;">
                                {fecha_display.strftime('%d/%m/%Y a las %I:%M %p')}
                            </td>
                        </tr>
                    </table>
                    <div style="margin-top: 1.5rem; text-align: center;">
                        <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/reservas"
                           style="background: linear-gradient(135deg, #912A5C, #FA8F3E); color: white; padding: 0.8rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 700;">
                            Ver en el dashboard →
                        </a>
                    </div>
                    <p style="color: #aaa; font-size: 0.78rem; text-align: center; margin-top: 1.5rem;">
                        Este email fue enviado automáticamente por Reserfy
                    </p>
                </div>
            </div>
            """
        )
    except Exception as e:
        print(f"Error enviando notificación al negocio: {e}")

def enviar_cancelacion_emails(cliente, negocio, reserva):
    if not cliente or not cliente.email:
        return

    # Email al cliente
    enviar_email(
        destinatario=cliente.email,
        asunto=f"Reserva cancelada — {negocio.nombre}",
        contenido_html=f"""
            <h2>Tu reserva fue cancelada</h2>
            <p>Hola <strong>{cliente.nombre}</strong>,</p>
            <p>Tu reserva ha sido cancelada:</p>
            <ul>
                <li><strong>Negocio:</strong> {negocio.nombre}</li>
                <li><strong>Servicio:</strong> {reserva.servicio}</li>
                <li><strong>Fecha y hora:</strong> {reserva.fecha_hora.strftime('%d/%m/%Y a las %I:%M %p')}</li>
            </ul>
            <p>Puedes hacer una nueva reserva en cualquier momento.</p>
        """
    )

    # Email al negocio
    enviar_email(
        destinatario=negocio.email,
        asunto=f"Reserva cancelada — {cliente.nombre}",
        contenido_html=f"""
            <h2>Una reserva fue cancelada</h2>
            <p>La siguiente reserva ha sido cancelada:</p>
            <ul>
                <li><strong>Cliente:</strong> {cliente.nombre}</li>
                <li><strong>Email:</strong> {cliente.email}</li>
                <li><strong>Servicio:</strong> {reserva.servicio}</li>
                <li><strong>Fecha y hora:</strong> {reserva.fecha_hora.strftime('%d/%m/%Y a las %H:%M')}</li>
            </ul>
        """
    )
    
@app.route("/b/<slug>/slots")
def slots_disponibles(slug):
    from flask import jsonify
    negocio = Negocio.query.filter_by(slug=slug).first_or_404()
    fecha_str = request.args.get("fecha")
    if not fecha_str:
        return jsonify({"slots": []})

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        slots = obtener_slots_disponibles(negocio.id, fecha)
        tz = pytz.timezone(negocio.timezone)

        resultado = []
        for slot_local, slot_utc in slots:
            resultado.append({
                "local": slot_local.strftime("%I:%M %p"),
                "utc": str(slot_utc)
            })
        return jsonify({"slots": resultado})
    except Exception as e:
        return jsonify({"slots": [], "error": str(e)})


# --- Página pública de reservas ---
@app.route("/b/<slug>", methods=["GET", "POST"])
def reserva_publica(slug):
    negocio = Negocio.query.filter_by(slug=slug).first_or_404()
    mensaje = ""
    slots = []
    fecha_seleccionada = None
    servicio_seleccionado = None

    servicios = Servicio.query.filter_by(
        negocio_id=negocio.id,
        activo=True
    ).all()

    if request.method == "POST" and "fecha" in request.form and "hora" not in request.form:
        fecha_seleccionada = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        servicio_seleccionado = request.form.get("servicio")
        slots = obtener_slots_disponibles(negocio.id, fecha_seleccionada)

    elif request.method == "POST" and "hora" in request.form:
        hora_str = request.form.get("hora", "").strip()
        nombre_cliente = request.form.get("nombre_cliente")
        email_cliente = request.form.get("email_cliente")
        servicio_seleccionado = request.form.get("servicio")

        try:
            puede, count = verificar_limite(negocio, "reservas_mes")
            if not puede:
                mensaje = "Este negocio ha alcanzado su límite de reservas por este mes. Intenta más tarde."
                return render_template(
                "reserva_publica.html",
                negocio=negocio,
                slots=slots,
                mensaje=mensaje,
                fecha_seleccionada=fecha_seleccionada,
                servicio_seleccionado=servicio_seleccionado,
                servicios=servicios,
                now=datetime.now()
            )
            fecha_hora_utc = datetime.strptime(hora_str, "%Y-%m-%d %H:%M:%S")

            cliente = Cliente.query.filter_by(
                email=email_cliente,
                negocio_id=negocio.id
            ).first()

            if not cliente:
                cliente = Cliente(
                    nombre=nombre_cliente,
                    telefono=request.form.get("telefono_cliente", ""),
                    email=email_cliente,
                    negocio_id=negocio.id
                )
                db.session.add(cliente)
                db.session.commit()

            reserva = Reserva(
                fecha_hora=fecha_hora_utc,
                servicio=servicio_seleccionado,
                negocio_id=negocio.id,
                cliente_id=cliente.id
            )
            db.session.add(reserva)
            db.session.commit()

            try:
                enviar_notificacion_negocio(negocio, cliente, reserva)
            except Exception as e:
                print(f"Error notificando al negocio: {e}")

            try:
                enviar_confirmacion(
                    email_cliente=email_cliente,
                    nombre_cliente=nombre_cliente,
                    servicio=servicio_seleccionado,
                    fecha_hora=fecha_hora_utc,
                    nombre_negocio=negocio.nombre,
                    token=reserva.token,
                    timezone=negocio.timezone
                )
            except Exception:
                pass

            tz = pytz.timezone(negocio.timezone)
            fecha_hora_local = pytz.utc.localize(fecha_hora_utc).astimezone(tz)
            mensaje = f"✅ Reserva confirmada para el {fecha_hora_local.strftime('%d/%m/%Y a las %I:%M %p')}"

        except ValueError:
            mensaje = "Error: formato de hora inválido. Intenta de nuevo."

    return render_template(
    "reserva_publica.html",
    negocio=negocio,
    slots=slots,
    mensaje=mensaje,
    fecha_seleccionada=fecha_seleccionada,
    servicio_seleccionado=servicio_seleccionado,
    servicios=servicios,
    now=datetime.now()
)
            
# Auto-cancelar reservas después de 4 horas
def auto_cancelar_reservas():
    with app.app_context():
        limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=4)
        reservas = Reserva.query.filter(
            Reserva.estado == 'pendiente',
            Reserva.fecha_hora < limite
        ).all()
        for r in reservas:
            r.estado = 'cancelada'
        if reservas:
            db.session.commit()
            print(f"Auto-canceladas {len(reservas)} reservas")

scheduler = BackgroundScheduler()
scheduler.add_job(auto_cancelar_reservas, 'interval', minutes=30)
scheduler.start()

# Ver reservas pendientes
@app.route("/reservas")
@login_required
def ver_reservas():
    reservas = Reserva.query.filter_by(
        negocio_id=current_user.negocio_id
    ).filter(
        Reserva.estado == 'pendiente'
    ).order_by(Reserva.fecha_hora).all()
    return render_template("reservas.html", reservas=reservas)

# Historial
@app.route("/reservas/historial")
@login_required
def historial_reservas():
    reservas = Reserva.query.filter_by(
        negocio_id=current_user.negocio_id
    ).filter(
        Reserva.estado.in_(['cancelada', 'completada'])
    ).order_by(Reserva.fecha_hora.desc()).all()
    return render_template("historial_reservas.html", reservas=reservas)

# Cancelar reserva
@app.route("/reservas/cancelar/<int:reserva_id>", methods=["POST"])
@login_required
def cancelar_reserva(reserva_id):
    reserva = Reserva.query.filter_by(
        id=reserva_id,
        negocio_id=current_user.negocio_id
    ).first_or_404()
    cliente = db.session.get(Cliente, reserva.cliente_id)
    negocio = db.session.get(Negocio, reserva.negocio_id)
    reserva.estado = "cancelada"
    db.session.commit()
    try:
        enviar_cancelacion_emails(cliente, negocio, reserva)
    except Exception as e:
        print(f"Error enviando email: {e}")
    return redirect(url_for("ver_reservas"))

# Completar reserva
@app.route("/reservas/completar/<int:reserva_id>", methods=["POST"])
@login_required
def completar_reserva(reserva_id):
    reserva = Reserva.query.filter_by(
        id=reserva_id,
        negocio_id=current_user.negocio_id
    ).first_or_404()
    reserva.estado = "completada"
    db.session.commit()
    return redirect(url_for("ver_reservas"))

# --- Gestionar reserva como cliente (sin login) ---
@app.route("/reserva/<token>/gestionar", methods=["GET", "POST"])
def gestionar_reserva(token):
    reserva = Reserva.query.filter_by(token=token).first_or_404()
    negocio = db.session.get(Negocio, reserva.negocio_id)
    cliente = db.session.get(Cliente, reserva.cliente_id)
    mensaje = ""

    if request.method == "POST":
        if reserva.estado != "cancelada":
            reserva.estado = "cancelada"
            db.session.commit()

            try:
                enviar_cancelacion_emails(cliente, negocio, reserva)
            except Exception as e:
                print(f"Error enviando email: {e}")

            mensaje = "✅ Tu reserva fue cancelada correctamente."
        else:
            mensaje = "Esta reserva ya estaba cancelada."

    return render_template(
        "gestionar_reserva.html",
        reserva=reserva,
        negocio=negocio,
        cliente=cliente,
        mensaje=mensaje
    )

# --- Manejadores de error ---
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def error_servidor(e):
    return render_template("500.html"), 500

with app.app_context():
    db.create_all()
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("ALTER TABLE negocio ADD COLUMN plan VARCHAR(20) DEFAULT 'trial'"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE negocio ADD COLUMN trial_expira DATETIME"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE negocio ADD COLUMN reset_token VARCHAR(100)"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE negocio ADD COLUMN reset_token_expira DATETIME"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE negocio ADD COLUMN marca_agua_personalizada VARCHAR(200)"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE usuario ADD COLUMN reset_token VARCHAR(100)"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("ALTER TABLE usuario ADD COLUMN reset_token_expira DATETIME"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("UPDATE reserva SET estado = 'pendiente' WHERE estado = 'confirmada'"))
            conn.commit()
        except:
            pass
        try:
            conn.execute(db.text("UPDATE reserva SET estado = 'pendiente' WHERE estado IS NULL"))
            conn.commit()
        except:
            pass

if __name__ == "__main__":
    app.run(debug=True)
