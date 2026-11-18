"""Avatares jurídicos e fotos normalizadas, sem metadados da câmera."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

AVATARES = (
    "balanca",
    "martelo",
    "livro",
    "constituicao",
    "coluna",
    "tribunal",
    "pergaminho",
    "estudante",
    "protecao",
)
PADRAO = "balanca"
LIMITE_BYTES = 2_000_000
PASTA = Path(__file__).resolve().parents[1] / "dados" / "avatares"


def avatar_valido(codigo: str) -> bool:
    return codigo in AVATARES


def caminho_imagem(usuario_id: str) -> Path:
    return PASTA / f"{usuario_id}.webp"


def _assinatura_aceita(bruto: bytes) -> bool:
    if bruto.startswith(b"\xff\xd8\xff"):
        return True
    if bruto.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    return len(bruto) >= 12 and bruto.startswith(b"RIFF") and bruto[8:12] == b"WEBP"


def normalizar_imagem(bruto: bytes) -> bytes:
    """Aceita JPEG, PNG ou WebP e devolve WebP quadrado, sem EXIF."""
    if not bruto or len(bruto) > LIMITE_BYTES:
        raise ValueError("A imagem passa do limite de 2 MB.")
    if bruto.startswith((b"MZ", b"\x7fELF")) or not _assinatura_aceita(bruto):
        raise ValueError("Envie uma imagem JPEG, PNG ou WebP.")
    try:
        with Image.open(io.BytesIO(bruto)) as imagem:
            imagem.verify()
        with Image.open(io.BytesIO(bruto)) as imagem:
            if imagem.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Envie uma imagem JPEG, PNG ou WebP.")
            quadro = imagem.convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError) as erro:
        if isinstance(erro, ValueError) and "JPEG" in str(erro):
            raise
        raise ValueError("Não foi possível ler a imagem.") from None
    quadro.thumbnail((512, 512))
    saida = io.BytesIO()
    quadro.save(saida, format="WEBP", quality=82)
    return saida.getvalue()


def guardar_imagem(usuario_id: str, bruto: bytes) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    caminho_imagem(usuario_id).write_bytes(normalizar_imagem(bruto))


def remover_imagem(usuario_id: str) -> None:
    caminho = caminho_imagem(usuario_id)
    if caminho.is_file():
        caminho.unlink()


def ler_imagem(usuario_id: str) -> bytes | None:
    caminho = caminho_imagem(usuario_id)
    if not caminho.is_file():
        return None
    return caminho.read_bytes()
