"""Histórico da conta. Cada operação confirma o dono da conversa."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.agente import carregar_chave_gemini, responder
from app.historico import (
    conversa_do_usuario,
    excluir,
    excluir_todas,
    importar,
    listar,
    preparar_pergunta,
    registrar_resposta,
    renomear,
    serializar,
)
from app.limite import consumir
from app.rotas_conta import _banco, _exigir_csrf, _usuario_da_sessao

router = APIRouter(prefix="/conta", tags=["historico"])
logger = logging.getLogger("meu_direito")


class PerguntaConta(BaseModel):
    pergunta: str = Field(min_length=1, max_length=8000)
    conversa_id: uuid.UUID | None = None
    titulo: str | None = Field(default=None, max_length=80)
    perfil: Literal["estudante", "profissional", "cidadao"] | None = None
    tipo_documento: Literal[
        "peticao_inicial",
        "contrato",
        "notificacao",
        "requerimento",
        "declaracao",
        "parecer",
        "resumo",
    ] | None = None


class RenomearEntrada(BaseModel):
    titulo: str = Field(min_length=1, max_length=80)


class MensagemImportada(BaseModel):
    papel: Literal["usuario", "agente"]
    conteudo: str = Field(min_length=1, max_length=20_000)
    referencias: list[dict[str, Any]] = Field(default_factory=list, max_length=8)


class ConversaImportada(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    titulo: str = Field(default="Conversa", max_length=80)
    tipo_documento: str | None = Field(default=None, max_length=40)
    mensagens: list[MensagemImportada] = Field(min_length=1, max_length=80)


class ImportacaoEntrada(BaseModel):
    conversas: list[ConversaImportada] = Field(max_length=30)


def _limitar_pesquisa(pedido: Request) -> None:
    origem = pedido.client.host if pedido.client else "local"
    if not consumir(origem):
        raise HTTPException(status_code=429, detail="Muitas consultas em sequência. Aguarde um minuto e tente de novo.")


def _conversa_ou_404(db, usuario, conversa_id: uuid.UUID):
    conversa = conversa_do_usuario(db, usuario, conversa_id)
    if conversa is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conversa


@router.get("/conversas")
def listar_conversas(pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, _sessao = _usuario_da_sessao(pedido, db)
        return {"conversas": [serializar(item, completa=False) for item in listar(db, usuario)]}
    finally:
        db.close()


@router.post("/conversas/perguntar")
async def perguntar(entrada: PerguntaConta, pedido: Request) -> dict[str, object]:
    _limitar_pesquisa(pedido)
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        try:
            conversa = preparar_pergunta(
                db,
                usuario,
                conversa_id=entrada.conversa_id,
                pergunta=entrada.pergunta,
                titulo=entrada.titulo,
                tipo_documento=entrada.tipo_documento,
            )
        except LookupError:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.") from None
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None

        from app.cota_gemini import exigir_cota_gemini

        exigir_cota_gemini(pedido.client.host if pedido.client else "local")
        carregar_chave_gemini()
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail={
                    "mensagem": "Defina GEMINI_API_KEY no arquivo .env antes de conversar com o agente.",
                    "conversa": serializar(conversa, completa=True),
                },
            )
        try:
            texto, consultas = await responder(entrada.pergunta.strip(), entrada.perfil, entrada.tipo_documento)
        except Exception as erro:
            from app.main import _detalhe_seguro

            status, detalhe = _detalhe_seguro(erro)
            logger.warning("Falha ao pesquisar na conta: %s, HTTP %s", type(erro).__name__, status)
            raise HTTPException(
                status_code=status,
                detail={"mensagem": detalhe, "conversa": serializar(conversa, completa=True)},
            ) from None
        try:
            completa = registrar_resposta(db, usuario, conversa, texto, consultas)
        except ValueError as erro:
            raise HTTPException(
                status_code=422,
                detail={"mensagem": str(erro), "conversa": serializar(conversa, completa=True)},
            ) from None
        logger.info("Pesquisa da conta concluída")
        return {"conversa": serializar(completa, completa=True)}
    finally:
        db.close()


@router.post("/conversas/importar")
def importar_conversas(entrada: ImportacaoEntrada, pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        try:
            return importar(db, usuario, [item.model_dump() for item in entrada.conversas])
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
    finally:
        db.close()


@router.delete("/conversas", status_code=204)
def apagar_historico(pedido: Request) -> Response:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        excluir_todas(db, usuario)
        return Response(status_code=204)
    finally:
        db.close()


@router.get("/conversas/{conversa_id}")
def ler_conversa(conversa_id: uuid.UUID, pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, _sessao = _usuario_da_sessao(pedido, db)
        return {"conversa": serializar(_conversa_ou_404(db, usuario, conversa_id), completa=True)}
    finally:
        db.close()


@router.patch("/conversas/{conversa_id}")
def renomear_conversa(conversa_id: uuid.UUID, entrada: RenomearEntrada, pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        conversa = _conversa_ou_404(db, usuario, conversa_id)
        try:
            atualizada = renomear(db, conversa, entrada.titulo)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
        return {"conversa": serializar(atualizada, completa=False)}
    finally:
        db.close()


@router.delete("/conversas/{conversa_id}", status_code=204)
def apagar_conversa(conversa_id: uuid.UUID, pedido: Request) -> Response:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        excluir(db, _conversa_ou_404(db, usuario, conversa_id))
        return Response(status_code=204)
    finally:
        db.close()
