"""
Decoradores de autorización y sistema de auditoría para Reserfy.
Incluye:
- @requires_role('admin') - Protege rutas según rol
- @requires_active_plan - Protege rutas si el plan está vencido
- @audit_action('ACCION') - Registra acciones automáticamente
- Funciones auxiliares para verificación de permisos
"""

from functools import wraps
from flask import request, redirect, url_for, flash, jsonify
from flask_login import current_user
from models import db, AuditLog, UserRole, AuditAction
from datetime import datetime, timezone


# === DECORador DE PLAN ACTIVO ===

def requires_active_plan(f):
    """
    Decorador que verifica si el plan del negocio está activo (no vencido).

    Si el plan ha vencido, redirige a la página de suscripción vencida.

    Uso:
        @app.route('/dashboard')
        @login_required
        @requires_active_plan
        def dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        from utils.subscription import plan_activo

        negocio = current_user.negocio

        # Si el plan está vencido, redirigir a página de suscripción vencida
        if not plan_activo(negocio):
            flash('Tu suscripción ha vencido. Renueva para continuar.', 'error')
            return redirect(url_for('suscripcion_vencida'))

        return f(*args, **kwargs)
    return decorated_function


# === DECORADORES DE AUTORIZACIÓN ===

def requires_role(*roles):
    """
    Decorador que restringe el acceso a usuarios con roles específicos.

    Uso:
        @app.route('/admin/empleados')
        @login_required
        @requires_role('admin')
        def gestionar_empleados():
            ...

        @app.route('/reservas')
        @login_required
        @requires_role('admin', 'staff')
        def ver_reservas():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión para acceder a esta página.', 'error')
                return redirect(url_for('login'))

            if current_user.role not in roles:
                flash('No tienes permisos para acceder a esta página.', 'error')
                return redirect(url_for('dashboard'))

            if not current_user.is_active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def requires_admin(f):
    """Atajo para @requires_role('admin')."""
    return requires_role(UserRole.ADMIN)(f)


def requires_plan(*plans):
    """
    Decorador que restringe el acceso según el plan del negocio.

    Uso:
        @app.route('/estadisticas-avanzadas')
        @login_required
        @requires_plan('pro', 'elite')
        def estadisticas_avanzadas():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión.', 'error')
                return redirect(url_for('login'))

            plan = current_user.negocio.plan or 'trial'

            if plan not in plans:
                flash('Esta función requiere un plan superior. Considera actualizar tu plan.', 'warning')
                return redirect(url_for('upgrade'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# === SISTEMA DE AUDITORÍA ===

def log_audit(action, entity_type=None, entity_id=None, description=None,
              old_values=None, new_values=None, user=None, negocio=None):
    """
    Registra una acción en el log de auditoría.

    Args:
        action: Tipo de acción (AuditAction)
        entity_type: Tipo de entidad ('usuario', 'reserva', 'cliente', etc.)
        entity_id: ID de la entidad afectada
        description: Descripción legible de la acción
        old_values: Diccionario con valores anteriores (opcional)
        new_values: Diccionario con valores nuevos (opcional)
        user: Usuario que realizó la acción (default: current_user)
        negocio: Negocio afectado (default: user.negocio)

    Returns:
        AuditLog instance o None si falla
    """
    try:
        # Obtener usuario actual si no se proporciona
        if user is None:
            try:
                user = current_user if current_user.is_authenticated else None
            except:
                user = None

        # Obtener negocio
        if negocio is None and user is not None:
            negocio = user.negocio

        # Crear el registro
        log = AuditLog(
            negocio_id=negocio.id if negocio else None,
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )

        # Guardar cambios si se proporcionan
        if old_values is not None or new_values is not None:
            log.set_changes(old_values or {}, new_values or {})

        # Obtener IP y User-Agent
        try:
            log.ip_address = request.remote_addr
            log.user_agent = request.user_agent.string[:255] if request.user_agent else None
        except:
            log.ip_address = None
            log.user_agent = None

        db.session.add(log)
        db.session.commit()

        return log

    except Exception as e:
        print(f"Error en log_audit: {e}")
        # No lanzar excepción para no interrumpir la operación principal
        return None


def audit_action(action, entity_type=None):
    """
    Decorador que registra automáticamente la acción de auditoría.

    Uso:
        @app.route('/api/clientes', methods=['POST'])
        @login_required
        @audit_action(AuditAction.CLIENTE_CREADO, entity_type='cliente')
        def crear_cliente():
            # ... crear cliente ...
            # El ID del cliente creado se guardará en kwargs.get('entity_id')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ejecutar la función primero
            result = f(*args, **kwargs)

            # Intentar obtener entity_id del resultado si es un dict o modelo
            entity_id = kwargs.get('entity_id')
            if hasattr(result, 'id'):
                entity_id = result.id

            # Registrar auditoría
            log_audit(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id
            )

            return result
        return decorated_function
    return decorator


# === FUNCIONES AUXILIARES ===

def can_user_access_negocio(user, negocio_id):
    """
    Verifica si un usuario puede acceder a un negocio específico.
    Un usuario solo puede acceder a su propio negocio.
    """
    if not user or not user.is_authenticated:
        return False
    return user.negocio_id == negocio_id


def can_user_manage_users(user):
    """
    Verifica si un usuario puede gestionar otros usuarios.
    Solo el admin puede gestionar usuarios.
    """
    if not user or not user.is_authenticated:
        return False
    return user.role == UserRole.ADMIN and user.is_active


def check_user_limit(negocio):
    """
    Verifica si el negocio puede agregar más usuarios según su plan.
    Retorna (puede_agregar, cantidad_actual, limite)
    """
    from app import LIMITES_PLAN, get_limites

    limites = get_limites(negocio)
    if limites is None:
        return False, 0, 0

    max_users = limites.get('usuarios', 1)
    current_users = len([u for u in negocio.usuarios if u.is_active])

    return current_users < max_users, current_users, max_users


def get_audit_logs(negocio_id, limit=50, offset=0, action_filter=None):
    """
    Obtiene los logs de auditoría para un negocio.

    Args:
        negocio_id: ID del negocio
        limit: Máximo de registros a retornar
        offset: Desplazamiento para paginación
        action_filter: Filtrar por tipo de acción (opcional)

    Returns:
        Lista de AuditLog
    """
    query = AuditLog.query.filter_by(negocio_id=negocio_id)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    return query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


def get_audit_logs_count(negocio_id, action_filter=None):
    """Cuenta el total de logs de auditoría para paginación."""
    query = AuditLog.query.filter_by(negocio_id=negocio_id)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    return query.count()