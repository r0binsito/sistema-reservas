from flask import Flask, request, redirect, url_for, render_template_string
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Negocio, Cliente, Reserva, Usuario, Horario
from datetime import datetime, time, date, timedelta
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, render_template

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///reservas.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "clave-temporal")
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --- Registro ---
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]

        negocio = Negocio(nombre=nombre, email=email)
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

# --- El algoritmo principal ---
def obtener_slots_disponibles(negocio_id, fecha):
    # 1. Buscar el horario del negocio para ese día de la semana
    dia_semana = fecha.weekday()  # 0=Lunes, 6=Domingo
    horario = Horario.query.filter_by(
        negocio_id=negocio_id,
        dia_semana=dia_semana
    ).first()

    if not horario:
        return []  # El negocio no trabaja ese día

    # 2. Generar todos los slots posibles cada 60 minutos
    slots = []
    hora_actual = datetime.combine(fecha, horario.hora_apertura)
    hora_cierre = datetime.combine(fecha, horario.hora_cierre)

    while hora_actual < hora_cierre:
        slots.append(hora_actual)
        hora_actual += timedelta(hours=1)

    # 3. Quitar los slots que ya tienen reserva
    reservas_del_dia = Reserva.query.filter(
        Reserva.negocio_id == negocio_id,
        Reserva.fecha_hora >= datetime.combine(fecha, time.min),
        Reserva.fecha_hora <= datetime.combine(fecha, time.max),
        Reserva.estado != "cancelada"
    ).all()

    horas_ocupadas = [r.fecha_hora.replace(second=0, microsecond=0) for r in reservas_del_dia]
    slots_disponibles = [s for s in slots if s not in horas_ocupadas]

    return slots_disponibles

def enviar_confirmacion(email_cliente, nombre_cliente, servicio, fecha_hora, nombre_negocio):
    msg = Message(
        subject=f"Reserva confirmada — {nombre_negocio}",
        recipients=[email_cliente]
    )
    msg.html = f"""
        <h2>¡Tu reserva está confirmada!</h2>
        <p>Hola <strong>{nombre_cliente}</strong>,</p>
        <p>Tu cita ha sido agendada con éxito:</p>
        <ul>
            <li><strong>Negocio:</strong> {nombre_negocio}</li>
            <li><strong>Servicio:</strong> {servicio}</li>
            <li><strong>Fecha y hora:</strong> {fecha_hora.strftime('%d/%m/%Y a las %H:%M')}</li>
        </ul>
        <p>Si necesitas cancelar, responde a este correo.</p>
    """
    mail.send(msg)

# --- Página pública de reservas ---
@app.route("/reservar", methods=["GET", "POST"])
@login_required
def reservar():
    mensaje = ""
    slots = []
    fecha_seleccionada = None

    if request.method == "POST" and "fecha" in request.form and "hora" not in request.form:
        fecha_seleccionada = datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
        slots = obtener_slots_disponibles(current_user.negocio_id, fecha_seleccionada)

    elif request.method == "POST" and "hora" in request.form:
        hora_str = request.form.get("hora", "").strip()
        try:
            fecha_hora = datetime.strptime(hora_str, "%Y-%m-%d %H:%M:%S")
            reserva = Reserva(
                fecha_hora=fecha_hora,
                servicio=request.form["servicio"],
                negocio_id=current_user.negocio_id,
                cliente_id=1
            )
            db.session.add(reserva)
            db.session.commit()
            try:
                enviar_confirmacion(
                    email_cliente=current_user.email,
                    nombre_cliente=current_user.negocio.nombre,
                    servicio=request.form["servicio"],
                    fecha_hora=fecha_hora,
                    nombre_negocio=current_user.negocio.nombre
                )
                mensaje = f"✅ Reserva confirmada para el {fecha_hora.strftime('%d/%m/%Y a las %H:%M')} — Email enviado"
            except Exception as e:
                mensaje = f"✅ Reserva guardada, pero el email no se pudo enviar: {str(e)}"
        except ValueError:
            mensaje = "Error: formato de hora inválido. Intenta de nuevo."

    return render_template("reservar.html", slots=slots, mensaje=mensaje, fecha_seleccionada=fecha_seleccionada)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)