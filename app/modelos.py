"""Tabelas de conta e do histórico autenticado."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    nome_exibicao: Mapped[str] = mapped_column(String(40))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    email_confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmacao_motivo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    perfil: Mapped[Perfil | None] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    sessoes: Mapped[list[Sessao]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    conversas: Mapped[list[ConversaRegistro]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    redefinicoes: Mapped[list[RedefinicaoSenha]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    confirmacoes: Mapped[list[ConfirmacaoEmail]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Perfil(Base):
    """Preferências da conta. A importação do navegador só ocorre com confirmação."""

    __tablename__ = "perfis"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, index=True
    )
    avatar_codigo: Mapped[str] = mapped_column(String(40), default="balanca")
    tipo_avatar: Mapped[str] = mapped_column(String(20), default="biblioteca")
    foto_referencia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    perfil_juridico: Mapped[str] = mapped_column(String(20), default="cidadao")
    tema: Mapped[str | None] = mapped_column(String(10), nullable=True)
    consentimento_sincronizacao: Mapped[bool] = mapped_column(Boolean, default=False)
    usuario: Mapped[Usuario] = relationship(back_populates="perfil")


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(64))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")


class RedefinicaoSenha(Base):
    """Pedido de nova senha. Só o hash do token fica gravado."""

    __tablename__ = "redefinicoes_senha"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped[Usuario] = relationship(back_populates="redefinicoes")


class ConfirmacaoEmail(Base):
    """Confirmação do endereço. Só o hash do token fica gravado."""

    __tablename__ = "confirmacoes_email"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped[Usuario] = relationship(back_populates="confirmacoes")


class RegistroExclusao(Base):
    """Registro mínimo da exclusão, sem conversa, nome ou e-mail em texto."""

    __tablename__ = "registros_exclusao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email_hash: Mapped[str] = mapped_column(String(64), index=True)
    excluido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConversaRegistro(Base):
    __tablename__ = "conversas"
    __table_args__ = (
        Index(
            "uq_conversas_usuario_origem",
            "usuario_id",
            "origem_local",
            unique=True,
            sqlite_where=text("origem_local IS NOT NULL"),
            postgresql_where=text("origem_local IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    titulo: Mapped[str] = mapped_column(String(80))
    tipo_documento: Mapped[str | None] = mapped_column(String(40), nullable=True)
    origem_local: Mapped[str | None] = mapped_column(String(80), nullable=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    usuario: Mapped[Usuario] = relationship(back_populates="conversas")
    mensagens: Mapped[list[MensagemRegistro]] = relationship(
        back_populates="conversa",
        cascade="all, delete-orphan",
        order_by="MensagemRegistro.ordem",
    )


class MensagemRegistro(Base):
    __tablename__ = "mensagens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversa_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("conversas.id", ondelete="CASCADE"), index=True)
    papel: Mapped[str] = mapped_column(String(20))
    conteudo: Mapped[str] = mapped_column(Text)
    ordem: Mapped[int] = mapped_column(Integer)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    conversa: Mapped[ConversaRegistro] = relationship(back_populates="mensagens")
    referencias: Mapped[list[ReferenciaRegistro]] = relationship(
        back_populates="mensagem",
        cascade="all, delete-orphan",
    )


class ReferenciaRegistro(Base):
    __tablename__ = "referencias_juridicas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mensagem_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("mensagens.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(40))
    tipo: Mapped[str] = mapped_column(String(20))
    verificada: Mapped[bool] = mapped_column(Boolean, default=False)
    norma: Mapped[str | None] = mapped_column(String(180), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ano: Mapped[str | None] = mapped_column(String(10), nullable=True)
    artigo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tribunal: Mapped[str | None] = mapped_column(String(80), nullable=True)
    processo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    relator: Mapped[str | None] = mapped_column(String(120), nullable=True)
    data_decisao: Mapped[str | None] = mapped_column(String(40), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    consultado_em: Mapped[str] = mapped_column(String(40))
    situacao: Mapped[str] = mapped_column(String(40))
    tipo_texto: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vigencia_confirmada: Mapped[bool] = mapped_column(Boolean, default=False)
    notas_fonte: Mapped[str] = mapped_column(Text, default="[]")
    aviso: Mapped[str] = mapped_column(Text)
    mensagem: Mapped[MensagemRegistro] = relationship(back_populates="referencias")
