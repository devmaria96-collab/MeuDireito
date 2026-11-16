"""Cria usuários e sessões.

Revision ID: 20261116_0001
Revises:
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261116_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("nome_exibicao", sa.String(40), nullable=False),
        sa.Column("perfil_juridico", sa.String(20), nullable=False),
        sa.Column("tema", sa.String(10), nullable=True),
        sa.Column("tipo_avatar", sa.String(20), nullable=False),
        sa.Column("avatar_codigo", sa.String(40), nullable=False),
        sa.Column("tem_imagem", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_table(
        "sessoes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf", sa.String(64), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessoes_usuario_id", "sessoes", ["usuario_id"])
    op.create_index("ix_sessoes_token_hash", "sessoes", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sessoes_token_hash", table_name="sessoes")
    op.drop_index("ix_sessoes_usuario_id", table_name="sessoes")
    op.drop_table("sessoes")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
