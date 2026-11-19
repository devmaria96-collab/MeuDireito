"""Demonstração de portfólio: sem conta, com limite do Gemini e sugestão sem dado pessoal."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.banco import preparar_banco, redefinir_banco
from app.limite import zerar
from app.main import app


class DemonstracaoTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = {
            nome: os.environ.get(nome)
            for nome in (
                "DATABASE_URL",
                "AMBIENTE",
                "COTA_GEMINI_POR_IP",
                "COTA_GEMINI_GLOBAL",
                "COTA_GEMINI_RAJADA",
                "SUGESTOES_ARQUIVO",
                "NOME_COMERCIAL",
                "CONTROLADOR_PRIVACIDADE",
                "CONTATO_PRIVACIDADE",
            )
        }
        for nome in self._anterior:
            os.environ.pop(nome, None)
        self.pasta = Path(tempfile.mkdtemp())
        os.environ["DATABASE_URL"] = "sqlite:///" + (self.pasta / "demo.db").as_posix()
        os.environ["AMBIENTE"] = "demonstracao"
        os.environ["SUGESTOES_ARQUIVO"] = str(self.pasta / "sugestoes.jsonl")
        os.environ["COTA_GEMINI_POR_IP"] = "2"
        os.environ["COTA_GEMINI_GLOBAL"] = "5"
        os.environ["COTA_GEMINI_RAJADA"] = "10"
        redefinir_banco()
        preparar_banco()
        self.cliente = TestClient(app)
        self.cliente.__enter__()

    def tearDown(self) -> None:
        self.cliente.__exit__(None, None, None)
        redefinir_banco()
        for nome, valor in self._anterior.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor
        zerar()

    def test_cadastro_fica_desligado_e_a_pesquisa_continua(self) -> None:
        modo = self.cliente.get("/modo")
        self.assertEqual(modo.status_code, 200, modo.text)
        self.assertTrue(modo.json()["demonstracao"])
        self.assertFalse(modo.json()["cadastro_disponivel"])
        self.assertEqual(modo.json()["identificacao"], "Versão experimental — Projeto de portfólio")
        self.assertEqual(modo.json()["cotas_gemini"]["por_acesso_em_24h"], 2)
        sessao = self.cliente.get("/conta/sessao")
        self.assertFalse(sessao.json()["contas_disponiveis"])
        self.assertTrue(sessao.json()["demonstracao"])
        cadastro = self.cliente.post(
            "/conta/cadastrar",
            json={"email": "ana@exemplo.com", "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": "Ana"},
        )
        self.assertEqual(cadastro.status_code, 403, cadastro.text)
        self.assertIn("desligado", cadastro.text)
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))):
            pesquisa = self.cliente.post("/conversar", json={"pergunta": "O que diz o artigo 5º?"})
        self.assertEqual(pesquisa.status_code, 200, pesquisa.text)
        self.assertEqual(pesquisa.json()["resposta"], "Texto de teste.")

    def test_limite_do_gemini_nao_chama_o_modelo_depois_da_cota(self) -> None:
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))) as agente:
            primeira = self.cliente.post("/conversar", json={"pergunta": "Primeira pergunta de teste."})
            segunda = self.cliente.post("/conversar", json={"pergunta": "Segunda pergunta de teste."})
            terceira = self.cliente.post("/conversar", json={"pergunta": "Terceira pergunta de teste."})
        self.assertEqual(primeira.status_code, 200, primeira.text)
        self.assertEqual(segunda.status_code, 200, segunda.text)
        self.assertEqual(terceira.status_code, 429, terceira.text)
        self.assertEqual(agente.call_count, 2)
        self.assertNotIn("Terceira", terceira.text)

    def test_sugestao_nao_guarda_contato(self) -> None:
        boa = self.cliente.post("/sugestoes", json={"texto": "Explicar melhor a diferença entre o texto oficial e a explicação."})
        self.assertEqual(boa.status_code, 204, boa.text)
        ruim = self.cliente.post("/sugestoes", json={"texto": "Me escrevam em ana@exemplo.com por favor."})
        self.assertEqual(ruim.status_code, 422, ruim.text)
        arquivo = (self.pasta / "sugestoes.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("@", arquivo)
        self.assertIn("texto oficial", arquivo)

    def test_politica_descreve_a_demonstracao_sem_conta(self) -> None:
        corpo = self.cliente.get("/lgpd").json()
        self.assertTrue(corpo["modo_demonstracao"])
        self.assertIn("Versão experimental", corpo["identificacao"])
        self.assertIn("banco de contas", corpo["aviso_demonstracao"].lower())
        texto = str(corpo["inventario"])
        self.assertIn("Sugestão", texto)
        self.assertNotIn("@", str(corpo))
        self.assertIsNone(corpo["controlador"])
        self.assertIsNone(corpo["contato"])

    def test_desenvolvimento_continua_com_cadastro(self) -> None:
        os.environ["AMBIENTE"] = "desenvolvimento"
        redefinir_banco()
        preparar_banco()
        outro = TestClient(app)
        outro.__enter__()
        try:
            self.assertFalse(outro.get("/modo").json()["demonstracao"])
            cadastro = outro.post(
                "/conta/cadastrar",
                json={"email": "ana@exemplo.com", "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": "Ana"},
            )
            self.assertEqual(cadastro.status_code, 200, cadastro.text)
        finally:
            outro.__exit__(None, None, None)
