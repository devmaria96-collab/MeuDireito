"""Confirmação de e-mail das contas já existentes antes deste recurso.

Revision ID: 20261119_0006
Revises: 20261119_0005
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261119_0006"
down_revision: str | None = "20261119_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("email_confirmado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("usuarios", sa.Column("confirmacao_motivo", sa.String(20), nullable=True))
    op.execute(
        "UPDATE usuarios SET email_confirmado_em = criado_em, confirmacao_motivo = 'conta_anterior' "
        "WHERE email_confirmado_em IS NULL"
    )
    op.create_table(
        "confirmacoes_email",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_confirmacoes_email_usuario_id", "confirmacoes_email", ["usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_confirmacoes_email_usuario_id", table_name="confirmacoes_email")
    op.drop_table("confirmacoes_email")
    op.drop_column("usuarios", "confirmacao_motivo")
    op.drop_column("usuarios", "email_confirmado_em")
