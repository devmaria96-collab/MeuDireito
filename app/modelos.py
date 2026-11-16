"""Tabelas de conta. O histórico de pesquisa não entra aqui."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    nome_exibicao: Mapped[str] = mapped_column(String(40))
    perfil_juridico: Mapped[str] = mapped_column(String(20), default="cidadao")
    tema: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tipo_avatar: Mapped[str] = mapped_column(String(20), default="biblioteca")
    avatar_codigo: Mapped[str] = mapped_column(String(40), default="balanca")
    tem_imagem: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sessoes: Mapped[list[Sessao]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(64))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")
