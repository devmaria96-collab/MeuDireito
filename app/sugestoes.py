"""Sugestão da demonstração, sem nome, e-mail ou texto da pesquisa."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "dados" / "sugestoes.jsonl"
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_DIGITO_LONGO = re.compile(r"\d{10,}")


def caminho_das_sugestoes() -> Path:
    informado = os.getenv("SUGESTOES_ARQUIVO", "").strip()
    return Path(informado) if informado else ARQUIVO


def registrar_sugestao(texto: str, destino: Path | None = None) -> dict[str, str]:
    limpo = " ".join(texto.split())
    if len(limpo) < 5 or len(limpo) > 500:
        raise ValueError("tamanho")
    if "@" in limpo or _EMAIL.search(limpo) or _DIGITO_LONGO.search(limpo):
        raise ValueError("pessoal")
    registro = {
        "id": "sg-" + uuid4().hex[:12],
        "em": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds"),
        "texto": limpo,
    }
    caminho = destino or caminho_das_sugestoes()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro
