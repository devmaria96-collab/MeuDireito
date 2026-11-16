"""Rotas de conta. A pesquisa jurídica não depende delas."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.avatares import LIMITE_BYTES
from app.banco import contas_disponiveis, exigir_fabrica
from app.contas import (
    COOKIE,
    atualizar_perfil,
    autenticar,
    abrir_sessao,
    cadastrar,
    encerrar_sessao,
    imagem_do_usuario,
    nome_publico,
    retirar_imagem,
    definir_imagem,
    sessao_do_token,
)
from app.limite import consumir
from app.modelos import Sessao as SessaoModelo
from app.modelos import Usuario

router = APIRouter(prefix="/conta", tags=["conta"])
_DURACAO_COOKIE = 14 * 24 * 3600


class CadastroEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=8, max_length=128)
    confirmar_senha: str = Field(min_length=8, max_length=128)
    nome: str | None = Field(default=None, max_length=40)


class EntradaLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=128)


class PerfilEntrada(BaseModel):
    nome: str | None = Field(default=None, max_length=40)
    perfil_juridico: Literal["estudante", "profissional", "cidadao"] | None = None
    tema: Literal["claro", "escuro"] | None = None
    avatar_codigo: str | None = Field(default=None, max_length=40)


def _banco() -> Session:
    if not contas_disponiveis():
        raise HTTPException(status_code=503, detail="As contas estão indisponíveis neste momento. A pesquisa continua aberta.")
    return exigir_fabrica()()


def _limitar(pedido: Request, acao: str, limite: int) -> None:
    origem = pedido.client.host if pedido.client else "local"
    if not consumir(f"{acao}:{origem}", limite=limite, janela=600):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos e tente de novo.")


def _usuario_da_sessao(pedido: Request, db: Session) -> tuple[Usuario, SessaoModelo]:
    encontrada = sessao_do_token(db, pedido.cookies.get(COOKIE))
    if encontrada is None or encontrada.usuario is None:
        raise HTTPException(status_code=401, detail="Entre na sua conta para continuar.")
    return encontrada.usuario, encontrada


def _exigir_csrf(pedido: Request, sessao: SessaoModelo) -> None:
    enviado = pedido.headers.get("x-csrf-token") or ""
    if not enviado or not secrets_iguais(enviado, sessao.csrf):
        raise HTTPException(status_code=403, detail="Não foi possível confirmar esta ação.")


def secrets_iguais(esquerda: str, direita: str) -> bool:
    import secrets

    return secrets.compare_digest(esquerda, direita)


def _publico(usuario: Usuario, csrf: str | None) -> dict[str, object]:
    return {
        "autenticado": True,
        "contas_disponiveis": True,
        "csrf": csrf,
        "usuario": {
            "nome_exibicao": nome_publico(usuario),
            "email": usuario.email,
            "perfil_juridico": usuario.perfil_juridico,
            "tema": usuario.tema,
            "tipo_avatar": usuario.tipo_avatar,
            "avatar_codigo": usuario.avatar_codigo,
        },
    }


def _definir_cookie(resposta: Response, token: str, pedido: Request) -> None:
    seguro = pedido.url.scheme == "https" or os.getenv("COOKIE_SECURE", "").lower() in {"1", "true"}
    resposta.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=seguro,
        samesite="lax",
        max_age=_DURACAO_COOKIE,
        path="/",
    )


@router.get("/sessao")
def ler_sessao(pedido: Request) -> dict[str, object]:
    if not contas_disponiveis():
        return {"autenticado": False, "contas_disponiveis": False, "csrf": None, "usuario": None}
    db = _banco()
    try:
        encontrada = sessao_do_token(db, pedido.cookies.get(COOKIE))
        if encontrada is None or encontrada.usuario is None:
            return {"autenticado": False, "contas_disponiveis": True, "csrf": None, "usuario": None}
        return _publico(encontrada.usuario, encontrada.csrf)
    finally:
        db.close()


@router.post("/cadastrar")
def criar_conta(entrada: CadastroEntrada, pedido: Request, resposta: Response) -> dict[str, object]:
    _limitar(pedido, "cadastro", 5)
    db = _banco()
    try:
        try:
            usuario = cadastrar(db, entrada.email, entrada.senha, entrada.confirmar_senha, entrada.nome)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
        token, csrf = abrir_sessao(db, usuario)
    finally:
        db.close()
    _definir_cookie(resposta, token, pedido)
    return _publico(usuario, csrf)


@router.post("/entrar")
def entrar(entrada: EntradaLogin, pedido: Request, resposta: Response) -> dict[str, object]:
    _limitar(pedido, "login", 8)
    db = _banco()
    try:
        try:
            usuario = autenticar(db, entrada.email, entrada.senha)
        except ValueError as erro:
            raise HTTPException(status_code=401, detail=str(erro)) from None
        token, csrf = abrir_sessao(db, usuario)
    finally:
        db.close()
    _definir_cookie(resposta, token, pedido)
    return _publico(usuario, csrf)


@router.post("/sair")
def sair(pedido: Request, resposta: Response) -> dict[str, bool]:
    if not contas_disponiveis():
        resposta.delete_cookie(COOKIE, path="/")
        return {"ok": True}
    db = _banco()
    try:
        encontrada = sessao_do_token(db, pedido.cookies.get(COOKIE))
        if encontrada is not None:
            _exigir_csrf(pedido, encontrada)
            encerrar_sessao(db, pedido.cookies.get(COOKIE))
    finally:
        db.close()
    resposta.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.post("/recuperar-senha")
def recuperar_senha() -> None:
    raise HTTPException(
        status_code=503,
        detail="O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente.",
    )


@router.patch("/perfil")
def editar_perfil(entrada: PerfilEntrada, pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        try:
            usuario = atualizar_perfil(
                db,
                usuario,
                nome=entrada.nome,
                perfil_juridico=entrada.perfil_juridico,
                tema=entrada.tema,
                avatar_codigo=entrada.avatar_codigo,
            )
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
        return _publico(usuario, sessao.csrf)
    finally:
        db.close()


@router.post("/avatar")
async def enviar_avatar(pedido: Request, arquivo: UploadFile = File(...)) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        bruto = await arquivo.read(LIMITE_BYTES + 1)
        try:
            usuario = definir_imagem(db, usuario, bruto)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
        return _publico(usuario, sessao.csrf)
    finally:
        db.close()


@router.delete("/avatar")
def apagar_avatar(pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        usuario = retirar_imagem(db, usuario)
        return _publico(usuario, sessao.csrf)
    finally:
        db.close()


@router.get("/avatar")
def obter_avatar(pedido: Request) -> Response:
    db = _banco()
    try:
        usuario, _sessao = _usuario_da_sessao(pedido, db)
        imagem = imagem_do_usuario(usuario)
    finally:
        db.close()
    if imagem is None:
        raise HTTPException(status_code=404, detail="Não há foto pessoal nesta conta.")
    return Response(content=imagem, media_type="image/webp", headers={"Cache-Control": "private, no-store"})
