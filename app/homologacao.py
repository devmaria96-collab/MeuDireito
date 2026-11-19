"""Acesso privado da homologação.

Em desenvolvimento e em produção a pesquisa pública continua aberta.
Em homologação, ou com AMBIENTE irreconhecível, a API só responde
depois de um cookie emitido por este módulo. A senha fica no ambiente,
não no repositório, e o cookie guarda só um HMAC.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.limite import consumir
from app.publicacao import cookie_samesite, cookie_seguro

logger = logging.getLogger("meu_direito")

COOKIE_ACESSO = "md_acesso"
MENSAGEM_TOKEN = b"md-acesso-homologacao-v1"
_DURACAO = 12 * 3600
_MINIMO = 16
_MENSAGEM_AUSENTE = "A homologação exige o acesso privado antes de usar a pesquisa ou a conta."
_MENSAGEM_INCOMPLETA = (
    "O acesso da homologação não está configurado. Defina ACESSO_HOMOLOGACAO com pelo menos 16 caracteres."
)
_MENSAGEM_RECUSADA = "A senha de acesso da homologação está incorreta."

router = APIRouter(tags=["homologacao"])


class AcessoEntrada(BaseModel):
    senha: str = Field(min_length=1, max_length=128)


class DestinoBanco:
    def __init__(self, esquema: str, host: str, porta: int | None, banco: str) -> None:
        self.esquema = esquema
        self.host = host
        self.porta = porta
        self.banco = banco

    def resumo(self) -> str:
        porta = str(self.porta) if self.porta else "-"
        return f"esquema={self.esquema or '-'} host={self.host or '-'} porta={porta} banco={self.banco or '-'}"


def ambiente() -> str:
    valor = os.getenv("AMBIENTE", "").strip().lower()
    if valor in {"", "desenvolvimento", "dev"}:
        return "desenvolvimento"
    if valor in {"homologacao", "homologação"}:
        return "homologacao"
    if valor in {"producao", "produção", "prod"}:
        return "producao"
    return "invalido"


def acesso_exigido() -> bool:
    return ambiente() in {"homologacao", "invalido"}


def segredo_configurado() -> str | None:
    valor = os.getenv("ACESSO_HOMOLOGACAO", "").strip()
    if len(valor) < _MINIMO:
        return None
    return valor


def token_de_acesso(segredo: str) -> str:
    return hmac.new(segredo.encode(), MENSAGEM_TOKEN, hashlib.sha256).hexdigest()


def url_normalizada(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def descrever_destino(url: str) -> DestinoBanco:
    """Host, porta e nome do banco. Usuário e senha não entram no resumo."""
    analisada = urlparse(url_normalizada(url))
    banco = analisada.path.lstrip("/").split("?", 1)[0]
    return DestinoBanco(analisada.scheme, analisada.hostname or "", analisada.port, banco)


def eh_banco_de_desenvolvimento(url: str) -> bool:
    destino = descrever_destino(url)
    return destino.host.lower() in {"127.0.0.1", "localhost", "::1"} and destino.banco == "meudireito"


def migracao_de_postgres_permitida(url: str) -> tuple[bool, str]:
    """Homologação não migra sozinha nem aponta para o banco local já usado."""
    atual = ambiente()
    if atual == "invalido":
        return False, "AMBIENTE inválido. Nada foi migrado."
    if atual != "homologacao":
        return True, ""
    normal = url_normalizada(url)
    if not normal.startswith("postgresql"):
        return False, "A homologação só migra PostgreSQL. Nada foi migrado."
    if eh_banco_de_desenvolvimento(normal):
        return False, "Migração recusada: o destino é o banco local de desenvolvimento. Nada foi migrado."
    if os.getenv("CONFIRMAR_MIGRACAO_HOMOLOGACAO", "").strip().lower() not in {"1", "true"}:
        return False, "Migração de homologação aguardando CONFIRMAR_MIGRACAO_HOMOLOGACAO=1. Nada foi migrado."
    return True, ""


def _cookie_do_cabecalho(cabecalho: str | None) -> str | None:
    if not cabecalho:
        return None
    prefixo = COOKIE_ACESSO + "="
    for parte in cabecalho.split(";"):
        pedaco = parte.strip()
        if pedaco.startswith(prefixo):
            return pedaco[len(prefixo) :]
    return None


def cookie_liberado(cabecalho: str | None) -> bool:
    segredo = segredo_configurado()
    if not segredo:
        return False
    valor = _cookie_do_cabecalho(cabecalho)
    if not valor:
        return False
    esperado = token_de_acesso(segredo)
    if len(valor) != len(esperado):
        return False
    return secrets.compare_digest(valor, esperado)


def _cabecalho_cookie(scope: dict) -> str | None:  # type: ignore[type-arg]
    for chave, valor in scope.get("headers", []):
        if chave == b"cookie":
            return valor.decode("latin-1")
    return None


def _caminho(scope: dict) -> str:  # type: ignore[type-arg]
    caminho = scope.get("path", "/") or "/"
    if caminho != "/":
        caminho = caminho.rstrip("/")
    return caminho


class AcessoHomologacaoMiddleware:
    """Recusa a API, inclusive a pesquisa, quando a homologação não foi liberada."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        self.app = app

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope["type"] != "http" or not acesso_exigido():
            await self.app(scope, receive, send)
            return
        metodo = scope.get("method", "GET")
        if metodo == "OPTIONS":
            await self.app(scope, receive, send)
            return
        caminho = _caminho(scope)
        if (metodo, caminho) in {
            ("GET", "/saude"),
            ("GET", "/acesso/homologacao"),
            ("POST", "/acesso/homologacao"),
            ("POST", "/acesso/homologacao/sair"),
        }:
            await self.app(scope, receive, send)
            return
        if segredo_configurado() is None or not cookie_liberado(_cabecalho_cookie(scope)):
            if segredo_configurado() is None:
                status = 503
                detalhe = _MENSAGEM_INCOMPLETA
            else:
                status = 403
                detalhe = _MENSAGEM_AUSENTE
            logger.info("Acesso de homologação recusado.")
            resposta = JSONResponse(status_code=status, content={"detail": detalhe})
            await resposta(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _origem(pedido: Request) -> str:
    return pedido.client.host if pedido.client else "local"


def _definir_cookie(resposta: Response, pedido: Request, segredo: str) -> None:
    seguro = cookie_seguro(pedido.url.scheme)
    resposta.set_cookie(
        COOKIE_ACESSO,
        token_de_acesso(segredo),
        httponly=True,
        secure=seguro,
        samesite=cookie_samesite(seguro),
        max_age=_DURACAO,
        path="/",
    )


def _estado(pedido: Request) -> dict[str, object]:
    exigido = acesso_exigido()
    configurado = segredo_configurado() is not None
    liberado = (not exigido) or (configurado and cookie_liberado(pedido.headers.get("cookie")))
    return {
        "exigido": exigido,
        "liberado": liberado,
        "configurado": (not exigido) or configurado,
        "ambiente": ambiente(),
    }


@router.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/acesso/homologacao")
def ler_acesso(pedido: Request) -> dict[str, object]:
    return _estado(pedido)


@router.post("/acesso/homologacao")
def entrar_acesso(entrada: AcessoEntrada, pedido: Request, resposta: Response) -> dict[str, object]:
    if not acesso_exigido():
        raise HTTPException(status_code=404, detail="O acesso privado não se aplica a este ambiente.")
    if not consumir(f"acesso:{_origem(pedido)}", limite=8, janela=600):
        raise HTTPException(status_code=429, detail="Muitas tentativas de acesso. Aguarde dez minutos.")
    segredo = segredo_configurado()
    if segredo is None:
        raise HTTPException(status_code=503, detail=_MENSAGEM_INCOMPLETA)
    informada = hashlib.sha256(entrada.senha.encode()).digest()
    esperada = hashlib.sha256(segredo.encode()).digest()
    if not secrets.compare_digest(informada, esperada):
        raise HTTPException(status_code=401, detail=_MENSAGEM_RECUSADA)
    _definir_cookie(resposta, pedido, segredo)
    return {"liberado": True}


@router.post("/acesso/homologacao/sair")
def sair_acesso(pedido: Request, resposta: Response) -> dict[str, bool]:
    seguro = cookie_seguro(pedido.url.scheme)
    resposta.delete_cookie(COOKIE_ACESSO, path="/", secure=seguro, samesite=cookie_samesite(seguro))
    return {"liberado": False}
