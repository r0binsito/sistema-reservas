from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
import uuid
import pytz

db = SQLAlchemy()

class Negocio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=True)
    timezone = db.Column(db.String(50), nullable=False, default="America/Santo_Domingo")
    tipo = db.Column(db.String(50), nullable=True)
    eslogan = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    logo_url = db.Column(db.String(300), nullable=True)
    clientes = db.relationship("Cliente", backref="negocio", lazy=True)
    servicios = db.relationship("Servicio", backref="negocio", lazy=True)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False)
    reservas = db.relationship("Reserva", backref="cliente", lazy=True)

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    servicio = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(20), default="pendiente")
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=True, default=lambda: str(uuid.uuid4()).replace("-", ""))

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False)
    negocio = db.relationship("Negocio", backref="usuarios")

class Horario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_apertura = db.Column(db.Time, nullable=False)
    hora_cierre = db.Column(db.Time, nullable=False)

class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    duracion_min = db.Column(db.Integer, nullable=False, default=60)
    precio = db.Column(db.Float, nullable=True)
    activo = db.Column(db.Boolean, default=True)
