"""Conexão com o PostgreSQL das contas. A pesquisa funciona sem este banco."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.modelos import Base

logger = logging.getLogger("meu_direito")
_engine: Engine | None = None
_fabrica: sessionmaker[Session] | None = None
_disponivel = False


def url_do_banco() -> str:
    atual = os.getenv("DATABASE_URL", "").strip()
    if atual:
        return atual
    from dotenv import dotenv_values
    from pathlib import Path

    valores = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    return str(valores.get("DATABASE_URL") or "").strip()


def contas_disponiveis() -> bool:
    return _disponivel and _fabrica is not None


def redefinir_banco() -> None:
    """Fecha a conexão atual. Usado nos testes."""
    global _engine, _fabrica, _disponivel
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _fabrica = None
    _disponivel = False


def preparar_banco() -> None:
    """Abre o banco quando a URL existe. Uma falha aqui não derruba a pesquisa."""
    global _engine, _fabrica, _disponivel
    url = url_do_banco()
    if not url:
        _disponivel = False
        return
    from app.homologacao import migracao_de_postgres_permitida, url_normalizada

    if url.startswith(("postgres://", "postgresql://", "postgresql+")):
        url = url_normalizada(url)
        permitida, motivo = migracao_de_postgres_permitida(url)
        if not permitida:
            logger.warning("%s", motivo)
            _disponivel = False
            _engine = None
            _fabrica = None
            return
    try:
        if _engine is not None:
            _engine.dispose()
        argumentos: dict[str, object] = {}
        if url.startswith("postgresql"):
            argumentos["connect_timeout"] = 3
        opcoes: dict[str, object] = {"pool_pre_ping": True, "connect_args": argumentos}
        if url.startswith("sqlite"):
            opcoes["poolclass"] = NullPool
        engine = create_engine(url, **opcoes)
        if url.startswith("sqlite"):
            Base.metadata.create_all(engine)
        else:
            from alembic import command
            from alembic.config import Config

            from pathlib import Path

            configuracao = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            configuracao.set_main_option("sqlalchemy.url", url)
            command.upgrade(configuracao, "head")
        _engine = engine
        _fabrica = sessionmaker(bind=engine, expire_on_commit=False)
        _disponivel = True
    except Exception as erro:
        logger.warning("Contas indisponíveis: %s", type(erro).__name__)
        _disponivel = False
        _engine = None
        _fabrica = None


def sessao_banco() -> Iterator[Session]:
    if _fabrica is None:
        raise RuntimeError("Banco de contas indisponível.")
    with _fabrica() as sessao:
        yield sessao


def exigir_fabrica() -> sessionmaker[Session]:
    if _fabrica is None:
        raise RuntimeError("Banco de contas indisponível.")
    return _fabrica
