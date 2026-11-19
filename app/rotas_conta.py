"""Rotas de conta. A pesquisa jurídica não depende delas."""

from __future__ import annotations

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.avatares import LIMITE_BYTES
from app.banco import contas_disponiveis, exigir_fabrica
from app.contas import (
    COOKIE,
    alterar_senha,
    atualizar_perfil,
    autenticar,
    abrir_sessao,
    cadastrar,
    confirmar_email,
    descrever_sessoes,
    encerrar_sessao,
    excluir_conta,
    exportar_dados,
    imagem_do_usuario,
    nome_publico,
    perfil_de,
    redefinir_senha,
    solicitar_confirmacao,
    retirar_imagem,
    definir_imagem,
    revogar_sessoes,
    sessao_do_token,
    sessoes_ativas,
    solicitar_redefinicao,
    validar_email,
    texto_privacidade,
)
from app.correio import correio_configurado, enviar_confirmacao, enviar_redefinicao, link_de_confirmacao, link_de_redefinicao
from app.publicacao import cookie_samesite, cookie_seguro
from app.limite import consumir
from app.modelos import Sessao as SessaoModelo
from app.modelos import Usuario

router = APIRouter(prefix="/conta", tags=["conta"])
logger = logging.getLogger("meu_direito")
_DURACAO_COOKIE = 14 * 24 * 3600
_MENSAGEM_REDEFINICAO = "Se houver uma conta com esse e-mail, enviaremos um link de redefinição."
_MENSAGEM_CONFIRMACAO = "Se houver uma conta com esse e-mail e ele ainda não estiver confirmado, enviaremos um link."
_MENSAGEM_SEM_CORREIO = "O envio de e-mail ainda não está configurado. A confirmação do endereço permanece pendente."


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
    perfil = perfil_de(usuario)
    return {
        "autenticado": True,
        "contas_disponiveis": True,
        "sincronizacao_disponivel": True,
        "csrf": csrf,
        "usuario": {
            "nome_exibicao": nome_publico(usuario),
            "email": usuario.email,
            "perfil_juridico": perfil.perfil_juridico,
            "tema": perfil.tema,
            "tipo_avatar": perfil.tipo_avatar,
            "avatar_codigo": perfil.avatar_codigo,
            "email_confirmado": usuario.email_confirmado_em is not None,
            "confirmacao_motivo": usuario.confirmacao_motivo,
        },
        "correio_configurado": correio_configurado(),
    }


def _definir_cookie(resposta: Response, token: str, pedido: Request) -> None:
    seguro = cookie_seguro(pedido.url.scheme)
    resposta.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=seguro,
        samesite=cookie_samesite(seguro),
        max_age=_DURACAO_COOKIE,
        path="/",
    )


@router.get("/sessao")
def ler_sessao(pedido: Request) -> dict[str, object]:
    if not contas_disponiveis():
        return {
            "autenticado": False,
            "contas_disponiveis": False,
            "sincronizacao_disponivel": False,
            "csrf": None,
            "usuario": None,
            "correio_configurado": correio_configurado(),
        }
    db = _banco()
    try:
        encontrada = sessao_do_token(db, pedido.cookies.get(COOKIE))
        if encontrada is None or encontrada.usuario is None:
            return {
                "autenticado": False,
                "contas_disponiveis": True,
                "sincronizacao_disponivel": False,
                "csrf": None,
                "usuario": None,
                "correio_configurado": correio_configurado(),
            }
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
        corpo = _publico(usuario, csrf)
        corpo["confirmacao_enviada"] = False
        if not correio_configurado():
            corpo["confirmacao_mensagem"] = _MENSAGEM_SEM_CORREIO
        else:
            token_confirmacao = solicitar_confirmacao(db, usuario)
            try:
                enviar_confirmacao(usuario.email, link_de_confirmacao(token_confirmacao))
            except Exception as erro:
                logger.warning("Falha no envio da confirmação: %s", type(erro).__name__)
                corpo["confirmacao_mensagem"] = "A conta foi criada, mas o e-mail de confirmação não pôde ser enviado."
            else:
                corpo["confirmacao_enviada"] = True
                corpo["confirmacao_mensagem"] = "Enviamos um link para confirmar o e-mail. Ele vale 24 horas e só pode ser usado uma vez."
    finally:
        db.close()
    _definir_cookie(resposta, token, pedido)
    return corpo


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
        corpo = _publico(usuario, csrf)
    finally:
        db.close()
    _definir_cookie(resposta, token, pedido)
    return corpo


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


