"""Acrescenta redefinição de senha e o registro mínimo de exclusão.

Revision ID: 20261119_0005
Revises: 20261118_0004
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_0005"
down_revision: str | None = "20261118_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "redefinicoes_senha",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_redefinicoes_senha_usuario_id", "redefinicoes_senha", ["usuario_id"])
    op.create_table(
        "registros_exclusao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("excluido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_registros_exclusao_email_hash", "registros_exclusao", ["email_hash"])


def downgrade() -> None:
    op.drop_index("ix_registros_exclusao_email_hash", table_name="registros_exclusao")
    op.drop_table("registros_exclusao")
    op.drop_index("ix_redefinicoes_senha_usuario_id", table_name="redefinicoes_senha")
    op.drop_table("redefinicoes_senha")
