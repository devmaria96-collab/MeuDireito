"""Confirmação de e-mail, cookies e origens, só com contas de teste."""

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.banco import exigir_fabrica, preparar_banco, redefinir_banco
from app.limite import zerar
from app.main import app
from app.modelos import ConfirmacaoEmail, Usuario
from app.publicacao import cookie_samesite, cookie_seguro, origens_permitidas


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


class PublicacaoTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = {
            nome: os.environ.get(nome)
            for nome in (
                "DATABASE_URL",
                "SMTP_HOST",
                "SMTP_DE",
                "SMTP_SENHA",
                "URL_PUBLICA",
                "COOKIE_SECURE",
                "COOKIE_SAMESITE",
                "ORIGENS_PERMITIDAS",
                "CONTROLADOR_PRIVACIDADE",
                "CONTATO_PRIVACIDADE",
            )
        }
        for nome in self._anterior:
            os.environ.pop(nome, None)
        pasta = tempfile.mkdtemp()
        os.environ["DATABASE_URL"] = "sqlite:///" + (Path(pasta) / "publicacao.db").as_posix()
        redefinir_banco()
        preparar_banco()
        self.cliente = TestClient(app)

    def tearDown(self) -> None:
        for nome, valor in self._anterior.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor
        redefinir_banco()

    def _cadastrar(self, email: str = "teste.publicacao@exemplo.com") -> dict[str, object]:
        resposta = self.cliente.post(
            "/conta/cadastrar",
            json={"email": email, "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": "Teste"},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return resposta.json()

    def test_sem_smtp_nao_simula_confirmacao_e_a_pesquisa_segue(self) -> None:
        corpo = self._cadastrar()
        self.assertFalse(corpo["confirmacao_enviada"])
        self.assertIn("pendente", str(corpo["confirmacao_mensagem"]))
        self.assertNotIn("Enviamos", str(corpo["confirmacao_mensagem"]))
        self.assertFalse(corpo["usuario"]["email_confirmado"])
        with exigir_fabrica()() as banco:
            self.assertEqual(len(banco.scalars(select(ConfirmacaoEmail)).all()), 0)
        reenvio = self.cliente.post("/conta/reenviar-confirmacao", json={"email": "naoexiste@exemplo.com"})
        self.assertEqual(reenvio.status_code, 503)
        self.assertIn("pendente", reenvio.json()["detail"])
        with patch("app.main.responder", new=AsyncMock(return_value=("Resposta de teste.", []))):
            pesquisa = self.cliente.post("/conversar", json={"pergunta": "O que é um contrato?"})
        self.assertEqual(pesquisa.status_code, 200)

    def test_confirmacao_real_expira_e_nao_se_repete(self) -> None:
        os.environ["SMTP_HOST"] = "smtp.teste.local"
        os.environ["SMTP_DE"] = "conta@teste.local"
        os.environ["SMTP_SENHA"] = "segredo-que-nao-pode-sair"
        os.environ["URL_PUBLICA"] = "https://teste.local"
        correio = _Correio()
        with patch("app.correio.smtplib.SMTP", return_value=correio):
            corpo = self._cadastrar("confirma@exemplo.com")
        self.assertTrue(corpo["confirmacao_enviada"])
        self.assertEqual(len(correio.mensagens), 1)
        mensagem = correio.mensagens[0]
        bruto = str(mensagem)
        self.assertNotIn("senha-segura", bruto)
        self.assertNotIn("segredo-que-nao-pode-sair", bruto)
        conteudo = mensagem.get_content()
        self.assertIn("Nenhuma senha é enviada", conteudo)
        self.assertIn("https://teste.local/?confirmar=", conteudo)
        token = conteudo.split("?confirmar=", 1)[1].split()[0].strip()
        with exigir_fabrica()() as banco:
            registro = banco.scalars(select(ConfirmacaoEmail)).one()
            self.assertNotEqual(registro.token_hash, token)
            self.assertEqual(len(registro.token_hash), 64)
            registro.expira_em = datetime.now(timezone.utc) - timedelta(minutes=1)
            banco.commit()
        expirado = self.cliente.post("/conta/confirmar-email", json={"token": token})
        self.assertEqual(expirado.status_code, 422)
        with patch("app.correio.smtplib.SMTP", return_value=correio):
            reenvio = self.cliente.post("/conta/reenviar-confirmacao", json={"email": "confirma@exemplo.com"})
        self.assertEqual(reenvio.status_code, 200)
        ultimo = correio.mensagens[-1]
        novo = ultimo.get_content().split("?confirmar=", 1)[1].split()[0].strip()
        self.assertNotEqual(novo, token)
        confirmado = self.cliente.post("/conta/confirmar-email", json={"token": novo})
        self.assertEqual(confirmado.status_code, 200)
        repetido = self.cliente.post("/conta/confirmar-email", json={"token": novo})
        self.assertEqual(repetido.status_code, 422)
        with exigir_fabrica()() as banco:
            usuario = banco.scalar(select(Usuario).where(Usuario.email == "confirma@exemplo.com"))
            assert usuario is not None
            self.assertIsNotNone(usuario.email_confirmado_em)
            self.assertEqual(usuario.confirmacao_motivo, "link")
        ausente = self.cliente.post("/conta/reenviar-confirmacao", json={"email": "ausente@exemplo.com"})
        self.assertEqual(ausente.status_code, 200)
        self.assertEqual(ausente.json()["mensagem"], reenvio.json()["mensagem"])

    def test_reenvio_tem_limite(self) -> None:
        for _ in range(5):
            self.assertEqual(self.cliente.post("/conta/reenviar-confirmacao").status_code, 503)
        self.assertEqual(self.cliente.post("/conta/reenviar-confirmacao").status_code, 429)

    def test_cookie_e_origens_de_producao(self) -> None:
        self.assertFalse(cookie_seguro("http"))
        self.assertTrue(cookie_seguro("https"))
        os.environ["COOKIE_SAMESITE"] = "none"
        self.assertEqual(cookie_samesite(False), "lax")
        self.assertEqual(cookie_samesite(True), "none")
        os.environ["COOKIE_SECURE"] = "1"
        self._cadastrar("cookie@exemplo.com")
        cabecalho = self.cliente.post(
            "/conta/entrar",
            json={"email": "cookie@exemplo.com", "senha": "senha-segura"},
        ).headers["set-cookie"].lower()
        self.assertIn("httponly", cabecalho)
        self.assertIn("samesite=none", cabecalho)
        self.assertIn("secure", cabecalho)
        os.environ["ORIGENS_PERMITIDAS"] = "https://publico.example, *, javascript:alert(1), http://localhost:5173/app"
        origens = origens_permitidas()
        self.assertIn("https://publico.example", origens)
        self.assertNotIn("*", origens)
        self.assertTrue(all(not item.startswith("javascript:") for item in origens))
        self.assertNotIn("http://localhost:5173/app", origens)

    def test_politica_nao_publica_dado_de_desenvolvimento(self) -> None:
        corpo = self.cliente.get("/lgpd").json()
        texto = json.dumps(corpo, ensure_ascii=False)
        self.assertIn("CONTROLADOR_PRIVACIDADE", texto)
        self.assertIn("CONTATO_PRIVACIDADE", texto)
        self.assertIsNone(corpo["controlador"])
        self.assertIsNone(corpo["contato"])
        self.assertIn("não registra se a chave", corpo["gemini"]["contrato"])
        self.assertIn("Pendente", corpo["gemini"]["transferencia_internacional"])
        self.assertNotIn("@", texto)
        chave = os.environ.get("GEMINI_API_KEY", "")
        if chave:
            self.assertNotIn(chave, texto)

    def test_preferencias_locais_persistem_e_a_recusa_apaga(self) -> None:
        modulo = Path(__file__).resolve().parents[1] / "frontend" / "src" / "services" / "consentimento.ts"
        script = Path(tempfile.mkdtemp()) / "rodar.mjs"
        script.write_text(
            "const mem = new Map();\n"
            "const sess = new Map();\n"
            "function caixa(mapa) { return { getItem: (k) => (mapa.has(k) ? mapa.get(k) : null), setItem: (k, v) => mapa.set(k, String(v)), removeItem: (k) => mapa.delete(k) }; }\n"
            "globalThis.localStorage = caixa(mem);\n"
            "globalThis.sessionStorage = caixa(sess);\n"
            "globalThis.window = { dispatchEvent() {} };\n"
            f"const m = await import({modulo.as_uri()!r});\n"
            "localStorage.setItem('meu-direito.conversas', 'conversa-teste');\n"
            "localStorage.setItem('meu-ia.tema', 'escuro');\n"
            "m.gravarEscolha({ preferencias: true, historicoVisitante: true });\n"
            "if (!m.permitirPreferencias() || !m.permitirHistoricoVisitante()) process.exit(1);\n"
            "const guardada = m.lerEscolha();\n"
            "if (!guardada || guardada.preferencias !== true || guardada.historicoVisitante !== true) process.exit(2);\n"
            "m.gravarEscolha({ preferencias: false, historicoVisitante: false });\n"
            "if (m.permitirPreferencias() || m.permitirHistoricoVisitante()) process.exit(3);\n"
            "if (localStorage.getItem('meu-direito.conversas') !== null) process.exit(4);\n"
            "if (localStorage.getItem('meu-ia.tema') !== null) process.exit(5);\n"
            "const escolha = m.lerEscolha();\n"
            "if (!escolha || escolha.preferencias !== false || escolha.historicoVisitante !== false) process.exit(6);\n",
            encoding="utf-8",
        )
        resultado = subprocess.run(
            ["node", "--experimental-strip-types", str(script)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr or resultado.stdout)