def _erro_conta(erro: ValueError) -> HTTPException:
    texto = str(erro)
    if "não confere" in texto and "confirmação" not in texto:
        return HTTPException(status_code=401, detail=texto)
    return HTTPException(status_code=422, detail=texto)


@router.post("/recuperar-senha")
async def recuperar_senha(pedido: Request) -> dict[str, str]:
    _limitar(pedido, "recuperar", 5)
    if not correio_configurado():
        raise HTTPException(
            status_code=503,
            detail="O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente.",
        )
    try:
        corpo = await pedido.json()
    except Exception:
        corpo = None
    email = corpo.get("email") if isinstance(corpo, dict) else None
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status_code=422, detail="Informe o e-mail da conta.")
    db = _banco()
    try:
        token = solicitar_redefinicao(db, email)
        if token is None:
            return {"mensagem": _MENSAGEM_REDEFINICAO}
        try:
            enviar_redefinicao(email.strip().lower(), link_de_redefinicao(token))
        except Exception as erro:
            logger.warning("Falha no envio da redefinição: %s", type(erro).__name__)
            raise HTTPException(status_code=503, detail="Não foi possível enviar o e-mail agora.") from None
    finally:
        db.close()
    return {"mensagem": _MENSAGEM_REDEFINICAO}


class TokenEntrada(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class EmailEntrada(BaseModel):
    email: str = Field(min_length=3, max_length=254)


@router.post("/confirmar-email")
def confirmar_endereco(entrada: TokenEntrada, pedido: Request) -> dict[str, str]:
    _limitar(pedido, "confirmar-email", 8)
    db = _banco()
    try:
        try:
            confirmar_email(db, entrada.token)
        except ValueError as erro:
            raise HTTPException(status_code=422, detail=str(erro)) from None
    finally:
        db.close()
    return {"mensagem": "E-mail confirmado."}


@router.post("/reenviar-confirmacao")
async def reenviar_confirmacao(pedido: Request) -> dict[str, str]:
    """Reenvia sem revelar se o e-mail tem conta. Sem SMTP, nada é criado nem simulado."""
    _limitar(pedido, "reenviar-confirmacao", 5)
    if not correio_configurado():
        raise HTTPException(status_code=503, detail=_MENSAGEM_SEM_CORREIO)
    try:
        corpo = await pedido.json()
    except Exception:
        corpo = None
    email = corpo.get("email") if isinstance(corpo, dict) else None
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status_code=422, detail="Informe o e-mail da conta.")
    db = _banco()
    try:
        try:
            endereco = validar_email(email)
        except ValueError:
            return {"mensagem": _MENSAGEM_CONFIRMACAO}
        usuario = db.scalar(select(Usuario).where(Usuario.email == endereco))
        if usuario is None or usuario.email_confirmado_em is not None:
            return {"mensagem": _MENSAGEM_CONFIRMACAO}
        token = solicitar_confirmacao(db, usuario)
        try:
            enviar_confirmacao(usuario.email, link_de_confirmacao(token))
        except Exception as erro:
            logger.warning("Falha no reenvio da confirmação: %s", type(erro).__name__)
            raise HTTPException(status_code=503, detail="Não foi possível enviar o e-mail agora.") from None
    finally:
        db.close()
    return {"mensagem": _MENSAGEM_CONFIRMACAO}


class SenhaEntrada(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)
    confirmar_senha: str = Field(min_length=8, max_length=128)


