"""
Rutas del Panel de Súper Administrador (SaaS Admin) para Reserfy.

Este módulo contiene todas las rutas protegidas para la gestión
global de la plataforma: negocios, usuarios, auditoría y estadísticas.
"""

import os
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc

# Crear Blueprint primero
saas_admin = Blueprint('saas_admin', __name__, url_prefix='/saas-admin')


# === Funciones auxiliares para importaciones diferidas ===

def _get_db():
    from app import db
    return db


def _get_models():
    from models import Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction
    return Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction


def _get_decorators():
    from decorators import requires_saas_admin, is_saas_admin, log_global_audit
    return requires_saas_admin, is_saas_admin, log_global_audit


def _get_subscription_utils():
    from utils.subscription import actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante
    return actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante


def _check_saas_admin():
    """Verifica si el usuario actual es SAAS Admin."""
    from decorators import is_saas_admin
    if not is_saas_admin(current_user):
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return False
    return True


# === DASHBOARD ===

@saas_admin.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal del Súper Admin con estadísticas globales."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante = _get_subscription_utils()

    # Estadísticas globales
    total_negocios = Negocio.query.count()
    total_usuarios = Usuario.query.count()
    total_clientes = Cliente.query.count()
    total_reservas = Reserva.query.count()

    # Negocios activos vs vencidos
    negocios_activos = 0
    negocios_vencidos = 0
    negocios = Negocio.query.all()
    for n in negocios:
        if plan_activo(n):
            negocios_activos += 1
        else:
            negocios_vencidos += 1

    # Negocios por plan
    negocios_por_plan = db.session.query(
        Negocio.plan, func.count(Negocio.id).label('total')
    ).group_by(Negocio.plan).all()
    planes_data = {p[0]: p[1] for p in negocios_por_plan}

    # Reservas de hoy
    hoy_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    hoy_fin = hoy_inicio + timedelta(days=1)
    reservas_hoy = Reserva.query.filter(
        Reserva.fecha_hora >= hoy_inicio,
        Reserva.fecha_hora < hoy_fin,
        Reserva.estado != 'cancelada'
    ).count()

    # Reservas del mes
    inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    reservas_mes = Reserva.query.filter(
        Reserva.fecha_hora >= inicio_mes,
        Reserva.estado != 'cancelada'
    ).count()

    # Últimos negocios y logs
    ultimos_negocios = Negocio.query.order_by(Negocio.id.desc()).limit(5).all()
    ultimos_logs = GlobalAuditLog.query.order_by(GlobalAuditLog.timestamp.desc()).limit(10).all()

    # Ingresos estimados
    ingresos_estimados = 0
    precios_plan = {'starter': 9.99, 'pro': 29.99, 'elite': 79.99}
    for n in negocios:
        if plan_activo(n) and n.plan in precios_plan:
            ingresos_estimados += precios_plan[n.plan]

    return render_template('saas_admin/dashboard.html',
        total_negocios=total_negocios,
        total_usuarios=total_usuarios,
        total_clientes=total_clientes,
        total_reservas=total_reservas,
        negocios_activos=negocios_activos,
        negocios_vencidos=negocios_vencidos,
        planes_data=planes_data,
        reservas_hoy=reservas_hoy,
        reservas_mes=reservas_mes,
        ingresos_estimados=round(ingresos_estimados, 2),
        ultimos_negocios=ultimos_negocios,
        ultimos_logs=ultimos_logs,
        plan_activo_fn=plan_activo,
        dias_restantes=dias_restantes_plan
    )


# === GESTIÓN DE NEGOCIOS ===

