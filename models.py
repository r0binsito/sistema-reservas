from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import uuid
from datetime import datetime, timedelta, timezone
import json

db = SQLAlchemy()


# === ROLES DE USUARIO ===
class UserRole:
    ADMIN = 'admin'      # Dueño del negocio - acceso total
    STAFF = 'staff'      # Empleado - acceso limitado (reservas, clientes)

# === TIPOS DE ACCIÓN PARA AUDITORÍA ===
class AuditAction:
    # Usuarios
    USUARIO_CREADO = 'USUARIO_CREADO'
    USUARIO_EDITADO = 'USUARIO_EDITADO'
    USUARIO_DESACTIVADO = 'USUARIO_DESACTIVADO'
    USUARIO_ACTIVADO = 'USUARIO_ACTIVADO'

    # Reservas
    RESERVA_CREADA = 'RESERVA_CREADA'
    RESERVA_EDITADA = 'RESERVA_EDITADA'
    RESERVA_CANCELADA = 'RESERVA_CANCELADA'
    RESERVA_COMPLETADA = 'RESERVA_COMPLETADA'

    # Clientes
    CLIENTE_CREADO = 'CLIENTE_CREADO'
    CLIENTE_EDITADO = 'CLIENTE_EDITADO'
    CLIENTE_ELIMINADO = 'CLIENTE_ELIMINADO'

    # Servicios
    SERVICIO_CREADO = 'SERVICIO_CREADO'
    SERVICIO_EDITADO = 'SERVICIO_EDITADO'
    SERVICIO_ELIMINADO = 'SERVICIO_ELIMINADO'

    # Negocio
    NEGOCIO_EDITADO = 'NEGOCIO_EDITADO'
    PLAN_ACTUALIZADO = 'PLAN_ACTUALIZADO'

    # Auth
    LOGIN_EXITOSO = 'LOGIN_EXITOSO'
    LOGIN_FALLIDO = 'LOGIN_FALLIDO'

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
    # Campos de suscripción
    plan_frecuencia = db.Column(db.String(20), default="mensual")  # 'mensual', 'anual', 'unico'
    plan_vence = db.Column(db.DateTime(timezone=True), nullable=True)  # Fecha de vencimiento del plan
    marca_agua_personalizada = db.Column(db.String(200), nullable=True)
    # Colores personalizados para plan Elite
    color_primario = db.Column(db.String(7), nullable=True)  # Color principal de botones (legacy)
    color_acento = db.Column(db.String(7), nullable=True)  # Color de acento: botones, iconos, pasos activos
    gradiente_banner_inicio = db.Column(db.String(7), nullable=True)  # Color inicial del gradiente del header
    gradiente_banner_fin = db.Column(db.String(7), nullable=True)  # Color final del gradiente del header
    gradiente_avatar_inicio = db.Column(db.String(7), nullable=True)  # Color inicial del gradiente del avatar
    gradiente_avatar_fin = db.Column(db.String(7), nullable=True)  # Color final del gradiente del avatar

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
    nombre = db.Column(db.String(100), nullable=True)  # Nombre del empleado/staff
    telefono = db.Column(db.String(20), nullable=True)  # Teléfono de contacto
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    negocio = db.relationship("Negocio", backref="usuarios")

    # === NUEVOS CAMPOS RBAC ===
    role = db.Column(db.String(20), default=UserRole.ADMIN)  # 'admin' o 'staff'
    is_active = db.Column(db.Boolean, default=True)  # Para desactivar empleados sin borrar
    is_saas_admin = db.Column(db.Boolean, default=False)  # Súper administrador de la plataforma

    # Token para recuperación de contraseña
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expira = db.Column(db.DateTime(timezone=True), nullable=True)

    # Token para invitaciones (solo para nuevos usuarios invitados)
    invitation_token = db.Column(db.String(100), nullable=True)
    invitation_expira = db.Column(db.DateTime(timezone=True), nullable=True)

    def is_admin(self):
        """Verifica si el usuario es administrador del negocio."""
        return self.role == UserRole.ADMIN

    def can_manage_users(self):
        """Verifica si el usuario puede gestionar otros usuarios (solo admin)."""
        return self.role == UserRole.ADMIN and self.is_active

    def is_saas_admin_user(self):
        """Verifica si el usuario es súper administrador de la plataforma."""
        return self.is_saas_admin

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


