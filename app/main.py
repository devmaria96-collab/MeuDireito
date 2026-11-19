"""Aplicação FastAPI do agente."""

import asyncio
import hashlib
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app.agente import carregar_chave_gemini, explicar_consulta, responder
from app.banco import preparar_banco
from app.rotas_conta import router as rotas_conta
from app.rotas_historico import router as rotas_historico
from app.consulta_legislacao import ResultadoConsulta, consultar
from app.feedback import registrar_feedback
from app.legislacao import AVISO_SEM_CONSULTA, FONTES_OFICIAIS
from app.limite import consumir
from app.minutas import (
    ErroExportacao,
    ErroFormulario,
    exportar_docx,
    exportar_pdf,
    gerar_minuta,
)

_PADRAO_OPENAI = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
_PADRAO_AIZA = re.compile(r"AIza[0-9A-Za-z_\-]{10,}")
_PADRAO_AQ = re.compile(r"AQ\.[A-Za-z0-9_\-.]{8,}")
_PADRAO_ATRIBUICAO = re.compile(
    r"(?:GEMINI_API_KEY|GOOGLE_API_KEY|OPENAI_API_KEY)=\S+"
)
logger = logging.getLogger("meu_direito")


@asynccontextmanager
async def _ciclo_de_vida(_aplicacao: FastAPI):
    preparar_banco()
    from app.banco import contas_disponiveis, exigir_fabrica
    from app.contas import purgar_retencao

    if contas_disponiveis():
        banco = exigir_fabrica()()
        try:
            purgar_retencao(banco)
        finally:
            banco.close()
    from app.lgpd import pendencias_administrador

    for item in pendencias_administrador():
        logger.warning("Pendência de publicação: %s", item)
    yield


app = FastAPI(
    title="Meu Direito",
    description="O conhecimento jurídico ao seu alcance. Assistente de pesquisa jurídica sobre o Direito brasileiro.",
    version="0.1.0",
    lifespan=_ciclo_de_vida,
)

from app.homologacao import AcessoHomologacaoMiddleware
from app.homologacao import router as rotas_homologacao
from app.publicacao import hosts_de_proxy, origens_permitidas, proxy_confiavel

app.add_middleware(AcessoHomologacaoMiddleware)

if proxy_confiavel():
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=hosts_de_proxy())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def _cabecalhos_de_seguranca(pedido: Request, seguinte):  # type: ignore[no-untyped-def]
    """Evita farejar o tipo do arquivo e, em HTTPS, pede a permanência do transporte seguro."""
    resposta = await seguinte(pedido)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    if pedido.url.scheme == "https":
        resposta.headers["Strict-Transport-Security"] = "max-age=31536000"
    return resposta

app.include_router(rotas_homologacao)
app.include_router(rotas_conta)
app.include_router(rotas_historico)


class PerguntaEntrada(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=8000, description="Pergunta enviada ao agente.")
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


class ReferenciaSaida(BaseModel):
    id: str
    tipo: Literal["legislacao"]
    verificada: bool
    norma: str | None = None
    numero: str | None = None
    ano: str | None = None
    artigo: str | None = None
    tribunal: str | None = None
    processo: str | None = None
    relator: str | None = None
    data_decisao: str | None = None
    url: str | None = None
    consultado_em: str
    situacao: str
    tipo_texto: str | None = None
    vigencia_confirmada: bool = False
    notas_fonte: list[str] = Field(default_factory=list)
    aviso: str


class RespostaSaida(BaseModel):
    resposta: str
    referencias: list[ReferenciaSaida] = Field(default_factory=list)


def _exigir_limite(pedido: Request) -> None:
    """Segura rajadas sem registrar o conteúdo da pergunta."""
    origem = pedido.client.host if pedido.client else "local"
    if not consumir(origem):
        raise HTTPException(
            status_code=429,
            detail="Muitas consultas em sequência. Aguarde um minuto e tente de novo.",
        )


def _texto_sem_credenciais(erro: Exception) -> str:
    """Remove chaves e atribuições do texto de uma exceção."""
    texto = str(erro)
    for nome in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
        chave = os.getenv(nome) or ""
        if chave and chave in texto:
            texto = texto.replace(chave, "")
    texto = _PADRAO_OPENAI.sub("", texto)
    texto = _PADRAO_AIZA.sub("", texto)
    texto = _PADRAO_AQ.sub("", texto)
    texto = _PADRAO_ATRIBUICAO.sub("", texto)
    return " ".join(texto.split())


