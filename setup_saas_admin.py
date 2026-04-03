"""
Script para configurar el primer Súper Administrador de la plataforma.
Este script permite designar un usuario como SAAS Admin.

Uso:
    python setup_saas_admin.py --email usuario@email.com

O con variable de entorno:
    SAAS_ADMIN_EMAIL=usuario@email.com python setup_saas_admin.py
"""

import os
import sys

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Usuario


def setup_saas_admin(email=None):
    """
    Configura un usuario como Súper Administrador.

    Args:
        email: Email del usuario a configurar como SAAS Admin.
               Si no se proporciona, usa la variable de entorno SAAS_ADMIN_EMAIL.
    """
    with app.app_context():
        # Obtener email de argumentos o variable de entorno
        if not email:
            email = os.getenv('SAAS_ADMIN_EMAIL')

        if not email:
            print("❌ Error: Debes proporcionar un email.")
            print("   Uso: python setup_saas_admin.py --email usuario@email.com")
            print("   O configurar la variable de entorno SAAS_ADMIN_EMAIL")
            return False

        # Buscar usuario
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            print(f"❌ Error: No existe un usuario con el email '{email}'")
            print("\nUsuarios disponibles:")
            usuarios = Usuario.query.all()
            for u in usuarios:
                print(f"  - {u.email} (ID: {u.id})")
            return False

        # Verificar si ya es SAAS Admin
        if usuario.is_saas_admin:
            print(f"✅ El usuario '{email}' ya es SAAS Admin.")
            return True

        # Configurar como SAAS Admin
        usuario.is_saas_admin = True
        db.session.commit()

        print("\n" + "=" * 60)
        print("   SAAS ADMIN CONFIGURADO")
        print("=" * 60)
        print(f"\n   Email: {usuario.email}")
        print(f"   Nombre: {usuario.nombre or 'No especificado'}")
        print(f"   Negocio: {usuario.negocio.nombre if usuario.negocio else 'N/A'}")
        print(f"   Usuario ID: {usuario.id}")
        print("\n" + "=" * 60)
        print("\n✅ El usuario ahora tiene acceso al panel de Súper Admin.")
        print("   Accede en: /saas-admin/dashboard")
        print("")

        return True


def list_saas_admins():
    """Lista todos los Súper Administradores."""
    with app.app_context():
        admins = Usuario.query.filter_by(is_saas_admin=True).all()

        if not admins:
            print("\n❌ No hay SAAS Admins configurados.")
            print("   Ejecuta: python setup_saas_admin.py --email usuario@email.com")
            return

        print("\n" + "=" * 60)
        print("   SAAS ADMINISTRADORES")
        print("=" * 60 + "\n")

        for admin in admins:
            print(f"  • {admin.email}")
            print(f"    ID: {admin.id}")
            print(f"    Negocio: {admin.negocio.nombre if admin.negocio else 'N/A'}")
            print("")


def remove_saas_admin(email):
    """Remueve los permisos de SAAS Admin de un usuario."""
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            print(f"❌ Error: No existe un usuario con el email '{email}'")
            return False

        if not usuario.is_saas_admin:
            print(f"ℹ️ El usuario '{email}' no es SAAS Admin.")
            return True

        usuario.is_saas_admin = False
        db.session.commit()

        print(f"✅ Permisos de SAAS Admin removidos de '{email}'")
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Gestionar SAAS Administradores')
    parser.add_argument('--email', '-e', help='Email del usuario a configurar')
    parser.add_argument('--list', '-l', action='store_true', help='Listar todos los SAAS Admins')
    parser.add_argument('--remove', '-r', help='Remover permisos de SAAS Admin')

    args = parser.parse_args()

    if args.list:
        list_saas_admins()
    elif args.remove:
        remove_saas_admin(args.remove)
    elif args.email:
        setup_saas_admin(args.email)
    else:
        # Intentar usar variable de entorno
        if os.getenv('SAAS_ADMIN_EMAIL'):
            setup_saas_admin()
        else:
            parser.print_help()
            print("\n💡 Ejemplo:")
            print("   python setup_saas_admin.py --email admin@reserfy.com")