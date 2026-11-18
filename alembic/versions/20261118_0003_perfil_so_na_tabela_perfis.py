"""Remove do usuário as colunas de perfil já copiadas para perfis.

Revision ID: 20261118_0003
Revises: 20261118_0002
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0003"
down_revision: str | None = "20261118_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("usuarios", "tem_imagem")
    op.drop_column("usuarios", "avatar_codigo")
    op.drop_column("usuarios", "tipo_avatar")
    op.drop_column("usuarios", "tema")
    op.drop_column("usuarios", "perfil_juridico")


def downgrade() -> None:
    op.add_column("usuarios", sa.Column("perfil_juridico", sa.String(20), nullable=True))
    op.add_column("usuarios", sa.Column("tema", sa.String(10), nullable=True))
    op.add_column("usuarios", sa.Column("tipo_avatar", sa.String(20), nullable=True))
    op.add_column("usuarios", sa.Column("avatar_codigo", sa.String(40), nullable=True))
    op.add_column("usuarios", sa.Column("tem_imagem", sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE usuarios AS u
        SET
            perfil_juridico = p.perfil_juridico,
            tema = p.tema,
            tipo_avatar = p.tipo_avatar,
            avatar_codigo = p.avatar_codigo,
            tem_imagem = p.foto_referencia IS NOT NULL
        FROM perfis AS p
        WHERE p.usuario_id = u.id
        """
    )
    op.alter_column("usuarios", "perfil_juridico", nullable=False, server_default="cidadao")
    op.alter_column("usuarios", "tipo_avatar", nullable=False, server_default="biblioteca")
    op.alter_column("usuarios", "avatar_codigo", nullable=False, server_default="balanca")
    op.alter_column("usuarios", "tem_imagem", nullable=False, server_default=sa.false())
