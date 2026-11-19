"""Senha, sessões, exportação e exclusão da própria conta."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from io import BytesIO
from sqlalchemy import select

from app.banco import exigir_fabrica, preparar_banco, redefinir_banco
from app.limite import zerar
from app.main import app
from app.modelos import ConversaRegistro, RedefinicaoSenha, RegistroExclusao, Usuario


class _Correio:
    def __init__(self) -> None:
        self.mensagens: list[object] = []

    def __enter__(self) -> "_Correio":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def starttls(self) -> None:
        return None

    def login(self, *_args: object) -> None:
        return None

    def send_message(self, mensagem: object) -> None:
        self.mensagens.append(mensagem)


class PrivacidadeContaTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = os.environ.get("DATABASE_URL")
        self._smtp = {nome: os.environ.get(nome) for nome in ("SMTP_HOST", "SMTP_DE", "URL_PUBLICA", "SMTP_TLS", "RETENCAO_REGISTRO_EXCLUSAO_DIAS")}
        for nome in self._smtp:
            os.environ.pop(nome, None)
        pasta = tempfile.mkdtemp()
        self.arquivo = Path(pasta) / "privacidade.db"
        os.environ["DATABASE_URL"] = "sqlite:///" + self.arquivo.as_posix()
        redefinir_banco()
        preparar_banco()
        self.cliente = TestClient(app)
        self.cliente.__enter__()

    def tearDown(self) -> None:
        self.cliente.__exit__(None, None, None)
        redefinir_banco()
        if self._anterior is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._anterior
        for nome, valor in self._smtp.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor
        zerar()

    def _cadastrar(self, cliente: TestClient, email: str, nome: str = "Pessoa", senha: str = "senha-segura") -> str:
        resposta = cliente.post(
            "/conta/cadastrar",
            json={"email": email, "senha": senha, "confirmar_senha": senha, "nome": nome},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return str(resposta.json()["csrf"])

    def test_visitante_nao_entra_nas_rotas_privadas_e_pesquisa_segue(self) -> None:
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))):
            pesquisa = self.cliente.post("/conversar", json={"pergunta": "O que é usucapião?"})
        self.assertEqual(pesquisa.status_code, 200)
        self.assertEqual(pesquisa.json()["resposta"], "Texto de teste.")
        self.assertEqual(self.cliente.get("/conta/sessoes").status_code, 401)
        self.assertEqual(self.cliente.get("/conta/dados").status_code, 401)
        self.assertEqual(self.cliente.get("/conta/privacidade").status_code, 401)
        self.assertEqual(
            self.cliente.request("DELETE", "/conta", json={"senha": "senha-segura", "confirmacao": "EXCLUIR"}).status_code,
            401,
        )
        self.assertNotIn("/conta/documentos", app.openapi()["paths"])

    def test_alterar_senha_revoga_as_outras_sessoes(self) -> None:
        csrf = self._cadastrar(self.cliente, "senha@exemplo.com")
        outro = TestClient(app)
        outro.__enter__()
        try:
            outro.post("/conta/entrar", json={"email": "senha@exemplo.com", "senha": "senha-segura"})
            with self.assertLogs("meu_direito", level="INFO") as registros:
                troca = self.cliente.post(
                    "/conta/senha",
                    json={"senha_atual": "senha-segura", "nova_senha": "senha-nova-secreta", "confirmar_senha": "senha-nova-secreta"},
                    headers={"X-CSRF-Token": csrf},
                )
            self.assertEqual(troca.status_code, 200, troca.text)
            self.assertNotIn("senha-nova-secreta", " ".join(registros.output))
            self.assertTrue(self.cliente.get("/conta/sessao").json()["autenticado"])
            self.assertFalse(outro.get("/conta/sessao").json()["autenticado"])
            antiga = outro.post("/conta/entrar", json={"email": "senha@exemplo.com", "senha": "senha-segura"})
            self.assertEqual(antiga.status_code, 401)
            nova = outro.post("/conta/entrar", json={"email": "senha@exemplo.com", "senha": "senha-nova-secreta"})
            self.assertEqual(nova.status_code, 200)
        finally:
            outro.__exit__(None, None, None)

    def test_senha_atual_errada_e_confirmacao(self) -> None:
        csrf = self._cadastrar(self.cliente, "errada@exemplo.com")
        errada = self.cliente.post(
            "/conta/senha",
            json={"senha_atual": "nao-e-esta", "nova_senha": "senha-nova-secreta", "confirmar_senha": "senha-nova-secreta"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(errada.status_code, 401)
        diferente = self.cliente.post(
            "/conta/senha",
            json={"senha_atual": "senha-segura", "nova_senha": "senha-nova-secreta", "confirmar_senha": "outra-senha-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(diferente.status_code, 422)

    def test_recuperacao_sem_correio_nao_revela_cadastro(self) -> None:
        self._cadastrar(self.cliente, "existe@exemplo.com")
        com_conta = self.cliente.post("/conta/recuperar-senha", json={"email": "existe@exemplo.com"})
        sem_conta = self.cliente.post("/conta/recuperar-senha", json={"email": "ninguem@exemplo.com"})
        self.assertEqual(com_conta.status_code, 503)
        self.assertEqual(sem_conta.status_code, 503)
        self.assertEqual(com_conta.json()["detail"], sem_conta.json()["detail"])
        self.assertIn("pendente", com_conta.json()["detail"])
        self.assertNotIn("enviado", com_conta.json()["detail"].lower())
        banco = exigir_fabrica()()
        try:
            self.assertEqual(banco.scalars(select(RedefinicaoSenha)).all(), [])
        finally:
            banco.close()

    def test_token_de_redefinicao_expira_e_nao_se_repete(self) -> None:
        self._cadastrar(self.cliente, "link@exemplo.com")
        os.environ["SMTP_HOST"] = "localhost"
        os.environ["SMTP_DE"] = "nao-responda@example.com"
        os.environ["URL_PUBLICA"] = "http://localhost:5173"
        os.environ["SMTP_TLS"] = "0"
        correio = _Correio()
        with patch("app.correio.smtplib.SMTP", return_value=correio):
            pedido = self.cliente.post("/conta/recuperar-senha", json={"email": "link@exemplo.com"})
            ausente = self.cliente.post("/conta/recuperar-senha", json={"email": "ausente@exemplo.com"})
        self.assertEqual(pedido.status_code, 200, pedido.text)
        self.assertEqual(ausente.status_code, 200)
        self.assertEqual(pedido.json()["mensagem"], ausente.json()["mensagem"])
        self.assertEqual(len(correio.mensagens), 1)
        texto = correio.mensagens[0].get_content()
        self.assertNotIn("senha-segura", texto)
        self.assertIn("Nenhuma senha é enviada", texto)
        token = texto.split("redefinir=", 1)[1].split()[0]
        banco = exigir_fabrica()()
        try:
            guardado = banco.scalars(select(RedefinicaoSenha)).one()
            self.assertNotIn(token, guardado.token_hash)
            guardado.expira_em = datetime.now(timezone.utc) - timedelta(minutes=1)
            banco.commit()
        finally:
            banco.close()
        expirado = self.cliente.post(
            "/conta/redefinir-senha",
            json={"token": token, "nova_senha": "senha-nova-secreta", "confirmar_senha": "senha-nova-secreta"},
        )
        self.assertEqual(expirado.status_code, 422)
        banco = exigir_fabrica()()
        try:
            guardado = banco.scalars(select(RedefinicaoSenha)).one()
            guardado.expira_em = datetime.now(timezone.utc) + timedelta(minutes=10)
            banco.commit()
        finally:
            banco.close()
        primeira = self.cliente.post(
            "/conta/redefinir-senha",
            json={"token": token, "nova_senha": "senha-nova-secreta", "confirmar_senha": "senha-nova-secreta"},
        )
        self.assertEqual(primeira.status_code, 200, primeira.text)
        segunda = self.cliente.post(
            "/conta/redefinir-senha",
            json={"token": token, "nova_senha": "senha-ainda-outra", "confirmar_senha": "senha-ainda-outra"},
        )
        self.assertEqual(segunda.status_code, 422)
        self.assertFalse(self.cliente.get("/conta/sessao").json()["autenticado"])
        antiga = self.cliente.post("/conta/entrar", json={"email": "link@exemplo.com", "senha": "senha-segura"})
        self.assertEqual(antiga.status_code, 401)
        nova = self.cliente.post("/conta/entrar", json={"email": "link@exemplo.com", "senha": "senha-nova-secreta"})
        self.assertEqual(nova.status_code, 200)

    def test_sessoes_nao_mostram_segredo_e_podem_ser_encerradas(self) -> None:
        csrf = self._cadastrar(self.cliente, "sessoes@exemplo.com")
        outro = TestClient(app)
        outro.__enter__()
        try:
            outro.post("/conta/entrar", json={"email": "sessoes@exemplo.com", "senha": "senha-segura"})
            lista = self.cliente.get("/conta/sessoes")
            self.assertEqual(lista.status_code, 200)
            corpo = lista.text
            self.assertNotIn("token", corpo)
            self.assertNotIn(self.cliente.cookies.get("md_sessao") or "ausente", corpo)
            self.assertEqual(sum(1 for item in lista.json()["sessoes"] if item["atual"]), 1)
            outras = self.cliente.delete("/conta/sessoes/outras", headers={"X-CSRF-Token": csrf})
            self.assertEqual(outras.status_code, 204)
            self.assertFalse(outro.get("/conta/sessao").json()["autenticado"])
            self.assertTrue(self.cliente.get("/conta/sessao").json()["autenticado"])
            todas = self.cliente.delete("/conta/sessoes", headers={"X-CSRF-Token": csrf})
            self.assertEqual(todas.status_code, 204)
            self.assertFalse(self.cliente.get("/conta/sessao").json()["autenticado"])
        finally:
            outro.__exit__(None, None, None)

    def test_exportacao_exclusao_e_isolamento(self) -> None:
        csrf = self._cadastrar(self.cliente, "dona@exemplo.com", "Dona")
        imagem = BytesIO()
        Image.new("RGB", (16, 16), (159, 18, 57)).save(imagem, format="PNG")
        self.assertEqual(
            self.cliente.post("/conta/avatar", files={"arquivo": ("foto.png", imagem.getvalue(), "image/png")}, headers={"X-CSRF-Token": csrf}).status_code,
            200,
        )
        with patch("app.rotas_historico.responder", new=AsyncMock(return_value=("Resposta da dona.", []))):
            criada = self.cliente.post(
                "/conta/conversas/perguntar",
                json={"pergunta": "pergunta exclusiva da dona"},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(criada.status_code, 200, criada.text)
        conversa_id = criada.json()["conversa"]["id"]
        dados = self.cliente.get("/conta/dados")
        self.assertEqual(dados.status_code, 200)
        self.assertIn("pergunta exclusiva da dona", dados.text)
        self.assertNotIn("senha_hash", dados.text)
        self.assertEqual(dados.json()["documentos_armazenados"], [])
        outro = TestClient(app)
        outro.__enter__()
        try:
            csrf_outro = self._cadastrar(outro, "outro@exemplo.com", "Outro")
            with patch("app.rotas_historico.responder", new=AsyncMock(return_value=("Resposta do outro.", []))):
                outro.post(
                    "/conta/conversas/perguntar",
                    json={"pergunta": "pergunta exclusiva do outro"},
                    headers={"X-CSRF-Token": csrf_outro},
                )
            self.assertEqual(outro.get(f"/conta/conversas/{conversa_id}").status_code, 404)
            self.assertEqual(outro.get("/conta/avatar").status_code, 404)
            self.assertNotIn("pergunta exclusiva da dona", outro.get("/conta/dados").text)
            os.environ["RETENCAO_REGISTRO_EXCLUSAO_DIAS"] = "0"
            banco = exigir_fabrica()()
            try:
                usuario = banco.scalar(select(Usuario).where(Usuario.email == "dona@exemplo.com"))
                self.assertIsNotNone(usuario)
                foto = Path("dados/avatares") / f"{usuario.id.hex}.webp"
            finally:
                banco.close()
            self.assertTrue(foto.is_file())
            apagada = self.cliente.request(
                "DELETE",
                "/conta",
                json={"senha": "senha-segura", "confirmacao": "EXCLUIR"},
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(apagada.status_code, 200, apagada.text)
            self.assertFalse(foto.is_file())
            self.assertFalse(self.cliente.get("/conta/sessao").json()["autenticado"])
            banco = exigir_fabrica()()
            try:
                self.assertIsNone(banco.scalar(select(Usuario).where(Usuario.email == "dona@exemplo.com")))
                self.assertIsNotNone(banco.scalar(select(Usuario).where(Usuario.email == "outro@exemplo.com")))
                self.assertEqual(banco.scalars(select(ConversaRegistro)).all().__len__(), 1)
                self.assertEqual(banco.scalars(select(RegistroExclusao)).all(), [])
                self.assertIn("pergunta exclusiva do outro", banco.scalars(select(ConversaRegistro)).one().titulo or "pergunta exclusiva do outro")
            finally:
                banco.close()
            self.assertEqual(outro.get("/conta/sessao").json()["usuario"]["nome_exibicao"], "Outro")
        finally:
            outro.__exit__(None, None, None)
            if foto.is_file():
                foto.unlink()

    def test_retencao_guarda_so_o_resumo_e_expira(self) -> None:
        csrf = self._cadastrar(self.cliente, "retencao@exemplo.com")
        os.environ["RETENCAO_REGISTRO_EXCLUSAO_DIAS"] = "15"
        apagada = self.cliente.request(
            "DELETE",
            "/conta",
            json={"senha": "senha-segura", "confirmacao": "EXCLUIR"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(apagada.status_code, 200, apagada.text)
        banco = exigir_fabrica()()
        try:
            registro = banco.scalars(select(RegistroExclusao)).one()
            self.assertNotIn("retencao@exemplo.com", registro.email_hash)
            self.assertEqual(len(registro.email_hash), 64)
            registro.expira_em = datetime.now(timezone.utc) - timedelta(days=1)
            banco.commit()
            from app.contas import purgar_retencao

            purgar_retencao(banco)
            self.assertEqual(banco.scalars(select(RegistroExclusao)).all(), [])
        finally:
            banco.close()


if __name__ == "__main__":
    unittest.main()