def _cadeia_do_erro(erro: BaseException) -> str:
    """Junta nomes e textos da exceção e das causas, já sem credenciais."""
    partes: list[str] = []
    atual: BaseException | None = erro
    vistos: set[int] = set()
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        partes.append(type(atual).__name__)
        partes.append(_texto_sem_credenciais(atual))
        atual = atual.__cause__ or atual.__context__
    return " ".join(partes)


def _detalhe_seguro(erro: Exception) -> tuple[int, str]:
    """Classifica a falha sem devolver credenciais ou texto técnico ao cliente."""
    texto = _cadeia_do_erro(erro)
    baixo = texto.lower()
    nomes = {parte.lower() for parte in texto.split()}

    autenticacao = bool(nomes & {"authenticationerror", "permissiondeniederror"}) or any(
        trecho in baixo
        for trecho in (
            "incorrect api key",
            "invalid api key",
            "api key not valid",
            "api_key_invalid",
            "invalid_api_key",
            "unauthenticated",
            "permission denied",
            "error code: 401",
            "error code: 403",
        )
    )
    if autenticacao:
        return (
            401,
            "A chave do Gemini foi recusada. Verifique a configuração no backend.",
        )

    sem_credito = any(
        trecho in baixo
        for trecho in (
            "insufficient credit",
            "insufficient_quota",
            "billing",
            "payment required",
            "quota exceeded",
            "exceeded your current quota",
            "prepayment",
            "error code: 402",
        )
    )
    if sem_credito:
        return (
            402,
            "A conta do Gemini está sem créditos ou cota disponível.",
        )

    limite = bool(nomes & {"ratelimiterror"}) or any(
        trecho in baixo
        for trecho in (
            "rate limit",
            "ratelimit",
            "too many requests",
            "error code: 429",
            "resource_exhausted",
            "resource exhausted",
        )
    )
    if limite:
        return (
            429,
            "O limite de requisições do Gemini foi excedido. Aguarde um instante e tente novamente.",
        )

    tempo_limite = bool(nomes & {"timeouterror", "apitimeouterror"}) or any(
        trecho in baixo
        for trecho in (
            "timed out",
            "timeout",
            "deadline exceeded",
            "error code: 504",
        )
    )
    if tempo_limite:
        return (
            504,
            "A resposta excedeu o tempo limite. Tente novamente.",
        )

    indisponivel = bool(nomes & {"serviceunavailableerror"}) or any(
        trecho in baixo
        for trecho in (
            "high demand",
            "overloaded",
            "temporarily unavailable",
            "service unavailable",
            "error code: 503",
            "unavailable",
        )
    )
    if indisponivel:
        return (
            503,
            "O Gemini está temporariamente indisponível. Tente novamente em instantes.",
        )

    conexao = bool(nomes & {"apiconnectionerror", "connecterror"}) or any(
        trecho in baixo
        for trecho in (
            "connection error",
            "connecterror",
            "network",
            "name or service not known",
        )
    )
    if conexao:
        return (
            503,
            "Não foi possível conectar ao Gemini. Verifique a internet e tente novamente.",
        )

    return 500, "O backend encontrou um erro interno ao processar a resposta."


@app.get("/lgpd")
def ler_lgpd(pedido: Request) -> dict[str, object]:
    """Descreve o tratamento desta instalação. Não exige conta e não declara conformidade."""
    from app.lgpd import panorama

    origem = pedido.client.host if pedido.client else "local"
    if not consumir(f"lgpd:{origem}", limite=60):
        raise HTTPException(status_code=429, detail="Muitas consultas em sequência. Aguarde um minuto e tente de novo.")
    return panorama(pedido.url.scheme == "https")


@app.get("/fontes-oficiais")
async def fontes_oficiais() -> dict[str, object]:
    """Apresenta portais oficiais sem consultar o conteúdo deles."""
    return {
        "verificacao_em_tempo_real": False,
        "aviso": AVISO_SEM_CONSULTA,
        "fontes": FONTES_OFICIAIS,
    }


class ConsultaLegislacaoEntrada(BaseModel):
    consulta: str = Field(..., min_length=1, max_length=500, description="Lei ou artigo a localizar.")
    perfil: Literal["estudante", "profissional", "cidadao"] | None = None


class ConsultaLegislacaoSaida(BaseModel):
    verificada: bool
    norma: str | None
    numero: str | None
    ano: str | None
    artigo: str | None
    texto_oficial: str | None
    url: str | None
    consultado_em: str
    aviso: str
    explicacao: str | None
    aviso_explicacao: str | None
    situacao: str = "nao_verificada"
    tipo_texto: str | None = None
    vigencia_confirmada: bool = False
    notas_fonte: list[str] = Field(default_factory=list)


@app.post("/consultar-legislacao", response_model=ConsultaLegislacaoSaida)
async def consultar_legislacao_endpoint(
    entrada: ConsultaLegislacaoEntrada,
    pedido: Request,
) -> ConsultaLegislacaoSaida:
    """Lê um artigo no Planalto e, se a leitura ocorrer, pede uma explicação separada."""
    _exigir_limite(pedido)
    resultado = await asyncio.to_thread(consultar, entrada.consulta.strip())
    explicacao: str | None = None
    aviso_explicacao: str | None = None
    if resultado.verificada and resultado.texto_oficial:
        try:
            explicacao = await explicar_consulta(resultado.como_texto(), entrada.perfil)
        except Exception as erro:
            status, detalhe = _detalhe_seguro(erro)
            logger.warning("Falha ao explicar legislação: %s, HTTP %s", type(erro).__name__, status)
            aviso_explicacao = detalhe
    return ConsultaLegislacaoSaida(
        verificada=resultado.verificada,
        norma=resultado.norma,
        numero=resultado.numero,
        ano=resultado.ano,
        artigo=resultado.artigo,
        texto_oficial=resultado.texto_oficial,
        url=resultado.url if resultado.url and resultado.url.startswith("https://www.planalto.gov.br/") else None,
        consultado_em=resultado.consultado_em,
        aviso=resultado.aviso,
        explicacao=explicacao,
        aviso_explicacao=aviso_explicacao,
        situacao=resultado.situacao,
        tipo_texto=resultado.tipo_texto,
        vigencia_confirmada=False,
        notas_fonte=list(resultado.notas_fonte),
    )


class GerarDocumentoEntrada(BaseModel):
    tipo: Literal[
        "contrato",
        "notificacao",
        "requerimento",
        "declaracao",
        "peticao_inicial",
        "parecer",
        "procuracao",
        "personalizado",
    ]
    campos: dict[str, str]
    perfil: Literal["estudante", "profissional", "cidadao"] | None = None

    @field_validator("campos")
    @classmethod
    def _limitar_campos(cls, campos: dict[str, str]) -> dict[str, str]:
        if len(campos) > 30:
            raise ValueError("O formulário tem campos demais.")
        limpos: dict[str, str] = {}
        for chave, valor in campos.items():
            if len(chave) > 40 or len(valor) > 4000:
                raise ValueError("Um campo do formulário é longo demais.")
            limpos[chave.strip()] = valor
        return limpos


class DocumentoGeradoSaida(BaseModel):
    titulo: str
    tipo: str
    html: str
    pendencias: list[str]
    aviso: str


class ExportarDocumentoEntrada(BaseModel):
    formato: Literal["pdf", "docx"]
    titulo: str = Field(default="Minuta", max_length=120)
    html: str = Field(..., min_length=1, max_length=80_000)


@app.post("/documentos/gerar", response_model=DocumentoGeradoSaida)
async def gerar_documento(entrada: GerarDocumentoEntrada, pedido: Request) -> DocumentoGeradoSaida:
    """Elabora uma minuta com o Gemini a partir dos campos revistos pela pessoa."""
    _exigir_limite(pedido)
    carregar_chave_gemini()
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Defina GEMINI_API_KEY no arquivo .env antes de gerar uma minuta.",
        )
    logger.info("Minuta solicitada: tipo=%s", entrada.tipo)
    try:
        pronta = await gerar_minuta(entrada.tipo, entrada.campos, entrada.perfil)
    except ErroFormulario as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from None
    except Exception as erro:
        status, detalhe = _detalhe_seguro(erro)
        logger.warning("Falha ao gerar minuta: %s, HTTP %s", type(erro).__name__, status)
        raise HTTPException(status_code=status, detail=detalhe) from None
    return DocumentoGeradoSaida(
        titulo=pronta.titulo,
        tipo=pronta.tipo,
        html=pronta.html,
        pendencias=pronta.pendencias,
        aviso=pronta.aviso,
    )