class RedefinirEntrada(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    nova_senha: str = Field(min_length=8, max_length=128)
    confirmar_senha: str = Field(min_length=8, max_length=128)


class ExclusaoEntrada(BaseModel):
    senha: str = Field(min_length=1, max_length=128)
    confirmacao: str = Field(min_length=1, max_length=20)


@router.post("/senha")
def trocar_senha(entrada: SenhaEntrada, pedido: Request) -> dict[str, str]:
    _limitar(pedido, "senha", 8)
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        try:
            alterar_senha(db, usuario, sessao, entrada.senha_atual, entrada.nova_senha, entrada.confirmar_senha)
        except ValueError as erro:
            raise _erro_conta(erro) from None
        logger.info("Senha da conta alterada")
        return {"mensagem": "Senha alterada. As outras sessões foram encerradas."}
    finally:
        db.close()


@router.post("/redefinir-senha")
def concluir_redefinicao(entrada: RedefinirEntrada, pedido: Request, resposta: Response) -> dict[str, str]:
    _limitar(pedido, "redefinir", 8)
    db = _banco()
    try:
        try:
            redefinir_senha(db, entrada.token, entrada.nova_senha, entrada.confirmar_senha)
        except ValueError as erro:
            raise _erro_conta(erro) from None
    finally:
        db.close()
    resposta.delete_cookie(COOKIE, path="/")
    logger.info("Senha redefinida e sessões encerradas")
    return {"mensagem": "Senha redefinida. Entre novamente com a nova senha."}


@router.get("/sessoes")
def listar_sessoes(pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        return {"sessoes": descrever_sessoes(sessoes_ativas(db, usuario), sessao.id)}
    finally:
        db.close()


@router.delete("/sessoes/outras", status_code=204)
def encerrar_outras(pedido: Request) -> Response:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        revogar_sessoes(db, usuario, preservar=sessao.id)
        db.commit()
        return Response(status_code=204)
    finally:
        db.close()


@router.delete("/sessoes", status_code=204)
def encerrar_todas(pedido: Request, resposta: Response) -> Response:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        revogar_sessoes(db, usuario)
        db.commit()
    finally:
        db.close()
    resposta.delete_cookie(COOKIE, path="/")
    return Response(status_code=204)


@router.delete("/sessoes/{sessao_id}", status_code=204)
def encerrar_uma(sessao_id: uuid.UUID, pedido: Request, resposta: Response) -> Response:
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        alvo = next((item for item in sessoes_ativas(db, usuario) if item.id == sessao_id), None)
        if alvo is None:
            raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        from datetime import datetime, timezone

        alvo.revogada_em = datetime.now(timezone.utc)
        db.commit()
        atual = alvo.id == sessao.id
    finally:
        db.close()
    if atual:
        resposta.delete_cookie(COOKIE, path="/")
    return Response(status_code=204)


@router.get("/privacidade")
def ler_privacidade(pedido: Request) -> dict[str, object]:
    db = _banco()
    try:
        _usuario_da_sessao(pedido, db)
        return texto_privacidade()
    finally:
        db.close()


@router.get("/dados")
def baixar_dados(pedido: Request) -> dict[str, object]:
    _limitar(pedido, "dados", 10)
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        return exportar_dados(db, usuario, sessao)
    finally:
        db.close()


@router.delete("")
def apagar_conta(entrada: ExclusaoEntrada, pedido: Request, resposta: Response) -> dict[str, str]:
    _limitar(pedido, "excluir-conta", 5)
    db = _banco()
    try:
        usuario, sessao = _usuario_da_sessao(pedido, db)
        _exigir_csrf(pedido, sessao)
        try:
            excluir_conta(db, usuario, entrada.senha, entrada.confirmacao)
        except ValueError as erro:
            raise _erro_conta(erro) from None
    finally:
        db.close()
    resposta.delete_cookie(COOKIE, path="/")
    logger.info("Conta excluída")
    return {"mensagem": "A conta e os dados associados foram excluídos."}


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
