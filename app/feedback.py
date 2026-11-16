"""Registro estruturado de avaliação, sem o texto da conversa."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "dados" / "feedback.jsonl"
MOTIVOS = {"incorreta", "desatualizada", "incompleta", "confusa", "outro"}


def registrar_feedback(avaliacao: str, motivo: str | None, destino: Path | None = None) -> dict[str, str | None]:
    """Grava só o tipo da avaliação e, se houver, o motivo escolhido."""
    if avaliacao not in {"positiva", "negativa"}:
        raise ValueError("Avaliação inválida.")
    motivo_limpo = motivo if avaliacao == "negativa" and motivo in MOTIVOS else None
    registro: dict[str, str | None] = {
        "id": "fb-" + uuid4().hex[:12],
        "em": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds"),
        "avaliacao": avaliacao,
        "motivo": motivo_limpo,
    }
    caminho = destino or ARQUIVO
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro
