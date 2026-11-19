"""Limites da demonstração para chamadas ao Gemini. Fora dela, não alteram o uso local."""

from __future__ import annotations

import os

from fastapi import HTTPException

from app.homologacao import modo_demonstracao
from app.limite import consumir


def _numero(nome: str, padrao: int, teto: int) -> int:
    try:
        valor = int(os.getenv(nome, "").strip() or padrao)
    except ValueError:
        valor = padrao
    return min(max(valor, 1), teto)


def cotas_publicas() -> dict[str, int] | None:
    if not modo_demonstracao():
        return None
    return {
        "por_acesso_em_24h": _numero("COTA_GEMINI_POR_IP", 15, 200),
        "coletivo_em_24h": _numero("COTA_GEMINI_GLOBAL", 300, 2000),
        "rajada_em_10min": _numero("COTA_GEMINI_RAJADA", 8, 30),
    }


def exigir_cota_gemini(origem: str) -> None:
    """Segura o consumo só na demonstração. O contador vive na memória do processo."""
    cotas = cotas_publicas()
    if cotas is None:
        return
    if not consumir(f"gemini-rajada:{origem}", limite=cotas["rajada_em_10min"], janela=600):
        raise HTTPException(
            status_code=429,
            detail="A demonstração limitou as pesquisas deste acesso. Aguarde alguns minutos.",
        )
    if not consumir(f"gemini-ip:{origem}", limite=cotas["por_acesso_em_24h"], janela=86400):
        raise HTTPException(
            status_code=429,
            detail="A demonstração atingiu o limite de pesquisas deste acesso. Tente novamente mais tarde.",
        )
    if not consumir("gemini-global", limite=cotas["coletivo_em_24h"], janela=86400):
        raise HTTPException(
            status_code=429,
            detail="A demonstração atingiu o limite coletivo de pesquisas. Tente novamente mais tarde.",
        )
