from flask import Flask, request, redirect, url_for, render_template_string
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Negocio, Cliente, Reserva, Usuario, Horario, Servicio
from datetime import datetime, time, date, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail
import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template
import re
import pytz

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///reservas.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-temporal")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

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

    # Si el slug ya existe, agrega un número al final
    slug_base = slug
    contador = 1
    while Negocio.query.filter_by(slug=slug).first():
        slug = f"{slug_base}-{contador}"
        contador += 1

    return slug

def hora_local(negocio, fecha_hora_utc):
    tz = pytz.timezone(negocio.timezone)
    if fecha_hora_utc.tzinfo is None:
        fecha_hora_utc = pytz.utc.localize(fecha_hora_utc)
    return fecha_hora_utc.astimezone(tz)

# --- Index ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]

        # Verificar si el email ya existe
        if Negocio.query.filter_by(email=email).first():
            return render_template("registro.html", error="Ya existe un negocio con ese email.")

        negocio = Negocio(nombre=nombre, email=email)
        negocio.slug = generar_slug(nombre)
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
        return redirect(url_for("dashboard"))

    return render_template("registro.html")

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

        return "Email o contraseña incorrectos"

    return render_template("login.html")

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
    

# --- Agregar cliente AL negocio actual ---
@app.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_cliente():
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

# --- Logout ---
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# --- Ver y gestionar servicios ---
@app.route("/servicios")
@login_required
def ver_servicios():
    servicios = Servicio.query.filter_by(
        negocio_id=current_user.negocio_id
    ).all()
    return render_template("servicios.html", servicios=servicios)

# --- Agregar servicio ---
@app.route("/servicios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_servicio():
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
        sg.send(mensaje)
    except Exception as e:
        print(f"Error enviando email: {e}")

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
                <li><strong>Fecha y hora:</strong> {fecha_hora_display.strftime('%d/%m/%Y a las %H:%M')}</li>
            </ul>
            <p>
                <a href="{link_gestion}" style="background:#e74c3c;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;">
                    Cancelar mi reserva
                </a>
            </p>
            <p style="color:#888;font-size:12px;">O copia este link: {link_gestion}</p>
        """
    )

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
                <li><strong>Fecha y hora:</strong> {reserva.fecha_hora.strftime('%d/%m/%Y a las %H:%M')}</li>
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
    

# --- Página pública de reservas ---
@app.route("/b/<slug>", methods=["GET", "POST"])
def reserva_publica(slug):
    negocio = Negocio.query.filter_by(slug=slug).first_or_404()
    mensaje = ""
    slots = []
    fecha_seleccionada = None
    servicio_seleccionado = None

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
            mensaje = f"✅ Reserva confirmada para el {fecha_hora_local.strftime('%d/%m/%Y a las %H:%M')}"

        except ValueError:
            mensaje = "Error: formato de hora inválido. Intenta de nuevo."

    servicios = Servicio.query.filter_by(
        negocio_id=negocio.id,
        activo=True
    ).all()

    return render_template(
        "reserva_publica.html",
        negocio=negocio,
        slots=slots,
        mensaje=mensaje,
        fecha_seleccionada=fecha_seleccionada,
        servicio_seleccionado=servicio_seleccionado,
        servicios=servicios
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