"""Cadastro, sessão e perfil. A senha fica só como hash Argon2id."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.avatares import PADRAO, avatar_valido, guardar_imagem, ler_imagem, remover_imagem
from app.modelos import ConfirmacaoEmail, Perfil, RedefinicaoSenha, RegistroExclusao, Sessao, Usuario

_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PERFIS = {"estudante", "profissional", "cidadao"}
_TEMAS = {"claro", "escuro"}
_DURACAO = timedelta(days=14)
_VALIDADE_REDEFINICAO = timedelta(minutes=30)
_VALIDADE_CONFIRMACAO = timedelta(hours=24)
CONFIRMACAO_EXCLUSAO = "EXCLUIR"
COOKIE = "md_sessao"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validar_email(email: str) -> str:
    limpo = email.strip().lower()
    if not _EMAIL.fullmatch(limpo) or len(limpo) > 254:
        raise ValueError("Informe um e-mail válido.")
    return limpo


def validar_senha(senha: str) -> str:
    if len(senha) < 8 or len(senha) > 128:
        raise ValueError("A senha precisa ter entre 8 e 128 caracteres.")
    return senha


def validar_nome(nome: str | None, identificador: uuid.UUID) -> str:
    texto = " ".join((nome or "").split())
    if not texto:
        return "Usuário"
    if "@" in texto or len(texto) > 40:
        raise ValueError("O nome de exibição não pode ser um e-mail nem passar de 40 caracteres.")
    if texto.lower() == "usuário" and identificador:
        return f"Usuário {identificador.hex[:4]}"
    return texto


def nome_publico(usuario: Usuario) -> str:
    if usuario.nome_exibicao.strip().lower() == "usuário":
        return f"Usuário {usuario.id.hex[:4]}"
    return usuario.nome_exibicao


def perfil_de(usuario: Usuario) -> Perfil:
    if usuario.perfil is None:
        raise RuntimeError("Perfil ausente.")
    return usuario.perfil


def referencia_da_foto(usuario: Usuario) -> str:
    return f"{usuario.id.hex}.webp"


def cadastrar(db: Session, email: str, senha: str, confirmar: str, nome: str | None) -> Usuario:
    if senha != confirmar:
        raise ValueError("A confirmação da senha não confere.")
    endereco = validar_email(email)
    validar_senha(senha)
    existente = db.scalar(select(Usuario).where(Usuario.email == endereco))
    if existente is not None:
        raise ValueError("Não foi possível criar a conta. Se você já se cadastrou, entre com seu e-mail.")
    agora = _agora()
    usuario = Usuario(
        id=uuid.uuid4(),
        email=endereco,
        senha_hash=_HASHER.hash(senha),
        nome_exibicao="Usuário",
        criado_em=agora,
        atualizado_em=agora,
    )
    usuario.nome_exibicao = validar_nome(nome, usuario.id)
    usuario.perfil = Perfil(
        id=uuid.uuid4(),
        usuario_id=usuario.id,
        avatar_codigo=PADRAO,
        tipo_avatar="biblioteca",
        foto_referencia=None,
        perfil_juridico="cidadao",
        tema=None,
        consentimento_sincronizacao=False,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, email: str, senha: str) -> Usuario:
    try:
        endereco = validar_email(email)
    except ValueError:
        raise ValueError("E-mail ou senha não conferem.") from None
    usuario = db.scalar(select(Usuario).where(Usuario.email == endereco))
    if usuario is None:
        _HASHER.hash("senha-inexistente")
        raise ValueError("E-mail ou senha não conferem.")
    try:
        _HASHER.verify(usuario.senha_hash, senha)
    except VerifyMismatchError:
        raise ValueError("E-mail ou senha não conferem.") from None
    if _HASHER.check_needs_rehash(usuario.senha_hash):
        usuario.senha_hash = _HASHER.hash(senha)
        db.commit()
    return usuario


def abrir_sessao(db: Session, usuario: Usuario) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    agora = _agora()
    db.add(
        Sessao(
            id=uuid.uuid4(),
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            csrf=csrf,
            criado_em=agora,
            expira_em=agora + _DURACAO,
        )
    )
    db.commit()
    return token, csrf


def sessao_do_token(db: Session, token: str | None) -> Sessao | None:
    if not token:
        return None
    encontrada = db.scalar(select(Sessao).where(Sessao.token_hash == _hash_token(token)))
    if encontrada is None:
        return None
    if _ciente(encontrada.expira_em) < _agora():
        return None
    if encontrada.revogada_em is not None:
        return None
    return encontrada


def _ciente(momento: datetime) -> datetime:
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def encerrar_sessao(db: Session, token: str | None) -> None:
    encontrada = sessao_do_token(db, token)
    if encontrada is not None:
        encontrada.revogada_em = _agora()
        db.commit()


def atualizar_perfil(
    db: Session,
    usuario: Usuario,
    *,
    nome: str | None = None,
    perfil_juridico: str | None = None,
    tema: str | None = None,
    avatar_codigo: str | None = None,
    limpar_tema: bool = False,
) -> Usuario:
    perfil = perfil_de(usuario)
    if nome is not None:
        usuario.nome_exibicao = validar_nome(nome, usuario.id)
    if perfil_juridico is not None:
        if perfil_juridico not in _PERFIS:
            raise ValueError("Escolha estudante, profissional jurídico ou cidadão.")
        perfil.perfil_juridico = perfil_juridico
    if limpar_tema:
        perfil.tema = None
    elif tema is not None:
        if tema not in _TEMAS:
            raise ValueError("O tema precisa ser claro ou escuro.")
        perfil.tema = tema
    if avatar_codigo is not None:
        if not avatar_valido(avatar_codigo):
            raise ValueError("Escolha um dos avatares jurídicos.")
        perfil.avatar_codigo = avatar_codigo
        perfil.tipo_avatar = "biblioteca"
        perfil.foto_referencia = None
        remover_imagem(usuario.id.hex)
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def definir_imagem(db: Session, usuario: Usuario, bruto: bytes) -> Usuario:
    guardar_imagem(usuario.id.hex, bruto)
    perfil = perfil_de(usuario)
    perfil.tipo_avatar = "imagem"
    perfil.foto_referencia = referencia_da_foto(usuario)
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def retirar_imagem(db: Session, usuario: Usuario) -> Usuario:
    perfil = perfil_de(usuario)
    remover_imagem(usuario.id.hex)
    perfil.tipo_avatar = "biblioteca"
    perfil.foto_referencia = None
    if not avatar_valido(perfil.avatar_codigo):
        perfil.avatar_codigo = PADRAO
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def imagem_do_usuario(usuario: Usuario) -> bytes | None:
    perfil = usuario.perfil
    if perfil is None or perfil.foto_referencia != referencia_da_foto(usuario):
        return None
    return ler_imagem(usuario.id.hex)


def _iso(momento: datetime) -> str:
    return _ciente(momento).isoformat()


def sessoes_ativas(db: Session, usuario: Usuario) -> list[Sessao]:
    agora = _agora()
    encontradas = db.scalars(select(Sessao).where(Sessao.usuario_id == usuario.id)).all()
    ativas = [sessao for sessao in encontradas if sessao.revogada_em is None and _ciente(sessao.expira_em) > agora]
    return sorted(ativas, key=lambda sessao: _ciente(sessao.criado_em), reverse=True)


def descrever_sessoes(sessoes: list[Sessao], atual_id: uuid.UUID) -> list[dict[str, object]]:
    return [
        {
            "id": str(sessao.id),
            "criada_em": _iso(sessao.criado_em),
            "expira_em": _iso(sessao.expira_em),
            "atual": sessao.id == atual_id,
        }
        for sessao in sessoes
    ]


def revogar_sessoes(db: Session, usuario: Usuario, preservar: uuid.UUID | None = None) -> None:
    agora = _agora()
    for sessao in sessoes_ativas(db, usuario):
        if preservar is not None and sessao.id == preservar:
            continue
        sessao.revogada_em = agora


def alterar_senha(db: Session, usuario: Usuario, sessao_atual: Sessao, atual: str, nova: str, confirmar: str) -> None:
    if nova != confirmar:
        raise ValueError("A confirmação da senha não confere.")
    validar_senha(nova)
    try:
        _HASHER.verify(usuario.senha_hash, atual)
    except VerifyMismatchError:
        raise ValueError("A senha atual não confere.") from None
    if nova == atual:
        raise ValueError("Escolha uma senha diferente da atual.")
    usuario.senha_hash = _HASHER.hash(nova)
    usuario.atualizado_em = _agora()
    revogar_sessoes(db, usuario, preservar=sessao_atual.id)
    db.commit()


def solicitar_redefinicao(db: Session, email: str) -> str | None:
    """Devolve o token só para o envio. Quem não tem conta recebe None."""
    try:
        endereco = validar_email(email)
    except ValueError:
        return None
    usuario = db.scalar(select(Usuario).where(Usuario.email == endereco))
    if usuario is None:
        return None
    agora = _agora()
    for antiga in db.scalars(
        select(RedefinicaoSenha).where(RedefinicaoSenha.usuario_id == usuario.id, RedefinicaoSenha.usado_em.is_(None))
    ):
        antiga.usado_em = agora
    token = secrets.token_urlsafe(32)
    db.add(
        RedefinicaoSenha(
            id=uuid.uuid4(),
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            criado_em=agora,
            expira_em=agora + _VALIDADE_REDEFINICAO,
            usado_em=None,
        )
    )
    db.commit()
    return token


def solicitar_confirmacao(db: Session, usuario: Usuario) -> str:
    """Gera um token novo e invalida os anteriores ainda não usados."""
    agora = _agora()
    for antiga in db.scalars(
        select(ConfirmacaoEmail).where(ConfirmacaoEmail.usuario_id == usuario.id, ConfirmacaoEmail.usado_em.is_(None))
    ):
        antiga.usado_em = agora
    token = secrets.token_urlsafe(32)
    db.add(
        ConfirmacaoEmail(
            id=uuid.uuid4(),
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            criado_em=agora,
            expira_em=agora + _VALIDADE_CONFIRMACAO,
            usado_em=None,
        )
    )
    db.commit()
    return token


def confirmar_email(db: Session, token: str) -> None:
    if not token or len(token) > 200:
        raise ValueError("O link de confirmação é inválido ou expirou.")
    registro = db.scalar(select(ConfirmacaoEmail).where(ConfirmacaoEmail.token_hash == _hash_token(token)))
    if registro is None or registro.usado_em is not None or _ciente(registro.expira_em) <= _agora():
        raise ValueError("O link de confirmação é inválido ou expirou.")
    usuario = registro.usuario
    if usuario is None:
        raise ValueError("O link de confirmação é inválido ou expirou.")
    agora = _agora()
    usuario.email_confirmado_em = agora
    usuario.confirmacao_motivo = "link"
    usuario.atualizado_em = agora
    registro.usado_em = agora
    db.commit()


def redefinir_senha(db: Session, token: str, nova: str, confirmar: str) -> None:
    if nova != confirmar:
        raise ValueError("A confirmação da senha não confere.")
    validar_senha(nova)
    if not token or len(token) > 200:
        raise ValueError("O link de redefinição é inválido ou expirou.")
    registro = db.scalar(select(RedefinicaoSenha).where(RedefinicaoSenha.token_hash == _hash_token(token)))
    if registro is None or registro.usado_em is not None or _ciente(registro.expira_em) <= _agora():
        raise ValueError("O link de redefinição é inválido ou expirou.")
    usuario = registro.usuario
    if usuario is None:
        raise ValueError("O link de redefinição é inválido ou expirou.")
    usuario.senha_hash = _HASHER.hash(nova)
    usuario.atualizado_em = _agora()
    registro.usado_em = _agora()
    revogar_sessoes(db, usuario)
    db.commit()


def dias_retencao() -> int:
    bruto = os.getenv("RETENCAO_REGISTRO_EXCLUSAO_DIAS", "0").strip()
    try:
        dias = int(bruto)
    except ValueError:
        return 0
    if dias < 0:
        return 0
    return min(dias, 3650)


def purgar_retencao(db: Session) -> None:
    agora = _agora()
    for registro in db.scalars(select(RegistroExclusao)).all():
        if _ciente(registro.expira_em) <= agora:
            db.delete(registro)
    db.commit()


def texto_privacidade() -> dict[str, object]:
    from app.correio import correio_configurado

    dias = dias_retencao()
    if dias == 0:
        retencao = "Nenhum dado pessoal da conta é mantido depois da exclusão."
    else:
        retencao = (
            f"Por {dias} dias permanece apenas um registro sem conteúdo: o resumo criptográfico do e-mail e a data da exclusão. "
            "Conversas, nome e foto não entram nesse registro."
        )
    return {
        "apagados": [
            "Perfil e nome de exibição",
            "Foto pessoal",
            "Conversas, mensagens e referências jurídicas salvas na conta",
            "Sessões e pedidos de redefinição de senha",
        ],
        "nao_armazenados": [
            "As avaliações das respostas não identificam a conta e não são apagadas junto com ela.",
            "Os documentos jurídicos são gerados para baixar e não ficam guardados no servidor.",
            "As conversas salvas só neste navegador permanecem nele até você apagá-las nas configurações.",
        ],
        "retencao": retencao,
        "treinamento": "O conteúdo das conversas não é usado para treinamento nem para análise adicional.",
        "email_configurado": correio_configurado(),
        "dias_retencao": dias,
    }


def exportar_dados(db: Session, usuario: Usuario, sessao_atual: Sessao) -> dict[str, object]:
    from app.historico import conversa_do_usuario, listar, serializar

    perfil = perfil_de(usuario)
    conversas = []
    for resumo in listar(db, usuario):
        completa = conversa_do_usuario(db, usuario, resumo.id)
        if completa is not None:
            conversas.append(serializar(completa, completa=True))
    return {
        "conta": {
            "nome_exibicao": nome_publico(usuario),
            "email": usuario.email,
            "criado_em": _iso(usuario.criado_em),
            "atualizado_em": _iso(usuario.atualizado_em),
            "email_confirmado": usuario.email_confirmado_em is not None,
            "confirmacao_motivo": usuario.confirmacao_motivo,
        },
        "perfil": {
            "perfil_juridico": perfil.perfil_juridico,
            "tema": perfil.tema,
            "avatar_codigo": perfil.avatar_codigo,
            "tipo_avatar": perfil.tipo_avatar,
            "tem_foto": perfil.foto_referencia is not None,
            "consentimento_sincronizacao": perfil.consentimento_sincronizacao,
        },
        "conversas": conversas,
        "documentos_armazenados": [],
        "avaliacoes": "As avaliações não ficam vinculadas a esta conta.",
        "sessoes": descrever_sessoes(sessoes_ativas(db, usuario), sessao_atual.id),
    }


def excluir_conta(db: Session, usuario: Usuario, senha: str, confirmacao: str) -> None:
    if confirmacao.strip() != CONFIRMACAO_EXCLUSAO:
        raise ValueError("Digite EXCLUIR para confirmar a exclusão da conta.")
    try:
        _HASHER.verify(usuario.senha_hash, senha)
    except VerifyMismatchError:
        raise ValueError("A senha não confere.") from None
    purgar_retencao(db)
    dias = dias_retencao()
    if dias > 0:
        agora = _agora()
        db.add(
            RegistroExclusao(
                id=uuid.uuid4(),
                email_hash=_hash_token(usuario.email),
                excluido_em=agora,
                expira_em=agora + timedelta(days=dias),
            )
        )
    remover_imagem(usuario.id.hex)
    db.delete(usuario)
    db.commit()
