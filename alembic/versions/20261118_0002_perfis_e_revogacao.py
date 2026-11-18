"""Separa perfis e registra revogação de sessão, sem apagar contas.

Revision ID: 20261118_0002
Revises: 20261116_0001
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0002"
down_revision: str | None = "20261116_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "perfis",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("avatar_codigo", sa.String(40), nullable=False),
        sa.Column("tipo_avatar", sa.String(20), nullable=False),
        sa.Column("foto_referencia", sa.String(80), nullable=True),
        sa.Column("perfil_juridico", sa.String(20), nullable=False),
        sa.Column("tema", sa.String(10), nullable=True),
        sa.Column("consentimento_sincronizacao", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_perfis_usuario_id", "perfis", ["usuario_id"], unique=True)
    op.execute(
        """
        INSERT INTO perfis (
            id, usuario_id, avatar_codigo, tipo_avatar, foto_referencia,
            perfil_juridico, tema, consentimento_sincronizacao
        )
        SELECT
            gen_random_uuid(),
            id,
            avatar_codigo,
            tipo_avatar,
            CASE
                WHEN tem_imagem THEN replace(id::text, '-', '') || '.webp'
                ELSE NULL
            END,
            perfil_juridico,
            tema,
            false
        FROM usuarios
        """
    )
    op.add_column("sessoes", sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.execute(
        """
        UPDATE usuarios AS u
        SET
            avatar_codigo = p.avatar_codigo,
            tipo_avatar = p.tipo_avatar,
            tem_imagem = p.foto_referencia IS NOT NULL,
            perfil_juridico = p.perfil_juridico,
            tema = p.tema
        FROM perfis AS p
        WHERE p.usuario_id = u.id
        """
    )
    op.drop_column("sessoes", "revogada_em")
    op.drop_index("ix_perfis_usuario_id", table_name="perfis")
    op.drop_table("perfis")
