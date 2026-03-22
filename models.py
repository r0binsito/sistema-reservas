from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

class Negocio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True)
    timezone = db.Column(db.String(50), default="America/Santo_Domingo")
    tipo = db.Column(db.String(50))
    eslogan = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    logo_url = db.Column(db.String(300))
    plan = db.Column(db.String(20), default="trial")
    trial_expira = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=14))

    clientes = db.relationship("Cliente", backref="negocio", lazy=True, cascade="all, delete-orphan")
    reservas = db.relationship("Reserva", backref="negocio", lazy=True, cascade="all, delete-orphan")
    servicios = db.relationship("Servicio", backref="negocio", lazy=True, cascade="all, delete-orphan")
    horarios = db.relationship("Horario", backref="negocio", lazy=True, cascade="all, delete-orphan")

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    reservas = db.relationship("Reserva", backref="cliente", lazy=True, cascade="all, delete")

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha_hora = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    servicio = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(20), default="pendiente")
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=True, default=lambda: str(uuid.uuid4()).replace("-", ""))

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    negocio = db.relationship("Negocio", backref="usuarios")
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expira = db.Column(db.DateTime(timezone=True), nullable=True)

class Horario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    dia_semana = db.Column(db.Integer, nullable=False)
    hora_apertura = db.Column(db.Time, nullable=False)
    hora_cierre = db.Column(db.Time, nullable=False)

class Servicio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    duracion_min = db.Column(db.Integer, nullable=False, default=60)
    precio = db.Column(db.Float, nullable=True)
    activo = db.Column(db.Boolean, default=True)