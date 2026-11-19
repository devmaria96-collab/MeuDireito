"""Acesso privado da homologação, com contas de teste e sem o banco real."""

import hashlib
import hmac
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.banco import exigir_fabrica, preparar_banco, redefinir_banco
from app.homologacao import (
    MENSAGEM_TOKEN,
    descrever_destino,
    eh_banco_de_desenvolvimento,
    migracao_de_postgres_permitida,
    token_de_acesso,
)
from app.limite import zerar
from app.main import app
from app.modelos import ConfirmacaoEmail, RedefinicaoSenha


_SENHA_ACESSO = "acesso-homologacao-teste"
_VARIAVEIS = (
    "DATABASE_URL",
    "AMBIENTE",
    "ACESSO_HOMOLOGACAO",
    "CONFIRMAR_MIGRACAO_HOMOLOGACAO",
    "NOME_COMERCIAL",
    "CONTROLADOR_PRIVACIDADE",
    "CONTATO_PRIVACIDADE",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
    "SMTP_HOST",
    "SMTP_DE",
    "URL_PUBLICA",
)


class HomologacaoTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = {nome: os.environ.get(nome) for nome in _VARIAVEIS}
        for nome in _VARIAVEIS:
            os.environ.pop(nome, None)
        pasta = tempfile.mkdtemp()
        self.arquivo = Path(pasta) / "homologacao.db"
        os.environ["DATABASE_URL"] = "sqlite:///" + self.arquivo.as_posix()
        os.environ["AMBIENTE"] = "homologacao"
        os.environ["ACESSO_HOMOLOGACAO"] = _SENHA_ACESSO
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

    def _liberar(self, cliente: TestClient | None = None) -> None:
        alvo = cliente or self.cliente
        resposta = alvo.post("/acesso/homologacao", json={"senha": _SENHA_ACESSO})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertNotIn(_SENHA_ACESSO, resposta.headers.get("set-cookie", ""))

    def test_sem_cookie_a_pesquisa_nao_chama_o_gemini(self) -> None:
        with patch("app.main.responder", new=AsyncMock(return_value=("não devia", []))) as agente:
            conversa = self.cliente.post("/conversar", json={"pergunta": "O que é usucapião?"})
            legislacao = self.cliente.post("/consultar-legislacao", json={"consulta": "artigo 5"})
            minuta = self.cliente.post("/documentos/gerar", json={})
        self.assertEqual(conversa.status_code, 403, conversa.text)
        self.assertEqual(legislacao.status_code, 403)
        self.assertEqual(minuta.status_code, 403)
        self.assertNotIn("usucapião", conversa.text)
        agente.assert_not_called()
        self.assertEqual(self.cliente.get("/openapi.json").status_code, 403)
        self.assertEqual(self.cliente.get("/saude").status_code, 200)
        self.assertEqual(self.cliente.get("/saude").json(), {"status": "ok"})
        estado = self.cliente.get("/acesso/homologacao")
        self.assertTrue(estado.json()["exigido"])
        self.assertFalse(estado.json()["liberado"])

    def test_senha_curta_ou_ausente_fecha_a_api(self) -> None:
        os.environ["ACESSO_HOMOLOGACAO"] = "curta"
        with patch("app.main.responder", new=AsyncMock(return_value=("não devia", []))) as agente:
            resposta = self.cliente.post("/conversar", json={"pergunta": "teste"})
        self.assertEqual(resposta.status_code, 503, resposta.text)
        agente.assert_not_called()
        os.environ.pop("ACESSO_HOMOLOGACAO")
        self.assertEqual(self.cliente.get("/acesso/homologacao").json()["configurado"], False)

    def test_cookie_libera_e_nao_guarda_a_senha(self) -> None:
        recusada = self.cliente.post("/acesso/homologacao", json={"senha": "senha-errada-homologacao"})
        self.assertEqual(recusada.status_code, 401, recusada.text)
        self.assertNotIn("set-cookie", recusada.headers)
        self._liberar()
        self.assertEqual(self.cliente.cookies.get("md_acesso"), token_de_acesso(_SENHA_ACESSO))
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))) as agente:
            resposta = self.cliente.post("/conversar", json={"pergunta": "Pergunta de teste."})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        agente.assert_called_once()
        self.assertEqual(self.cliente.post("/acesso/homologacao/sair").status_code, 200)
        bloqueada = self.cliente.post("/conversar", json={"pergunta": "outra"})
        self.assertEqual(bloqueada.status_code, 403)
        os.environ["COOKIE_SECURE"] = "1"
        os.environ["COOKIE_SAMESITE"] = "none"
        seguro = self.cliente.post("/acesso/homologacao", json={"senha": _SENHA_ACESSO})
        bruto = seguro.headers["set-cookie"].lower()
        self.assertIn("httponly", bruto)
        self.assertIn("secure", bruto)
        self.assertIn("samesite=none", bruto)
        self.assertNotIn(_SENHA_ACESSO, bruto)

    def test_limite_de_tentativas(self) -> None:
        for _ in range(8):
            self.assertEqual(
                self.cliente.post("/acesso/homologacao", json={"senha": "senha-errada-homologacao"}).status_code,
                401,
            )
        excesso = self.cliente.post("/acesso/homologacao", json={"senha": _SENHA_ACESSO})
        self.assertEqual(excesso.status_code, 429, excesso.text)

    def test_conta_confirmacao_recuperacao_isolamento_e_exclusao(self) -> None:
        self._liberar()
        cadastro = self.cliente.post(
            "/conta/cadastrar",
            json={"email": "ana@exemplo.com", "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": "Ana"},
        )
        self.assertEqual(cadastro.status_code, 200, cadastro.text)
        self.assertFalse(cadastro.json()["confirmacao_enviada"])
        self.assertIn("pendente", cadastro.json()["confirmacao_mensagem"])
        csrf = str(cadastro.json()["csrf"])
        recuperacao = self.cliente.post("/conta/recuperar-senha", json={"email": "ana@exemplo.com"})
        self.assertEqual(recuperacao.status_code, 503, recuperacao.text)
        self.assertIn("pendente", recuperacao.text)
        banco = exigir_fabrica()()
        try:
            self.assertEqual(banco.scalar(select(func.count()).select_from(ConfirmacaoEmail)), 0)
            self.assertEqual(banco.scalar(select(func.count()).select_from(RedefinicaoSenha)), 0)
        finally:
            banco.close()

        bruno = TestClient(app)
        bruno.__enter__()
        try:
            self._liberar(bruno)
            outro = bruno.post(
                "/conta/cadastrar",
                json={"email": "bruno@exemplo.com", "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": "Bruno"},
            )
            self.assertEqual(outro.status_code, 200, outro.text)
            pacote = {
                "conversas": [
                    {
                        "id": "local-ana",
                        "titulo": "Artigo 5",
                        "mensagens": [{"papel": "usuario", "conteudo": "O que diz o artigo 5º?"}],
                    }
                ]
            }
            importada = self.cliente.post("/conta/conversas/importar", json=pacote, headers={"X-CSRF-Token": csrf})
            self.assertEqual(importada.status_code, 200, importada.text)
            conversa_id = self.cliente.get("/conta/conversas").json()["conversas"][0]["id"]
            self.assertEqual(bruno.get(f"/conta/conversas/{conversa_id}").status_code, 404)
            apagada = self.cliente.request(
                "DELETE",
                "/conta",
                json={"senha": "senha-segura", "confirmacao": "EXCLUIR"},
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(apagada.status_code, 200, apagada.text)
            self.assertEqual(bruno.get("/conta/sessao").json()["autenticado"], True)
        finally:
            bruno.__exit__(None, None, None)

    def test_destino_de_desenvolvimento_nao_e_migrado(self) -> None:
        local = "postgresql+psycopg://meudireito:segredo-local@127.0.0.1:5434/meudireito"
        self.assertTrue(eh_banco_de_desenvolvimento(local))
        os.environ["CONFIRMAR_MIGRACAO_HOMOLOGACAO"] = "1"
        permitida, motivo = migracao_de_postgres_permitida(local)
        self.assertFalse(permitida)
        self.assertIn("desenvolvimento", motivo)
        self.assertNotIn("segredo-local", motivo)
        self.assertNotIn("segredo-local", descrever_destino(local).resumo())
        outro = "postgresql+psycopg://usuario:outra-senha@db.exemplo:5432/meudireito_homologacao"
        os.environ.pop("CONFIRMAR_MIGRACAO_HOMOLOGACAO", None)
        recusada, aviso = migracao_de_postgres_permitida(outro)
        self.assertFalse(recusada)
        self.assertIn("CONFIRMAR_MIGRACAO_HOMOLOGACAO", aviso)
        self.assertNotIn("outra-senha", aviso)
        os.environ["CONFIRMAR_MIGRACAO_HOMOLOGACAO"] = "1"
        aceita, _ = migracao_de_postgres_permitida(outro)
        self.assertTrue(aceita)
        os.environ["AMBIENTE"] = "invalido"
        bloqueada, texto = migracao_de_postgres_permitida(outro)
        self.assertFalse(bloqueada)
        self.assertIn("inválido", texto)

    def test_marca_nao_vira_controlador_nem_contato(self) -> None:
        self._liberar()
        os.environ["NOME_COMERCIAL"] = "Tavares Web"
        corpo = self.cliente.get("/lgpd").json()
        self.assertEqual(corpo["marca_comercial"], "Tavares Web")
        self.assertIsNone(corpo["controlador"])
        self.assertIsNone(corpo["contato"])
        texto = str(corpo)
        self.assertIn("não substitui a identificação legal", texto)
        self.assertNotIn("@", texto)

    def test_token_da_interface_confere_com_o_backend(self) -> None:
        modulo = Path(__file__).resolve().parents[1] / "frontend" / "src" / "acessoInterface.ts"
        script = Path(tempfile.mkdtemp()) / "token.mjs"
        script.write_text(
            "const m = await import(" + repr(modulo.as_uri()) + ");\n"
            "const segredo = " + repr(_SENHA_ACESSO) + ";\n"
            "const token = await m.tokenDeAcesso(segredo);\n"
            "if (!m.cookieConfere('md_acesso_interface=' + token, token)) process.exit(2);\n"
            "if (m.origemApiValida('https://api.exemplo') !== 'https://api.exemplo') process.exit(3);\n"
            "if (m.origemApiValida('https://usuario:segredo@api.exemplo') !== '') process.exit(4);\n"
            "if (m.origemApiValida('http://api.exemplo') !== '') process.exit(5);\n"
            "if (m.paginaDeAcesso('https://api.exemplo').includes(segredo)) process.exit(6);\n"
            "process.stdout.write(token);\n",
            encoding="utf-8",
        )
        resultado = subprocess.run(
            ["node", "--experimental-strip-types", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stdout, token_de_acesso(_SENHA_ACESSO))
        self.assertEqual(
            resultado.stdout,
            hmac.new(_SENHA_ACESSO.encode(), MENSAGEM_TOKEN, hashlib.sha256).hexdigest(),
        )

    def test_desenvolvimento_nao_exige_acesso(self) -> None:
        os.environ["AMBIENTE"] = "desenvolvimento"
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))):
            resposta = self.cliente.post("/conversar", json={"pergunta": "Pergunta de teste."})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertFalse(self.cliente.get("/acesso/homologacao").json()["exigido"])
        self.assertEqual(self.cliente.post("/acesso/homologacao", json={"senha": _SENHA_ACESSO}).status_code, 404)
