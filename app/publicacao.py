"""Ajustes de publicação lidos do ambiente. Valores vazios não são inventados."""

from __future__ import annotations

import os

_ORIGENS_LOCAIS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def origens_permitidas() -> list[str]:
    """Junta o ambiente local às origens HTTPS ou HTTP informadas, sem curinga."""
    origens = list(_ORIGENS_LOCAIS)
    for item in os.getenv("ORIGENS_PERMITIDAS", "").split(","):
        origem = item.strip().rstrip("/")
        if not origem.startswith(("https://", "http://")) or any(caractere in origem for caractere in " *"):
            continue
        if "/" in origem.split("://", 1)[1]:
            continue
        if origem not in origens:
            origens.append(origem)
    return origens


def cookie_seguro(esquema: str) -> bool:
    return esquema == "https" or os.getenv("COOKIE_SECURE", "").lower() in {"1", "true"}


def cookie_samesite(seguro: bool) -> str:
    """None só vale com Secure. O padrão continua Lax."""
    pedido = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
    if pedido == "none" and seguro:
        return "none"
    if pedido == "strict":
        return "strict"
    return "lax"


def proxy_confiavel() -> bool:
    return os.getenv("PROXY_CONFIAVEL", "").lower() in {"1", "true"}


def hosts_de_proxy() -> list[str]:
    hosts = [item.strip() for item in os.getenv("PROXY_HOSTS", "127.0.0.1").split(",") if item.strip()]
    return hosts or ["127.0.0.1"]