@saas_admin.route('/negocios')
@login_required
def negocios():
    """Lista todos los negocios con paginación y filtros."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante = _get_subscription_utils()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    plan_filter = request.args.get('plan', '')
    estado_filter = request.args.get('estado', '')
    busqueda = request.args.get('q', '').strip()

    query = Negocio.query

    if plan_filter:
        query = query.filter(Negocio.plan == plan_filter)

    if busqueda:
        query = query.filter(
            db.or_(
                Negocio.nombre.ilike(f'%{busqueda}%'),
                Negocio.email.ilike(f'%{busqueda}%')
            )
        )

    all_negocios = query.order_by(Negocio.id.desc()).all()

    if estado_filter == 'activo':
        all_negocios = [n for n in all_negocios if plan_activo(n)]
    elif estado_filter == 'vencido':
        all_negocios = [n for n in all_negocios if not plan_activo(n)]

    total = len(all_negocios)
    start = (page - 1) * per_page
    end = start + per_page
    negocios_pagina = all_negocios[start:end]

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages

    return render_template('saas_admin/negocios.html',
        negocios=negocios_pagina,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        total=total,
        plan_filter=plan_filter,
        estado_filter=estado_filter,
        busqueda=busqueda,
        plan_activo_fn=plan_activo,
        dias_restantes=dias_restantes_plan
    )


@saas_admin.route('/negocios/<int:negocio_id>')
@login_required
def detalle_negocio(negocio_id):
    """Ver detalles de un negocio específico."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante = _get_subscription_utils()

    negocio = Negocio.query.get_or_404(negocio_id)

    usuarios = Usuario.query.filter_by(negocio_id=negocio.id).all()
    clientes = Cliente.query.filter_by(negocio_id=negocio.id).count()
    servicios = Servicio.query.filter_by(negocio_id=negocio.id, activo=True).count()

    inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    reservas_mes = Reserva.query.filter(
        Reserva.negocio_id == negocio.id,
        Reserva.fecha_hora >= inicio_mes,
        Reserva.estado != 'cancelada'
    ).count()

    logs = GlobalAuditLog.query.filter_by(negocio_id=negocio.id).order_by(GlobalAuditLog.timestamp.desc()).limit(20).all()

    return render_template('saas_admin/detalle_negocio.html',
        negocio=negocio,
        usuarios=usuarios,
        total_clientes=clientes,
        total_servicios=servicios,
        reservas_mes=reservas_mes,
        logs=logs,
        plan_activo_fn=plan_activo,
        dias_restantes=dias_restantes_plan,
        formatear_tiempo=formatear_tiempo_restante
    )


@saas_admin.route('/negocios/<int:negocio_id>/cambiar-plan', methods=['POST'])
@login_required
def cambiar_plan_negocio(negocio_id):
    """Cambiar el plan de un negocio."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante = _get_subscription_utils()
    requires_saas_admin, is_saas_admin, log_global_audit = _get_decorators()

    negocio = Negocio.query.get_or_404(negocio_id)

    nuevo_plan = request.form.get('plan')
    nuevo_ciclo = request.form.get('ciclo', 'mensual')

    if nuevo_plan not in ['trial', 'starter', 'pro', 'elite']:
        flash('Plan inválido.', 'error')
        return redirect(url_for('saas_admin.detalle_negocio', negocio_id=negocio_id))

    plan_anterior = negocio.plan
    ciclo_anterior = negocio.plan_frecuencia

    actualizar_plan(negocio, nuevo_plan, nuevo_ciclo)
    db = _get_db()
    db.session.commit()

    log_global_audit(
        action=GlobalAuditAction.PLAN_CAMBIADO,
        negocio_id=negocio.id,
        entity_type='negocio',
        entity_id=negocio.id,
        description=f"Plan cambiado de {plan_anterior} a {nuevo_plan} ({nuevo_ciclo})",
        details={
            'plan_anterior': plan_anterior,
            'ciclo_anterior': ciclo_anterior,
            'nuevo_plan': nuevo_plan,
            'nuevo_ciclo': nuevo_ciclo,
            'admin_email': current_user.email
        }
    )

    flash(f'Plan actualizado a {nuevo_plan.upper()} ({nuevo_ciclo}).', 'success')
    return redirect(url_for('saas_admin.detalle_negocio', negocio_id=negocio_id))


@saas_admin.route('/negocios/<int:negocio_id>/suspender', methods=['POST'])
@login_required
def suspender_negocio(negocio_id):
    """Suspender un negocio."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    requires_saas_admin, is_saas_admin, log_global_audit = _get_decorators()

    negocio = Negocio.query.get_or_404(negocio_id)
    vencimiento_anterior = negocio.plan_vence

    negocio.plan_vence = datetime.now(timezone.utc) - timedelta(days=1)
    db = _get_db()
    db.session.commit()

    log_global_audit(
        action=GlobalAuditAction.NEGOCIO_SUSPENDIDO,
        negocio_id=negocio.id,
        entity_type='negocio',
        entity_id=negocio.id,
        description=f"Negocio '{negocio.nombre}' suspendido",
        details={'vencimiento_anterior': str(vencimiento_anterior), 'admin_email': current_user.email}
    )

    flash(f'Negocio "{negocio.nombre}" suspendido correctamente.', 'success')
    return redirect(url_for('saas_admin.detalle_negocio', negocio_id=negocio_id))


