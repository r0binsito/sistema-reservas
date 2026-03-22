from flask import Flask, request, redirect, url_for, render_template, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, Negocio, Cliente, Reserva, Usuario, Horario, Servicio
from datetime import datetime, time, date, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from dotenv import load_dotenv
import os
import re
import pytz
import cloudinary
import cloudinary.uploader
from flask import g
from flask_dance.consumer import oauth_authorized
from flask_dance.contrib.google import google
import secrets
import ssl
import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

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
    return Usuario.query.get(int(user_id))

@app.context_processor
def inject_plan_info():
    if current_user.is_authenticated:
        negocio = current_user.negocio
        plan = negocio.plan or "trial"
        limites = get_limites(negocio)
        
        # Calcular uso actual
        from datetime import datetime
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
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
            delta = negocio.trial_expira - datetime.utcnow()
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

PLANTILLAS_SERVICIOS = {
    "Barbería": [
        {"nombre": "Corte de cabello", "duracion_min": 30, "precio": 350},
        {"nombre": "Barba", "duracion_min": 20, "precio": 200},
        {"nombre": "Corte + Barba", "duracion_min": 45, "precio": 500},
    ],
    "Salón de belleza": [
        {"nombre": "Corte de dama", "duracion_min": 45, "precio": 500},
        {"nombre": "Tinte", "duracion_min": 90, "precio": 1500},
        {"nombre": "Manicure", "duracion_min": 30, "precio": 300},
        {"nombre": "Pedicure", "duracion_min": 45, "precio": 400},
    ],
    "Consultorio médico": [
        {"nombre": "Consulta general", "duracion_min": 30, "precio": 800},
        {"nombre": "Consulta de seguimiento", "duracion_min": 20, "precio": 500},
    ],
    "Consultorio dental": [
        {"nombre": "Limpieza dental", "duracion_min": 45, "precio": 1000},
        {"nombre": "Extracción", "duracion_min": 30, "precio": 800},
        {"nombre": "Consulta", "duracion_min": 20, "precio": 500},
    ],
    "Spa": [
        {"nombre": "Masaje relajante", "duracion_min": 60, "precio": 1500},
        {"nombre": "Facial", "duracion_min": 45, "precio": 1200},
        {"nombre": "Masaje deportivo", "duracion_min": 60, "precio": 1800},
    ],
    "Restaurante": [
        {"nombre": "Reserva de mesa", "duracion_min": 120, "precio": 0},
        {"nombre": "Reserva privada", "duracion_min": 180, "precio": 0},
    ],
    "Gimnasio": [
        {"nombre": "Clase grupal", "duracion_min": 60, "precio": 300},
        {"nombre": "Entrenamiento personal", "duracion_min": 60, "precio": 800},
    ],
    "Otro": [
        {"nombre": "Servicio personalizado", "duracion_min": 60, "precio": 0},
    ],
}

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
        from datetime import datetime
        if datetime.utcnow() > negocio.trial_expira:
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

# --- Registro ---
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if Usuario.query.filter_by(email=email).first():
            return render_template("registro.html", error="Ya existe una cuenta con ese email.", paso=1)

        # Crear negocio vacío temporalmente
        negocio = Negocio(
            nombre="Mi negocio",
            email=email
        )
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

    return render_template("registro.html", paso=1)

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

        # Precargar servicios según tipo
        if negocio.tipo and negocio.tipo in PLANTILLAS_SERVICIOS:
            servicios_existentes = Servicio.query.filter_by(negocio_id=negocio.id).count()
            if servicios_existentes == 0:
                for s in PLANTILLAS_SERVICIOS[negocio.tipo]:
                    servicio = Servicio(
                        nombre=s["nombre"],
                        duracion_min=s["duracion_min"],
                        precio=s["precio"],
                        negocio_id=negocio.id
                    )
                    db.session.add(servicio)

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

    return render_template("configurar_negocio.html", negocio=negocio, paso=3)

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

from flask_dance.consumer import oauth_error

@oauth_error.connect_via(google_bp)
def google_error(blueprint, message, response):
    pass  # Ignorar errores OAuth

@oauth_authorized.connect_via(google_bp)
def google_authorized(blueprint, token):
    if not token:
        return redirect(url_for("login"))

    resp = blueprint.session.get("/oauth2/v1/userinfo")
    if not resp.ok:
        return redirect(url_for("login"))

    info = resp.json()
    email = info["email"]
    nombre = info.get("name", email.split("@")[0])

    usuario = Usuario.query.filter_by(email=email).first()
    if usuario:
        login_user(usuario)
        return False

    negocio = Negocio(nombre="Mi negocio", email=email)
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
    return False

@app.after_request
def redirigir_post_oauth(response):
    if response.status_code == 302 and '/auth/google' in request.path:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
    return response

# --- Dashboard protegido ---
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

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
            telefono=request.form["telefono"],
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
    return redirect(url_for("login"))

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

# --- Ver y gestionar servicios ---
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

# --- Configurar horario del negocio ---
@app.route("/horario/configurar", methods=["GET", "POST"])
@login_required
def configurar_horario():
    if request.method == "POST":
        # Borra el horario anterior del negocio
        Horario.query.filter_by(negocio_id=current_user.negocio_id).delete()

        dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
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
        return redirect(url_for("dashboard"))

    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    return render_template("horario.html", dias=enumerate(dias))

def obtener_slots_disponibles(negocio_id, fecha):
    negocio = Negocio.query.get(negocio_id)
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
            
# --- Ver todas las reservas del negocio ---
@app.route("/reservas")
@login_required
def ver_reservas():
    reservas = Reserva.query.filter_by(
        negocio_id=current_user.negocio_id
    ).order_by(Reserva.fecha_hora).all()
    return render_template("reservas.html", reservas=reservas)

@app.route("/reservas/cancelar/<int:reserva_id>", methods=["POST"])
@login_required
def cancelar_reserva(reserva_id):
    reserva = Reserva.query.filter_by(
        id=reserva_id,
        negocio_id=current_user.negocio_id
    ).first_or_404()

    cliente = Cliente.query.get(reserva.cliente_id)
    negocio = Negocio.query.get(reserva.negocio_id)

    reserva.estado = "cancelada"
    db.session.commit()

    try:
        enviar_cancelacion_emails(cliente, negocio, reserva)
    except Exception as e:
        print(f"Error enviando email de cancelación: {e}")

    return redirect(url_for("ver_reservas"))

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

# --- Gestionar reserva como cliente (sin login) ---
@app.route("/reserva/<token>/gestionar", methods=["GET", "POST"])
def gestionar_reserva(token):
    reserva = Reserva.query.filter_by(token=token).first_or_404()
    negocio = Negocio.query.get(reserva.negocio_id)
    cliente = Cliente.query.get(reserva.cliente_id)
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

if __name__ == "__main__":
    app.run(debug=True)