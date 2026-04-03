"""Agregar is_saas_admin y GlobalAuditLog

Revision ID: saas_admin_001
Revises:
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'saas_admin_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Agregar columna is_saas_admin a usuario
    op.add_column('usuario', sa.Column('is_saas_admin', sa.Boolean(), nullable=True, server_default='false'))

    # Crear tabla global_audit_log
    op.create_table(
        'global_audit_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('negocio_id', sa.Integer(), sa.ForeignKey('negocio.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('usuario.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # Crear índices
    op.create_index('idx_global_audit_negocio', 'global_audit_log', ['negocio_id'])
    op.create_index('idx_global_audit_timestamp', 'global_audit_log', ['timestamp'])


def downgrade():
    # Eliminar índices
    op.drop_index('idx_global_audit_timestamp', 'global_audit_log')
    op.drop_index('idx_global_audit_negocio', 'global_audit_log')

    # Eliminar tabla
    op.drop_table('global_audit_log')

    # Eliminar columna
    op.drop_column('usuario', 'is_saas_admin')