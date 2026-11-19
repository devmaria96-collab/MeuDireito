"""A descrição da LGPD só pode conter o que esta instalação realmente configura."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.banco import redefinir_banco
from app.limite import zerar
from app.main import app


class LgpdTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = {
            nome: os.environ.get(nome)
            for nome in (
                "CONTATO_PRIVACIDADE",
                "CONTROLADOR_PRIVACIDADE",
                "SMTP_HOST",
                "SMTP_DE",
                "SMTP_SENHA",
                "URL_PUBLICA",
                "DATABASE_URL",
            )
        }
        for nome in self._anterior:
            os.environ.pop(nome, None)
        pasta = tempfile.mkdtemp()
        os.environ["DATABASE_URL"] = "sqlite:///" + (Path(pasta) / "lgpd.db").as_posix()
        redefinir_banco()
        self.cliente = TestClient(app)

    def tearDown(self) -> None:
        for nome, valor in self._anterior.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor
        redefinir_banco()

    def test_publico_nao_inventa_responsavel_nem_contato(self) -> None:
        resposta = self.cliente.get("/lgpd")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.headers["x-content-type-options"], "nosniff")
        corpo = resposta.json()
        self.assertIs(corpo["conformidade_declarada"], False)
        self.assertIn("não declara conformidade", corpo["aviso"])
        self.assertIsNone(corpo["controlador"])
        self.assertIsNone(corpo["contato"])
        self.assertFalse(corpo["recuperacao_de_senha_configurada"])
        texto = json.dumps(corpo, ensure_ascii=False)
        self.assertNotIn("@", texto)
        chave = os.environ.get("GEMINI_API_KEY", "")
        if chave:
            self.assertNotIn(chave, texto)
        self.assertIn("Google Gemini", texto)
        self.assertIn("md_sessao", texto)
        self.assertIn("OpenAI", texto)
        self.assertIn("não grava a minuta", texto.lower())
        self.assertEqual(corpo["dias_retencao_exclusao"], 0)
        self.assertIn("/conversar", app.openapi()["paths"])

    def test_contato_e_responsavel_so_aparecem_se_configurados(self) -> None:
        os.environ["CONTATO_PRIVACIDADE"] = "privacidade@instituicao.example"
        os.environ["CONTROLADOR_PRIVACIDADE"] = "Responsável informado no ambiente"
        os.environ["SMTP_HOST"] = "smtp.interno.local"
        os.environ["SMTP_DE"] = "conta@instituicao.example"
        os.environ["SMTP_SENHA"] = "segredo-que-nao-pode-sair"
        os.environ["URL_PUBLICA"] = "https://instituicao.example"
        corpo = self.cliente.get("/lgpd").json()
        self.assertEqual(corpo["contato"], "privacidade@instituicao.example")
        self.assertEqual(corpo["controlador"], "Responsável informado no ambiente")
        self.assertTrue(corpo["recuperacao_de_senha_configurada"])
        texto = json.dumps(corpo, ensure_ascii=False)
        self.assertIn("smtp.interno.local", texto)
        self.assertNotIn("segredo-que-nao-pode-sair", texto)

    def test_pesquisa_publica_continua_sem_conta(self) -> None:
        self.assertIn("/lgpd", app.openapi()["paths"])
        self.assertNotIn("authorization", app.openapi()["paths"]["/lgpd"]["get"].get("security", []))
