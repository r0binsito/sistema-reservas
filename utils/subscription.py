"""
Utilidades para el sistema de suscripciones.

Funciones para verificar estado de plan, calcular días restantes,
y actualizar planes con fechas de vencimiento.
"""

from datetime import datetime, timedelta, timezone


# Duración de cada tipo de plan en días
PLAN_DURACION = {
    'trial': {
        'unico': 14,  # Trial dura 14 días
    },
    'starter': {
        'mensual': 30,
        'anual': 365,
    },
    'pro': {
        'mensual': 30,
        'anual': 365,
    },
    'elite': {
        'mensual': 30,
        'anual': 365,
    },
}


def plan_activo(negocio):
    """
    Verifica si el plan del negocio está activo (no ha vencido).

    Args:
        negocio: Objeto Negocio con campos plan, plan_vence, trial_expira

    Returns:
        bool: True si el plan está activo, False si ha vencido
    """
    # Trial sin fecha de expiración = activo (caso edge)
    if negocio.plan == 'trial' and not negocio.trial_expira and not negocio.plan_vence:
        return True

    # Usar plan_vence si existe, sino trial_expira para retrocompatibilidad
    fecha_vence = negocio.plan_vence or negocio.trial_expira

    if not fecha_vence:
        # Sin fecha de vencimiento = plan activo (para planes legacy)
        return True

    # Comparar fechas en UTC
    ahora = datetime.now(timezone.utc)

    # Convertir fecha_vence a UTC si no tiene timezone
    if fecha_vence.tzinfo is None:
        fecha_vence = fecha_vence.replace(tzinfo=timezone.utc)

    return ahora < fecha_vence


def dias_restantes_plan(negocio):
    """
    Calcula los días restantes hasta el vencimiento del plan.

    Args:
        negocio: Objeto Negocio

    Returns:
        int or None: Días restantes, None si no tiene fecha de vencimiento
                     o ya venció. Para trial, usa trial_expira.
    """
    # Usar plan_vence si existe, sino trial_expira
    fecha_vence = negocio.plan_vence or negocio.trial_expira

    if not fecha_vence:
        return None

    ahora = datetime.now(timezone.utc)

    # Convertir fecha_vence a UTC si no tiene timezone
    if fecha_vence.tzinfo is None:
        fecha_vence = fecha_vence.replace(tzinfo=timezone.utc)

    if ahora >= fecha_vence:
        return 0  # Ya venció

    delta = fecha_vence - ahora
    return max(0, delta.days)


def formatear_tiempo_restante(dias):
    """
    Formatea los días restantes en un string legible.

    Args:
        dias: Número de días (int)

    Returns:
        str: String formateado como "15 días", "3 meses", "1 año"
    """
    if dias is None:
        return "Sin límite"

    if dias <= 0:
        return "Vencido"

    if dias == 1:
        return "1 día"

    if dias < 30:
        return f"{dias} días"

    if dias < 365:
        meses = dias // 30
        if meses == 1:
            return "1 mes"
        return f"{meses} meses"

    años = dias // 365
    if años == 1:
        return "1 año"
    return f"{años} años"


def estado_plan(negocio):
    """
    Determina el estado del plan para mostrar indicadores en la UI.

    Args:
        negocio: Objeto Negocio

    Returns:
        str: 'vencido', 'proximo_vencer', 'activo'
    """
    dias = dias_restantes_plan(negocio)

    if dias is None:
        return 'activo'  # Sin fecha de vencimiento

    if dias <= 0:
        return 'vencido'

    if dias <= 5:
        return 'proximo_vencer'

    return 'activo'


def actualizar_plan(negocio, nuevo_plan, frecuencia='mensual'):
    """
    Actualiza el plan de un negocio con la fecha de vencimiento correcta.

    Args:
        negocio: Objeto Negocio
        nuevo_plan: String con el nuevo plan ('trial', 'starter', 'pro', 'elite')
        frecuencia: String con la frecuencia ('mensual', 'anual', 'unico')

    Returns:
        datetime: La nueva fecha de vencimiento
    """
    negocio.plan = nuevo_plan

    if nuevo_plan == 'trial':
        negocio.plan_frecuencia = 'unico'
        negocio.plan_vence = datetime.now(timezone.utc) + timedelta(days=14)
        negocio.trial_expira = negocio.plan_vence
    else:
        negocio.plan_frecuencia = frecuencia
        dias = PLAN_DURACION.get(nuevo_plan, {}).get(frecuencia, 30)
        negocio.plan_vence = datetime.now(timezone.utc) + timedelta(days=dias)

    return negocio.plan_vence


def proxima_fecha_vencimiento(plan, frecuencia='mensual'):
    """
    Calcula la fecha de vencimiento para un nuevo plan.

    Args:
        plan: Nombre del plan ('starter', 'pro', 'elite')
        frecuencia: 'mensual' o 'anual'

    Returns:
        datetime: Fecha de vencimiento
    """
    dias = PLAN_DURACION.get(plan, {}).get(frecuencia, 30)
    return datetime.now(timezone.utc) + timedelta(days=dias)