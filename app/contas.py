"""Cadastro, sessão e perfil. A senha fica só como hash Argon2id."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.avatares import PADRAO, avatar_valido, guardar_imagem, ler_imagem, remover_imagem
from app.modelos import Sessao, Usuario

_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, type=Type.ID)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PERFIS = {"estudante", "profissional", "cidadao"}
_TEMAS = {"claro", "escuro"}
_DURACAO = timedelta(days=14)
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
        perfil_juridico="cidadao",
        tema=None,
        tipo_avatar="biblioteca",
        avatar_codigo=PADRAO,
        tem_imagem=False,
        criado_em=agora,
        atualizado_em=agora,
    )
    usuario.nome_exibicao = validar_nome(nome, usuario.id)
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
    expira = encontrada.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < _agora():
        db.delete(encontrada)
        db.commit()
        return None
    return encontrada


def encerrar_sessao(db: Session, token: str | None) -> None:
    encontrada = sessao_do_token(db, token)
    if encontrada is not None:
        db.delete(encontrada)
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
    if nome is not None:
        usuario.nome_exibicao = validar_nome(nome, usuario.id)
    if perfil_juridico is not None:
        if perfil_juridico not in _PERFIS:
            raise ValueError("Escolha estudante, profissional jurídico ou cidadão.")
        usuario.perfil_juridico = perfil_juridico
    if limpar_tema:
        usuario.tema = None
    elif tema is not None:
        if tema not in _TEMAS:
            raise ValueError("O tema precisa ser claro ou escuro.")
        usuario.tema = tema
    if avatar_codigo is not None:
        if not avatar_valido(avatar_codigo):
            raise ValueError("Escolha um dos avatares jurídicos.")
        usuario.avatar_codigo = avatar_codigo
        usuario.tipo_avatar = "biblioteca"
        usuario.tem_imagem = False
        remover_imagem(usuario.id.hex)
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def definir_imagem(db: Session, usuario: Usuario, bruto: bytes) -> Usuario:
    guardar_imagem(usuario.id.hex, bruto)
    usuario.tipo_avatar = "imagem"
    usuario.tem_imagem = True
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def retirar_imagem(db: Session, usuario: Usuario) -> Usuario:
    remover_imagem(usuario.id.hex)
    usuario.tipo_avatar = "biblioteca"
    usuario.tem_imagem = False
    if not avatar_valido(usuario.avatar_codigo):
        usuario.avatar_codigo = PADRAO
    usuario.atualizado_em = _agora()
    db.commit()
    db.refresh(usuario)
    return usuario


def imagem_do_usuario(usuario: Usuario) -> bytes | None:
    if not usuario.tem_imagem:
        return None
    return ler_imagem(usuario.id.hex)