@app.post("/documentos/exportar")
async def exportar_documento(entrada: ExportarDocumentoEntrada, pedido: Request) -> Response:
    """Converte a minuta editada em PDF ou Word, sem assinatura ou autenticação."""
    _exigir_limite(pedido)
    logger.info("Exportação de minuta: formato=%s", entrada.formato)
    try:
        if entrada.formato == "pdf":
            conteudo = exportar_pdf(entrada.titulo, entrada.html)
            media = "application/pdf"
            nome = "minuta.pdf"
        else:
            conteudo = exportar_docx(entrada.titulo, entrada.html)
            media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            nome = "minuta.docx"
    except ErroExportacao as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from None
    except Exception as erro:
        logger.warning("Falha ao exportar minuta: %s", type(erro).__name__)
        raise HTTPException(status_code=500, detail="Não foi possível exportar o documento.") from None
    return Response(
        content=conteudo,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


def _referencia_de(item: ResultadoConsulta) -> ReferenciaSaida:
    """Monta a referência só com o que a consulta ao Planalto devolveu."""
    confirmada = bool(
        item.verificada
        and item.texto_oficial
        and item.url
        and item.url.startswith("https://www.planalto.gov.br/")
    )
    base = "|".join(
        (
            str(confirmada),
            item.url or "",
            item.artigo or "",
            item.consultado_em,
            item.situacao,
        )
    )
    return ReferenciaSaida(
        id="ref-" + hashlib.sha256(base.encode()).hexdigest()[:12],
        tipo="legislacao",
        verificada=confirmada,
        norma=item.norma,
        numero=item.numero,
        ano=item.ano,
        artigo=item.artigo,
        url=item.url if confirmada else None,
        consultado_em=item.consultado_em,
        situacao=item.situacao if confirmada else "nao_verificada",
        tipo_texto=item.tipo_texto if confirmada else None,
        vigencia_confirmada=False,
        notas_fonte=list(item.notas_fonte) if confirmada else [],
        aviso=item.aviso,
    )


@app.post("/conversar", response_model=RespostaSaida)
async def conversar(entrada: PerguntaEntrada, pedido: Request) -> RespostaSaida:
    """Recebe uma pergunta e devolve a resposta do agente."""
    _exigir_limite(pedido)
    carregar_chave_gemini()
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Defina GEMINI_API_KEY no arquivo .env antes de conversar com o agente.",
        )

    try:
        texto, consultas = await responder(
            entrada.pergunta.strip(),
            entrada.perfil,
            entrada.tipo_documento,
        )
    except Exception as erro:
        status, detalhe = _detalhe_seguro(erro)
        logger.warning("Falha ao conversar: %s, HTTP %s", type(erro).__name__, status)
        raise HTTPException(status_code=status, detail=detalhe) from None

    vistas: dict[str, ReferenciaSaida] = {}
    for item in consultas:
        referencia = _referencia_de(item)
        vistas.setdefault(referencia.id, referencia)
    return RespostaSaida(resposta=texto, referencias=list(vistas.values()))


class FeedbackEntrada(BaseModel):
    avaliacao: Literal["positiva", "negativa"]
    motivo: Literal["incorreta", "desatualizada", "incompleta", "confusa", "outro"] | None = None


@app.post("/feedback", status_code=204)
async def receber_feedback(entrada: FeedbackEntrada, pedido: Request) -> Response:
    """Registra a avaliação sem a pergunta, a resposta ou dados pessoais."""
    _exigir_limite(pedido)
    try:
        registrar_feedback(entrada.avaliacao, entrada.motivo)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail="Não foi possível registrar a avaliação.") from erro
    logger.info("Avaliação registrada: %s", entrada.avaliacao)
    return Response(status_code=204)
