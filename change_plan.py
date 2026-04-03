"""
Script para cambiar el plan, ciclo y fecha de vencimiento de un negocio.
Actualizado para usar el sistema de suscripciones con plan_frecuencia y plan_vence.
"""
from app import app, db
from models import Negocio, GlobalAuditAction
from utils.subscription import actualizar_plan, plan_activo, dias_restantes_plan, formatear_tiempo_restante
from decorators import log_global_audit
from datetime import datetime, timezone

def actualizar_suscripcion():
    with app.app_context():
        # 1. Listar negocios
        negocios = Negocio.query.all()
        if not negocios:
            print("❌ No hay negocios en la base de datos.")
            return

        print("\n" + "=" * 60)
        print("   GESTIÓN DE SUSCRIPCIONES - RESERFY")
        print("=" * 60 + "\n")

        print("Negocios registrados:\n")
        print(f"{'ID':<4} {'Nombre':<25} {'Plan':<10} {'Ciclo':<10} {'Estado':<12} {'Vence':<12}")
        print("-" * 80)

        for n in negocios:
            vence = n.plan_vence.strftime('%d/%m/%Y') if n.plan_vence else "N/A"
            activo = "✅ Activo" if plan_activo(n) else "❌ Vencido"
            print(f"{n.id:<4} {n.nombre[:24]:<25} {n.plan.upper():<10} {n.plan_frecuencia or 'N/A':<10} {activo:<12} {vence:<12}")

        # 2. Selección de Negocio
        print("\n" + "-" * 60)
        try:
            id_input = int(input("\nID del negocio a modificar: "))
            negocio = Negocio.query.get(id_input)
            if not negocio:
                print("❌ ID no encontrado.")
                return
        except ValueError:
            print("❌ Entrada inválida.")
            return

        # 3. Selección de Plan
        print("\n--- SELECCIONA EL PLAN ---")
        print("  1. Trial (14 días gratis)")
        print("  2. Starter")
        print("  3. Pro")
        print("  4. Elite")
        p_opt = input("\nOpción: ").strip()
        planes = {'1': 'trial', '2': 'starter', '3': 'pro', '4': 'elite'}
        nuevo_plan = planes.get(p_opt)

        if not nuevo_plan:
            print("❌ Opción inválida.")
            return

        # 4. Selección de Periodo (Solo si no es Trial)
        nuevo_ciclo = "mensual"

        if nuevo_plan != 'trial':
            print("\n--- CICLO DE FACTURACIÓN ---")
            print("  1. Mensual (30 días)")
            print("  2. Anual (365 días) - 2 meses gratis")
            c_opt = input("\nOpción: ").strip()
            if c_opt == '2':
                nuevo_ciclo = "anual"
        else:
            nuevo_ciclo = 'unico'

        # 5. Confirmar cambios
        print("\n" + "=" * 60)
        print(f"  Negocio: {negocio.nombre}")
        print(f"  Plan actual: {negocio.plan.upper()} ({negocio.plan_frecuencia or 'N/A'})")
        print(f"  Nuevo plan: {nuevo_plan.upper()} ({nuevo_ciclo})")
        print("=" * 60)

        confirmar = input("\n¿Confirmar cambios? (s/n): ").strip().lower()
        if confirmar != 's':
            print("❌ Operación cancelada.")
            return

        # 6. Actualizar usando la función de utilidad
        try:
            plan_anterior = negocio.plan
            ciclo_anterior = negocio.plan_frecuencia

            actualizar_plan(negocio, nuevo_plan, nuevo_ciclo)
            db.session.commit()

            # Registrar en auditoría global
            log_global_audit(
                action=GlobalAuditAction.PLAN_CAMBIADO,
                negocio_id=negocio.id,
                entity_type='negocio',
                entity_id=negocio.id,
                description=f"Plan cambiado vía script: {plan_anterior} -> {nuevo_plan}",
                details={
                    'plan_anterior': plan_anterior,
                    'ciclo_anterior': ciclo_anterior,
                    'nuevo_plan': nuevo_plan,
                    'nuevo_ciclo': nuevo_ciclo
                }
            )

            dias = dias_restantes_plan(negocio)
            tiempo = formatear_tiempo_restante(dias)

            print(f"\n✅ ACTUALIZACIÓN EXITOSA")
            print(f"   Plan: {nuevo_plan.upper()} ({nuevo_ciclo})")
            print(f"   Vence: {negocio.plan_vence.strftime('%d/%m/%Y a las %H:%M')}")
            print(f"   Tiempo restante: {tiempo}\n")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al actualizar: {e}")


def ver_estado_suscripciones():
    """Muestra el estado de todas las suscripciones."""
    with app.app_context():
        negocios = Negocio.query.all()

        print("\n" + "=" * 80)
        print("   ESTADO DE SUSCRIPCIONES")
        print("=" * 80 + "\n")

        print(f"{'ID':<4} {'Nombre':<25} {'Plan':<10} {'Ciclo':<10} {'Estado':<12} {'Vence':<12} {'Días':<8}")
        print("-" * 90)

        for n in negocios:
            vence = n.plan_vence.strftime('%d/%m/%Y') if n.plan_vence else "N/A"
            activo = "✅ Activo" if plan_activo(n) else "❌ Vencido"
            dias = dias_restantes_plan(n)
            dias_str = str(dias) if dias is not None else "∞"
            print(f"{n.id:<4} {n.nombre[:24]:<25} {n.plan.upper():<10} {n.plan_frecuencia or 'N/A':<10} {activo:<12} {vence:<12} {dias_str:<8}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        ver_estado_suscripciones()
    else:
        actualizar_suscripcion()