class AuditLog(db.Model):
    """Registro de auditoría para acciones críticas del sistema."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)  # Quién realizó la acción
    action = db.Column(db.String(50), nullable=False)  # Tipo de acción (AuditAction)
    entity_type = db.Column(db.String(50), nullable=True)  # 'usuario', 'reserva', 'cliente', 'servicio', 'negocio'
    entity_id = db.Column(db.Integer, nullable=True)  # ID de la entidad afectada
    description = db.Column(db.String(500), nullable=True)  # Descripción legible
    changes = db.Column(db.Text, nullable=True)  # JSON con valores antiguos/nuevos
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 o IPv6
    user_agent = db.Column(db.String(255), nullable=True)  # Browser/Client info
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relaciones
    negocio = db.relationship("Negocio", backref="audit_logs")
    user = db.relationship("Usuario", backref="audit_logs")

    def set_changes(self, old_values, new_values):
        """Guarda los cambios como JSON."""
        self.changes = json.dumps({
            'old': old_values,
            'new': new_values
        })

    def get_changes(self):
        """Obtiene los cambios desde JSON."""
        if self.changes:
            return json.loads(self.changes)
        return None

    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id} at {self.timestamp}>'


class GlobalAuditLog(db.Model):
    """
    Registro de auditoría GLOBAL para el Súper Admin.
    Registra acciones de TODA la plataforma, no solo de un negocio específico.
    """
    __tablename__ = 'global_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocio.id"), nullable=True, index=True)  # Opcional
    user_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)  # Quién realizó la acción
    action = db.Column(db.String(50), nullable=False)  # Tipo de acción
    entity_type = db.Column(db.String(50), nullable=True)  # 'negocio', 'usuario', 'plan', 'sistema'
    entity_id = db.Column(db.Integer, nullable=True)  # ID de la entidad afectada
    description = db.Column(db.String(500), nullable=True)  # Descripción legible
    details = db.Column(db.Text, nullable=True)  # JSON con detalles adicionales
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 o IPv6
    user_agent = db.Column(db.String(255), nullable=True)  # Browser/Client info
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relaciones
    negocio = db.relationship("Negocio", backref="global_audit_logs")
    user = db.relationship("Usuario", backref="global_audit_logs")

    def set_details(self, data):
        """Guarda detalles como JSON."""
        self.details = json.dumps(data)

    def get_details(self):
        """Obtiene los detalles desde JSON."""
        if self.details:
            return json.loads(self.details)
        return None

    def __repr__(self):
        return f'<GlobalAuditLog {self.action} at {self.timestamp}>'


# === TIPOS DE ACCIÓN PARA AUDITORÍA GLOBAL ===
class GlobalAuditAction:
    # Negocios
    NEGOCIO_CREADO = 'NEGOCIO_CREADO'
    NEGOCIO_SUSPENDIDO = 'NEGOCIO_SUSPENDIDO'
    NEGOCIO_ACTIVADO = 'NEGOCIO_ACTIVADO'
    NEGOCIO_ELIMINADO = 'NEGOCIO_ELIMINADO'

    # Planes
    PLAN_CAMBIADO = 'PLAN_CAMBIADO'
    PLAN_VENCIDO = 'PLAN_VENCIDO'
    PLAN_RENOVADO = 'PLAN_RENOVADO'

    # Usuarios
    USUARIO_REGISTRADO = 'USUARIO_REGISTRADO'
    USUARIO_ELIMINADO = 'USUARIO_ELIMINADO'
    SAAS_ADMIN_LOGIN = 'SAAS_ADMIN_LOGIN'

    # Sistema
    SISTEMA_BACKUP = 'SISTEMA_BACKUP'
    SISTEMA_ERROR = 'SISTEMA_ERROR'
    SISTEMA_CONFIG = 'SISTEMA_CONFIG'