@saas_admin.route('/negocios/<int:negocio_id>/activar', methods=['POST'])
@login_required
def activar_negocio(negocio_id):
    """Activar un negocio suspendido."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    requires_saas_admin, is_saas_admin, log_global_audit = _get_decorators()

    negocio = Negocio.query.get_or_404(negocio_id)

    negocio.plan_vence = datetime.now(timezone.utc) + timedelta(days=30)
    db = _get_db()
    db.session.commit()

    log_global_audit(
        action=GlobalAuditAction.NEGOCIO_ACTIVADO,
        negocio_id=negocio.id,
        entity_type='negocio',
        entity_id=negocio.id,
        description=f"Negocio '{negocio.nombre}' activado",
        details={'admin_email': current_user.email}
    )

    flash(f'Negocio "{negocio.nombre}" activado correctamente.', 'success')
    return redirect(url_for('saas_admin.detalle_negocio', negocio_id=negocio_id))


# === GESTIÓN DE USUARIOS ===

@saas_admin.route('/usuarios')
@login_required
def usuarios():
    """Lista todos los usuarios de la plataforma."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    page = request.args.get('page', 1, type=int)
    per_page = 25
    busqueda = request.args.get('q', '').strip()
    rol_filter = request.args.get('rol', '')

    query = Usuario.query

    if busqueda:
        query = query.filter(
            db.or_(
                Usuario.email.ilike(f'%{busqueda}%'),
                Usuario.nombre.ilike(f'%{busqueda}%')
            )
        )

    if rol_filter:
        query = query.filter(Usuario.role == rol_filter)

    pagination = query.order_by(Usuario.id.desc()).paginate(page=page, per_page=per_page)

    return render_template('saas_admin/usuarios.html',
        usuarios=pagination.items,
        page=page,
        total_pages=pagination.pages,
        has_prev=pagination.has_prev,
        has_next=pagination.has_next,
        total=pagination.total,
        busqueda=busqueda,
        rol_filter=rol_filter
    )


@saas_admin.route('/usuarios/<int:usuario_id>')
@login_required
def detalle_usuario(usuario_id):
    """Ver detalles de un usuario específico."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    usuario = Usuario.query.get_or_404(usuario_id)
    logs = GlobalAuditLog.query.filter_by(user_id=usuario.id).order_by(GlobalAuditLog.timestamp.desc()).limit(20).all()

    return render_template('saas_admin/detalle_usuario.html',
        usuario=usuario,
        logs=logs
    )


@saas_admin.route('/usuarios/<int:usuario_id>/hacer-admin', methods=['POST'])
@login_required
def hacer_saas_admin(usuario_id):
    """Convertir usuario en Súper Admin."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    requires_saas_admin, is_saas_admin, log_global_audit = _get_decorators()

    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.is_saas_admin:
        flash('Este usuario ya es Súper Admin.', 'warning')
        return redirect(url_for('saas_admin.detalle_usuario', usuario_id=usuario_id))

    usuario.is_saas_admin = True
    db = _get_db()
    db.session.commit()

    log_global_audit(
        action=GlobalAuditAction.SISTEMA_CONFIG,
        entity_type='usuario',
        entity_id=usuario.id,
        description=f"Usuario '{usuario.email}' convertido en Súper Admin",
        details={'admin_email': current_user.email}
    )

    flash(f'Usuario {usuario.email} ahora es Súper Admin.', 'success')
    return redirect(url_for('saas_admin.detalle_usuario', usuario_id=usuario_id))


