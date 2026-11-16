"""Limite simples de consultas por endereço, só em memória."""

from __future__ import annotations

import threading
import time

_chamadas: dict[str, list[float]] = {}
_trava = threading.Lock()
LIMITE = 30
JANELA = 60.0


def consumir(chave: str, *, limite: int = LIMITE, janela: float = JANELA, agora: float | None = None) -> bool:
    """Devolve False quando a chave já estourou o limite na janela."""
    momento = time.monotonic() if agora is None else agora
    with _trava:
        recentes = [marca for marca in _chamadas.get(chave, []) if momento - marca < janela]
        if len(recentes) >= limite:
            _chamadas[chave] = recentes
            return False
        recentes.append(momento)
        _chamadas[chave] = recentes
        return True


def zerar() -> None:
    with _trava:
        _chamadas.clear()
