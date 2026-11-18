"""Cria o histórico autenticado sem alterar as tabelas de conta.

Revision ID: 20261118_0004
Revises: 20261118_0003
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261118_0004"
down_revision: str | None = "20261118_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("titulo", sa.String(80), nullable=False),
        sa.Column("tipo_documento", sa.String(40), nullable=True),
        sa.Column("origem_local", sa.String(80), nullable=True),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversas_usuario_id", "conversas", ["usuario_id"])
    op.create_index("ix_conversas_atualizada_em", "conversas", ["atualizada_em"])
    op.create_index(
        "uq_conversas_usuario_origem",
        "conversas",
        ["usuario_id", "origem_local"],
        unique=True,
        postgresql_where=sa.text("origem_local IS NOT NULL"),
    )
    op.create_table(
        "mensagens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversa_id", sa.Uuid(), sa.ForeignKey("conversas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mensagens_conversa_id", "mensagens", ["conversa_id"])
    op.create_table(
        "referencias_juridicas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mensagem_id", sa.Uuid(), sa.ForeignKey("mensagens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("verificada", sa.Boolean(), nullable=False),
        sa.Column("norma", sa.String(180), nullable=True),
        sa.Column("numero", sa.String(40), nullable=True),
        sa.Column("ano", sa.String(10), nullable=True),
        sa.Column("artigo", sa.String(40), nullable=True),
        sa.Column("tribunal", sa.String(80), nullable=True),
        sa.Column("processo", sa.String(80), nullable=True),
        sa.Column("relator", sa.String(120), nullable=True),
        sa.Column("data_decisao", sa.String(40), nullable=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("consultado_em", sa.String(40), nullable=False),
        sa.Column("situacao", sa.String(40), nullable=False),
        sa.Column("tipo_texto", sa.String(80), nullable=True),
        sa.Column("vigencia_confirmada", sa.Boolean(), nullable=False),
        sa.Column("notas_fonte", sa.Text(), nullable=False),
        sa.Column("aviso", sa.Text(), nullable=False),
    )
    op.create_index("ix_referencias_juridicas_mensagem_id", "referencias_juridicas", ["mensagem_id"])


def downgrade() -> None:
    op.drop_index("ix_referencias_juridicas_mensagem_id", table_name="referencias_juridicas")
    op.drop_table("referencias_juridicas")
    op.drop_index("ix_mensagens_conversa_id", table_name="mensagens")
    op.drop_table("mensagens")
    op.drop_index("uq_conversas_usuario_origem", table_name="conversas")
    op.drop_index("ix_conversas_atualizada_em", table_name="conversas")
    op.drop_index("ix_conversas_usuario_id", table_name="conversas")
    op.drop_table("conversas")