@saas_admin.route('/usuarios/<int:usuario_id>/quitar-admin', methods=['POST'])
@login_required
def quitar_saas_admin(usuario_id):
    """Quitar permisos de Súper Admin."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()
    requires_saas_admin, is_saas_admin, log_global_audit = _get_decorators()

    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.id == current_user.id:
        flash('No puedes quitarte tus propios permisos de Súper Admin.', 'error')
        return redirect(url_for('saas_admin.detalle_usuario', usuario_id=usuario_id))

    usuario.is_saas_admin = False
    db = _get_db()
    db.session.commit()

    log_global_audit(
        action=GlobalAuditAction.SISTEMA_CONFIG,
        entity_type='usuario',
        entity_id=usuario.id,
        description=f"Permisos de Súper Admin removidos de '{usuario.email}'",
        details={'admin_email': current_user.email}
    )

    flash(f'Permisos de Súper Admin removidos de {usuario.email}.', 'success')
    return redirect(url_for('saas_admin.detalle_usuario', usuario_id=usuario_id))


# === LOGS DE AUDITORÍA ===

@saas_admin.route('/logs')
@login_required
def logs():
    """Visor de logs de auditoría global."""
    if not _check_saas_admin():
        return redirect(url_for('dashboard'))

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    action_filter = request.args.get('action', '')
    negocio_id = request.args.get('negocio_id', '', type=int)
    user_id = request.args.get('user_id', '', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = GlobalAuditLog.query

    if action_filter:
        query = query.filter(GlobalAuditLog.action == action_filter)
    if negocio_id:
        query = query.filter(GlobalAuditLog.negocio_id == negocio_id)
    if user_id:
        query = query.filter(GlobalAuditLog.user_id == user_id)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(GlobalAuditLog.timestamp >= dt_from)
        except:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(GlobalAuditLog.timestamp < dt_to)
        except:
            pass

    pagination = query.order_by(GlobalAuditLog.timestamp.desc()).paginate(page=page, per_page=per_page)

    acciones = [
        GlobalAuditAction.NEGOCIO_CREADO,
        GlobalAuditAction.NEGOCIO_SUSPENDIDO,
        GlobalAuditAction.NEGOCIO_ACTIVADO,
        GlobalAuditAction.PLAN_CAMBIADO,
        GlobalAuditAction.USUARIO_REGISTRADO,
        GlobalAuditAction.SAAS_ADMIN_LOGIN,
        GlobalAuditAction.SISTEMA_CONFIG,
    ]

    negocios_lista = Negocio.query.order_by(Negocio.nombre).all()

    return render_template('saas_admin/logs.html',
        logs=pagination.items,
        page=page,
        total_pages=pagination.pages,
        has_prev=pagination.has_prev,
        has_next=pagination.has_next,
        total=pagination.total,
        action_filter=action_filter,
        negocio_id=negocio_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        acciones=acciones,
        negocios_lista=negocios_lista,
        GlobalAuditAction=GlobalAuditAction
    )


@saas_admin.route('/api/logs/<int:log_id>')
@login_required
def api_detalle_log(log_id):
    """API para obtener detalles de un log específico."""
    if not _check_saas_admin():
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    log = GlobalAuditLog.query.get_or_404(log_id)

    return jsonify({
        'id': log.id,
        'action': log.action,
        'description': log.description,
        'details': log.get_details(),
        'ip_address': log.ip_address,
        'user_agent': log.user_agent,
        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
        'negocio_id': log.negocio_id,
        'user_id': log.user_id,
        'entity_type': log.entity_type,
        'entity_id': log.entity_id
    })


# === API PARA BÚSQUEDA ===

@saas_admin.route('/api/negocios/buscar')
@login_required
def api_buscar_negocios():
    """API para buscar negocios."""
    if not _check_saas_admin():
        return jsonify({'negocios': []})

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'negocios': []})

    negocios = Negocio.query.filter(
        db.or_(
            Negocio.nombre.ilike(f'%{q}%'),
            Negocio.email.ilike(f'%{q}%')
        )
    ).limit(10).all()

    return jsonify({
        'negocios': [{
            'id': n.id,
            'nombre': n.nombre,
            'email': n.email,
            'plan': n.plan
        } for n in negocios]
    })


@saas_admin.route('/api/usuarios/buscar')
@login_required
def api_buscar_usuarios():
    """API para buscar usuarios."""
    if not _check_saas_admin():
        return jsonify({'usuarios': []})

    db = _get_db()
    Negocio, Usuario, Cliente, Reserva, Servicio, GlobalAuditLog, GlobalAuditAction = _get_models()

    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'usuarios': []})

    usuarios = Usuario.query.filter(
        db.or_(
            Usuario.email.ilike(f'%{q}%'),
            Usuario.nombre.ilike(f'%{q}%')
        )
    ).limit(10).all()

    return jsonify({
        'usuarios': [{
            'id': u.id,
            'email': u.email,
            'nombre': u.nombre,
            'negocio_id': u.negocio_id
        } for u in usuarios]
    })