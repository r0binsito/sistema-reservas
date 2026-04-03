"""
Decoradores de autorización y sistema de auditoría para Reserfy.
Incluye:
- @requires_role('admin') - Protege rutas según rol
- @requires_active_plan - Protege rutas si el plan está vencido
- @audit_action('ACCION') - Registra acciones automáticamente
- @requires_saas_admin - Protege rutas del Súper Admin
- Funciones auxiliares para verificación de permisos
"""

import os
from functools import wraps
from flask import request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user
from models import db, AuditLog, UserRole, AuditAction, GlobalAuditLog, GlobalAuditAction
from datetime import datetime, timezone
import json


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


# === SISTEMA DE SÚPER ADMIN (SaaS Admin) ===

def is_saas_admin(user=None):
    """
    Verifica si un usuario es Súper Administrador de la plataforma.

    Verifica:
    1. Flag is_saas_admin en la base de datos
    2. Variable de entorno SAAS_ADMIN_EMAIL coincide con el email

    Args:
        user: Usuario a verificar (default: current_user)

    Returns:
        bool: True si es Súper Admin, False si no
    """
    if user is None:
        try:
            user = current_user if current_user.is_authenticated else None
        except:
            return False

    if not user:
        return False

    # Verificar flag en la base de datos
    if hasattr(user, 'is_saas_admin') and user.is_saas_admin:
        return True

    # Verificar variable de entorno
    saas_admin_email = os.getenv('SAAS_ADMIN_EMAIL')
    if saas_admin_email and user.email:
        # Soportar múltiples emails separados por coma
        admin_emails = [e.strip().lower() for e in saas_admin_email.split(',')]
        if user.email.lower() in admin_emails:
            return True

    return False


def requires_saas_admin(f):
    """
    Decorador que restringe el acceso solo a Súper Administradores.

    Uso:
        @app.route('/saas-admin/dashboard')
        @login_required
        @requires_saas_admin
        def saas_admin_dashboard():
            ...

    Si el usuario no es Súper Admin:
    - Retorna 403 Forbidden para requests AJAX/API
    - Redirige al dashboard para requests normales
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para acceder.', 'error')
            return redirect(url_for('login'))

        if not is_saas_admin(current_user):
            # Si es request AJAX/API, retornar 403
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
            flash('No tienes permisos para acceder a esta sección.', 'error')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def log_global_audit(action, negocio_id=None, user_id=None, entity_type=None,
                     entity_id=None, description=None, details=None):
    """
    Registra una acción en el log de auditoría GLOBAL.

    Este log es visible solo para el Súper Admin y registra
    acciones de toda la plataforma.

    Args:
        action: Tipo de acción (GlobalAuditAction)
        negocio_id: ID del negocio afectado (opcional)
        user_id: ID del usuario que realizó la acción (default: current_user)
        entity_type: Tipo de entidad ('negocio', 'usuario', 'plan', etc.)
        entity_id: ID de la entidad afectada
        description: Descripción legible
        details: Diccionario con detalles adicionales

    Returns:
        GlobalAuditLog instance o None si falla
    """
    try:
        # Obtener usuario actual si no se proporciona
        if user_id is None:
            try:
                user_id = current_user.id if current_user.is_authenticated else None
            except:
                user_id = None

        # Crear el registro
        log = GlobalAuditLog(
            negocio_id=negocio_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )

        # Guardar detalles si se proporcionan
        if details:
            log.set_details(details)

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
        print(f"Error en log_global_audit: {e}")
        # No lanzar excepción para no interrumpir la operación principal
        return None


def get_global_audit_logs(limit=100, offset=0, action_filter=None,
                          negocio_id=None, user_id=None,
                          date_from=None, date_to=None):
    """
    Obtiene los logs de auditoría global con filtros.

    Args:
        limit: Máximo de registros a retornar
        offset: Desplazamiento para paginación
        action_filter: Filtrar por tipo de acción
        negocio_id: Filtrar por negocio
        user_id: Filtrar por usuario
        date_from: Fecha inicial (datetime)
        date_to: Fecha final (datetime)

    Returns:
        Lista de GlobalAuditLog
    """
    query = GlobalAuditLog.query

    if action_filter:
        query = query.filter(GlobalAuditLog.action == action_filter)

    if negocio_id:
        query = query.filter(GlobalAuditLog.negocio_id == negocio_id)

    if user_id:
        query = query.filter(GlobalAuditLog.user_id == user_id)

    if date_from:
        query = query.filter(GlobalAuditLog.timestamp >= date_from)

    if date_to:
        query = query.filter(GlobalAuditLog.timestamp <= date_to)

    return query.order_by(GlobalAuditLog.timestamp.desc()).offset(offset).limit(limit).all()


def get_global_audit_logs_count(action_filter=None, negocio_id=None,
                                user_id=None, date_from=None, date_to=None):
    """Cuenta el total de logs de auditoría global para paginación."""
    query = GlobalAuditLog.query

    if action_filter:
        query = query.filter(GlobalAuditLog.action == action_filter)

    if negocio_id:
        query = query.filter(GlobalAuditLog.negocio_id == negocio_id)

    if user_id:
        query = query.filter(GlobalAuditLog.user_id == user_id)

    if date_from:
        query = query.filter(GlobalAuditLog.timestamp >= date_from)

    if date_to:
        query = query.filter(GlobalAuditLog.timestamp <= date_to)

    return query.count()