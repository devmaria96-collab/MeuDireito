"""Envio de redefinição de senha. Sem serviço configurado, nada é enviado."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("meu_direito")


def correio_configurado() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_DE", "").strip() and _url_publica())


def _url_publica() -> str:
    url = os.getenv("URL_PUBLICA", "").strip().rstrip("/")
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return ""


def link_de_redefinicao(token: str) -> str:
    return f"{_url_publica()}/?redefinir={token}"


def link_de_confirmacao(token: str) -> str:
    return f"{_url_publica()}/?confirmar={token}"


def _enviar(mensagem: EmailMessage) -> None:
    """Entrega a mensagem no SMTP configurado. Sem serviço, não há envio simulado."""
    if not correio_configurado():
        raise RuntimeError("Correio indisponível.")
    porta = int(os.getenv("SMTP_PORT", "587") or "587")
    with smtplib.SMTP(os.environ["SMTP_HOST"].strip(), porta, timeout=10) as smtp:
        if os.getenv("SMTP_TLS", "1").lower() not in {"0", "false"}:
            smtp.starttls()
        usuario = os.getenv("SMTP_USUARIO", "").strip()
        if usuario:
            smtp.login(usuario, os.getenv("SMTP_SENHA", ""))
        smtp.send_message(mensagem)


def enviar_redefinicao(destino: str, link: str) -> None:
    """Envia só o link. A senha não entra na mensagem nem no log."""
    mensagem = EmailMessage()
    mensagem["Subject"] = "Redefinir a senha do Meu Direito"
    mensagem["From"] = os.environ["SMTP_DE"].strip()
    mensagem["To"] = destino
    mensagem.set_content(
        "Recebemos um pedido para redefinir a senha da sua conta no Meu Direito.\n\n"
        "Abra o link abaixo nos próximos 30 minutos. Ele funciona uma única vez:\n"
        f"{link}\n\n"
        "Se você não pediu a redefinição, ignore este e-mail. Nenhuma senha é enviada por e-mail.\n"
    )
    _enviar(mensagem)
    logger.info("Link de redefinição enviado")


def enviar_confirmacao(destino: str, link: str) -> None:
    """Envia só o link de confirmação. A senha não entra na mensagem nem no log."""
    mensagem = EmailMessage()
    mensagem["Subject"] = "Confirmar o e-mail do Meu Direito"
    mensagem["From"] = os.environ["SMTP_DE"].strip()
    mensagem["To"] = destino
    mensagem.set_content(
        "Recebemos um cadastro no Meu Direito com este endereço.\n\n"
        "Abra o link abaixo nas próximas 24 horas para confirmá-lo. Ele funciona uma única vez:\n"
        f"{link}\n\n"
        "Se você não criou a conta, ignore este e-mail. Nenhuma senha é enviada por e-mail.\n"
    )
    _enviar(mensagem)
    logger.info("Link de confirmação enviado")
