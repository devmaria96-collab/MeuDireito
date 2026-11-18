"""Histórico da conta. O texto das conversas não entra em log."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.consulta_legislacao import ResultadoConsulta
from app.modelos import ConversaRegistro, MensagemRegistro, ReferenciaRegistro, Usuario

_TIPOS = {"peticao_inicial", "contrato", "notificacao", "requerimento", "declaracao", "parecer", "resumo"}
_LIMITE_TITULO = 80
_LIMITE_USUARIO = 8000
_LIMITE_AGENTE = 20_000
_LIMITE_IMPORTACAO = 30
_LIMITE_MENSAGENS = 80


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(momento: datetime) -> str:
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.isoformat()


def titulo_de(texto: str) -> str:
    limpo = " ".join(texto.split())
    if len(limpo) <= 42:
        return limpo or "Conversa"
    return limpo[:42].rstrip() + "…"


def validar_titulo(titulo: str) -> str:
    limpo = " ".join(titulo.split())
    if not limpo or len(limpo) > _LIMITE_TITULO:
        raise ValueError("O título precisa ter entre 1 e 80 caracteres.")
    return limpo


def _tipo(valor: str | None) -> str | None:
    if valor is None or valor == "":
        return None
    if valor not in _TIPOS:
        raise ValueError("O tipo de documento não é aceito.")
    return valor


def conversa_do_usuario(db: Session, usuario: Usuario, conversa_id: uuid.UUID) -> ConversaRegistro | None:
    return db.scalar(
        select(ConversaRegistro)
        .where(ConversaRegistro.id == conversa_id, ConversaRegistro.usuario_id == usuario.id)
        .options(selectinload(ConversaRegistro.mensagens).selectinload(MensagemRegistro.referencias))
    )


def listar(db: Session, usuario: Usuario) -> list[ConversaRegistro]:
    return list(
        db.scalars(
            select(ConversaRegistro)
            .where(ConversaRegistro.usuario_id == usuario.id)
            .order_by(ConversaRegistro.atualizada_em.desc())
        )
    )


def criar(db: Session, usuario: Usuario, titulo: str, tipo_documento: str | None, origem_local: str | None = None) -> ConversaRegistro:
    agora = _agora()
    conversa = ConversaRegistro(
        id=uuid.uuid4(),
        usuario_id=usuario.id,
        titulo=validar_titulo(titulo),
        tipo_documento=_tipo(tipo_documento),
        origem_local=origem_local,
        criada_em=agora,
        atualizada_em=agora,
    )
    db.add(conversa)
    db.commit()
    db.refresh(conversa)
    return conversa


def renomear(db: Session, conversa: ConversaRegistro, titulo: str) -> ConversaRegistro:
    conversa.titulo = validar_titulo(titulo)
    conversa.atualizada_em = _agora()
    db.commit()
    db.refresh(conversa)
    return conversa


def excluir(db: Session, conversa: ConversaRegistro) -> None:
    db.delete(conversa)
    db.commit()


def excluir_todas(db: Session, usuario: Usuario) -> None:
    for conversa in listar(db, usuario):
        db.delete(conversa)
    db.commit()


def _ultima_pendente(conversa: ConversaRegistro, pergunta: str) -> bool:
    if not conversa.mensagens:
        return False
    ultima = conversa.mensagens[-1]
    return ultima.papel == "usuario" and ultima.conteudo == pergunta


def preparar_pergunta(
    db: Session,
    usuario: Usuario,
    *,
    conversa_id: uuid.UUID | None,
    pergunta: str,
    titulo: str | None,
    tipo_documento: str | None,
) -> ConversaRegistro:
    texto = " ".join(pergunta.split())
    if not texto or len(pergunta) > _LIMITE_USUARIO:
        raise ValueError("A pergunta precisa ter entre 1 e 8000 caracteres.")
    if conversa_id is None:
        conversa = criar(db, usuario, titulo or titulo_de(texto), tipo_documento)
        conversa = conversa_do_usuario(db, usuario, conversa.id)
        if conversa is None:
            raise RuntimeError("Conversa ausente.")
    else:
        conversa = conversa_do_usuario(db, usuario, conversa_id)
        if conversa is None:
            raise LookupError
        if tipo_documento is not None:
            conversa.tipo_documento = _tipo(tipo_documento)
    if not _ultima_pendente(conversa, pergunta.strip()):
        conversa.mensagens.append(
            MensagemRegistro(
                id=uuid.uuid4(),
                conversa_id=conversa.id,
                papel="usuario",
                conteudo=pergunta.strip(),
                ordem=len(conversa.mensagens) + 1,
                criada_em=_agora(),
            )
        )
    conversa.atualizada_em = _agora()
    db.commit()
    recarregada = conversa_do_usuario(db, usuario, conversa.id)
    if recarregada is None:
        raise RuntimeError("Conversa ausente.")
    return recarregada


def _referencia_de(item: ResultadoConsulta) -> dict[str, object]:
    confirmada = bool(
        item.verificada and item.texto_oficial and item.url and item.url.startswith("https://www.planalto.gov.br/")
    )
    base = "|".join((str(confirmada), item.url or "", item.artigo or "", item.consultado_em, item.situacao))
    return {
        "codigo": "ref-" + hashlib.sha256(base.encode()).hexdigest()[:12],
        "tipo": "legislacao",
        "verificada": confirmada,
        "norma": item.norma,
        "numero": item.numero,
        "ano": item.ano,
        "artigo": item.artigo,
        "url": item.url if confirmada else None,
        "consultado_em": item.consultado_em,
        "situacao": item.situacao if confirmada else "nao_verificada",
        "tipo_texto": item.tipo_texto if confirmada else None,
        "notas_fonte": list(item.notas_fonte) if confirmada else [],
        "aviso": item.aviso,
    }


def registrar_resposta(
    db: Session,
    usuario: Usuario,
    conversa: ConversaRegistro,
    texto: str,
    consultas: list[ResultadoConsulta],
) -> ConversaRegistro:
    if not texto.strip() or len(texto) > _LIMITE_AGENTE:
        raise ValueError("A resposta não pôde ser armazenada.")
    vistas: dict[str, dict[str, object]] = {}
    for item in consultas:
        referencia = _referencia_de(item)
        vistas.setdefault(str(referencia["codigo"]), referencia)
    mensagem = MensagemRegistro(
        id=uuid.uuid4(),
        conversa_id=conversa.id,
        papel="agente",
        conteudo=texto,
        ordem=len(conversa.mensagens) + 1,
        criada_em=_agora(),
    )
    for referencia in vistas.values():
        notas = referencia["notas_fonte"]
        mensagem.referencias.append(
            ReferenciaRegistro(
                id=uuid.uuid4(),
                mensagem_id=mensagem.id,
                codigo=str(referencia["codigo"]),
                tipo="legislacao",
                verificada=bool(referencia["verificada"]),
                norma=_curto(referencia["norma"], 180),
                numero=_curto(referencia["numero"], 40),
                ano=_curto(referencia["ano"], 10),
                artigo=_curto(referencia["artigo"], 40),
                url=_curto(referencia["url"], 500),
                consultado_em=_curto(referencia["consultado_em"], 40) or "",
                situacao=_curto(referencia["situacao"], 40) or "nao_verificada",
                tipo_texto=_curto(referencia["tipo_texto"], 80),
                vigencia_confirmada=False,
                notas_fonte=json.dumps(notas if isinstance(notas, list) else [], ensure_ascii=False),
                aviso=str(referencia["aviso"])[:2000],
            )
        )
    conversa.mensagens.append(mensagem)
    conversa.atualizada_em = _agora()
    db.commit()
    recarregada = conversa_do_usuario(db, usuario, conversa.id)
    if recarregada is None:
        raise RuntimeError("Conversa ausente.")
    return recarregada


def _curto(valor: object, limite: int) -> str | None:
    if not isinstance(valor, str):
        return None
    texto = " ".join(valor.split())
    if not texto:
        return None
    return texto[:limite]


def _notas(bruto: str) -> list[str]:
    try:
        dados = json.loads(bruto or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(dados, list):
        return []
    return [item for item in dados if isinstance(item, str)][:12]


def serializar(conversa: ConversaRegistro, *, completa: bool) -> dict[str, object]:
    corpo: dict[str, object] = {
        "id": str(conversa.id),
        "titulo": conversa.titulo,
        "criada_em": _iso(conversa.criada_em),
        "atualizada_em": _iso(conversa.atualizada_em),
        "tipo_documento": conversa.tipo_documento,
        "origem_local": conversa.origem_local,
    }
    if not completa:
        return corpo
    corpo["mensagens"] = [
        {
            "id": str(mensagem.id),
            "papel": mensagem.papel,
            "conteudo": mensagem.conteudo,
            "criada_em": _iso(mensagem.criada_em),
            "referencias": [
                {
                    "id": referencia.codigo,
                    "tipo": "legislacao",
                    "verificada": referencia.verificada,
                    "norma": referencia.norma,
                    "numero": referencia.numero,
                    "ano": referencia.ano,
                    "artigo": referencia.artigo,
                    "tribunal": None,
                    "processo": None,
                    "relator": None,
                    "data_decisao": None,
                    "url": referencia.url,
                    "consultado_em": referencia.consultado_em,
                    "situacao": referencia.situacao,
                    "tipo_texto": referencia.tipo_texto,
                    "vigencia_confirmada": False,
                    "notas_fonte": _notas(referencia.notas_fonte),
                    "aviso": referencia.aviso,
                }
                for referencia in mensagem.referencias
            ],
        }
        for mensagem in conversa.mensagens
    ]
    return corpo


def importar(db: Session, usuario: Usuario, itens: list[dict[str, object]]) -> dict[str, object]:
    if len(itens) > _LIMITE_IMPORTACAO:
        raise ValueError("Há conversas demais para importar de uma vez.")
    importadas = 0
    ignoradas = 0
    origens: list[str] = []
    for item in itens:
        origem = item.get("id")
        if not isinstance(origem, str) or not origem.strip() or len(origem) > 80:
            ignoradas += 1
            continue
        origem = origem.strip()
        existente = db.scalar(
            select(ConversaRegistro).where(
                ConversaRegistro.usuario_id == usuario.id,
                ConversaRegistro.origem_local == origem,
            )
        )
        if existente is not None:
            ignoradas += 1
            origens.append(origem)
            continue
        mensagens = item.get("mensagens")
        if not isinstance(mensagens, list) or not mensagens:
            ignoradas += 1
            continue
        titulo_bruto = item.get("titulo")
        tipo = item.get("tipo_documento")
        try:
            titulo = validar_titulo(titulo_bruto) if isinstance(titulo_bruto, str) and titulo_bruto.strip() else "Conversa"
            tipo_documento = _tipo(tipo) if isinstance(tipo, str) and tipo else None
        except ValueError:
            ignoradas += 1
            continue
        conversa = ConversaRegistro(
            id=uuid.uuid4(),
            usuario_id=usuario.id,
            titulo=titulo,
            tipo_documento=tipo_documento,
            origem_local=origem,
            criada_em=_agora(),
            atualizada_em=_agora(),
        )
        ordem = 0
        for bruto in mensagens[:_LIMITE_MENSAGENS]:
            if not isinstance(bruto, dict):
                continue
            papel = bruto.get("papel")
            conteudo = bruto.get("conteudo")
            if papel not in {"usuario", "agente"} or not isinstance(conteudo, str) or not conteudo.strip():
                continue
            limite = _LIMITE_USUARIO if papel == "usuario" else _LIMITE_AGENTE
            ordem += 1
            mensagem = MensagemRegistro(
                id=uuid.uuid4(),
                conversa_id=conversa.id,
                papel=papel,
                conteudo=conteudo.strip()[:limite],
                ordem=ordem,
                criada_em=_agora(),
            )
            if papel == "agente":
                _anexar_referencias(mensagem, bruto.get("referencias"))
            conversa.mensagens.append(mensagem)
        if ordem == 0:
            ignoradas += 1
            continue
        try:
            with db.begin_nested():
                db.add(conversa)
                db.flush()
        except IntegrityError:
            ignoradas += 1
            continue
        importadas += 1
        origens.append(origem)
    if usuario.perfil is not None and importadas:
        usuario.perfil.consentimento_sincronizacao = True
    db.commit()
    return {"importadas": importadas, "ignoradas": ignoradas, "origens": origens}


def _anexar_referencias(mensagem: MensagemRegistro, bruto: object) -> None:
    if not isinstance(bruto, list):
        return
    for item in bruto[:8]:
        if not isinstance(item, dict):
            continue
        aviso = item.get("aviso")
        codigo = item.get("id")
        if not isinstance(aviso, str) or not isinstance(codigo, str):
            continue
        notas = item.get("notas_fonte")
        mensagem.referencias.append(
            ReferenciaRegistro(
                id=uuid.uuid4(),
                mensagem_id=mensagem.id,
                codigo=codigo[:40],
                tipo="legislacao",
                verificada=bool(item.get("verificada")),
                norma=_curto(item.get("norma"), 180),
                numero=_curto(item.get("numero"), 40),
                ano=_curto(item.get("ano"), 10),
                artigo=_curto(item.get("artigo"), 40),
                url=_curto(item.get("url"), 500),
                consultado_em=_curto(item.get("consultado_em"), 40) or "",
                situacao=_curto(item.get("situacao"), 40) or "nao_verificada",
                tipo_texto=_curto(item.get("tipo_texto"), 80),
                vigencia_confirmada=False,
                notas_fonte=json.dumps(notas if isinstance(notas, list) else [], ensure_ascii=False),
                aviso=aviso[:2000],
            )
        )
