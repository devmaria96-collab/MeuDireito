"""Conta opcional: a pesquisa continua aberta e o perfil de outra pessoa permanece intacto."""

import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.banco import preparar_banco, redefinir_banco
from app.limite import zerar
from app.main import app


class ContaOpcionalTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = os.environ.get("DATABASE_URL")
        pasta = tempfile.mkdtemp()
        self.arquivo = Path(pasta) / "contas.db"
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
        zerar()

    def test_visitante_pesquisa_sem_conta(self) -> None:
        sessao = self.cliente.get("/conta/sessao")
        self.assertEqual(sessao.status_code, 200)
        self.assertFalse(sessao.json()["autenticado"])
        fontes = self.cliente.get("/fontes-oficiais")
        self.assertEqual(fontes.status_code, 200)
        self.assertIn("/conversar", app.openapi()["paths"])

    def test_cadastro_login_senha_errada_e_saida(self) -> None:
        criado = self._cadastrar("ana@exemplo.com", "senha-segura", "Ana")
        self.assertEqual(criado.status_code, 200)
        corpo = criado.json()
        self.assertEqual(corpo["usuario"]["nome_exibicao"], "Ana")
        self.assertNotIn("@", corpo["usuario"]["nome_exibicao"])
        self.cliente.post("/conta/sair", headers={"X-CSRF-Token": corpo["csrf"]})
        errada = self.cliente.post("/conta/entrar", json={"email": "ana@exemplo.com", "senha": "errada-demais"})
        self.assertEqual(errada.status_code, 401)
        certa = self.cliente.post("/conta/entrar", json={"email": "ana@exemplo.com", "senha": "senha-segura"})
        self.assertEqual(certa.status_code, 200)
        self.cliente.post("/conta/sair", headers={"X-CSRF-Token": certa.json()["csrf"]})
        depois = self.cliente.get("/conta/sessao")
        self.assertFalse(depois.json()["autenticado"])

    def test_nome_vazio_nao_usa_o_email(self) -> None:
        criado = self._cadastrar("pessoa@exemplo.com", "senha-segura", None)
        self.assertEqual(criado.status_code, 200)
        nome = criado.json()["usuario"]["nome_exibicao"]
        self.assertTrue(nome.startswith("Usuário"))
        self.assertNotIn("pessoa@exemplo.com", nome)

    def test_perfil_avatar_imagem_e_isolamento(self) -> None:
        ana = self._cadastrar("ana2@exemplo.com", "senha-segura", "Ana")
        csrf = ana.json()["csrf"]
        perfil = self.cliente.patch(
            "/conta/perfil",
            json={"nome": "Ana Souza", "avatar_codigo": "livro", "perfil_juridico": "estudante"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(perfil.status_code, 200)
        self.assertEqual(perfil.json()["usuario"]["nome_exibicao"], "Ana Souza")
        self.assertEqual(perfil.json()["usuario"]["avatar_codigo"], "livro")
        imagem = BytesIO()
        Image.new("RGB", (32, 24), (225, 6, 0)).save(imagem, format="PNG")
        envio = self.cliente.post(
            "/conta/avatar",
            files={"arquivo": ("foto.png", imagem.getvalue(), "image/png")},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(envio.status_code, 200)
        self.assertEqual(envio.json()["usuario"]["tipo_avatar"], "imagem")
        foto = self.cliente.get("/conta/avatar")
        self.assertEqual(foto.status_code, 200)
        self.assertEqual(foto.headers["content-type"], "image/webp")
        self.assertNotIn(b"PNG", foto.content[:16])
        troca = self.cliente.patch("/conta/perfil", json={"avatar_codigo": "martelo"}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(troca.json()["usuario"]["tipo_avatar"], "biblioteca")
        self.assertEqual(troca.json()["usuario"]["avatar_codigo"], "martelo")
        self.assertEqual(self.cliente.get("/conta/avatar").status_code, 404)
        self.cliente.post("/conta/sair", headers={"X-CSRF-Token": troca.json()["csrf"]})

        bruno = self._cadastrar("bruno@exemplo.com", "senha-segura", "Bruno")
        self.cliente.patch("/conta/perfil", json={"nome": "Bruno Lima"}, headers={"X-CSRF-Token": bruno.json()["csrf"]})
        self.assertNotEqual(self.cliente.get("/conta/sessao").json()["usuario"]["nome_exibicao"], "Ana Souza")
        self.assertEqual(self.cliente.get("/conta/avatar").status_code, 404)

    def test_upload_executavel_e_recusado(self) -> None:
        criado = self._cadastrar("foto@exemplo.com", "senha-segura", "Foto")
        recusado = self.cliente.post(
            "/conta/avatar",
            files={"arquivo": ("virus.png", b"MZ" + b"\x00" * 32, "image/png")},
            headers={"X-CSRF-Token": criado.json()["csrf"]},
        )
        self.assertEqual(recusado.status_code, 422)

    def test_recuperacao_nao_simula_email(self) -> None:
        resposta = self.cliente.post("/conta/recuperar-senha")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("pendente", resposta.json()["detail"])
        self.assertNotIn("enviado", resposta.json()["detail"].lower())

    def test_perfil_permanece_apos_reabrir_o_banco(self) -> None:
        self._cadastrar("persistente@exemplo.com", "senha-segura", "Persistente")
        redefinir_banco()
        preparar_banco()
        with TestClient(app) as outro:
            entrada = outro.post("/conta/entrar", json={"email": "persistente@exemplo.com", "senha": "senha-segura"})
        self.assertEqual(entrada.status_code, 200)
        self.assertEqual(entrada.json()["usuario"]["nome_exibicao"], "Persistente")

    def _cadastrar(self, email: str, senha: str, nome: str | None):
        return self.cliente.post(
            "/conta/cadastrar",
            json={"email": email, "senha": senha, "confirmar_senha": senha, "nome": nome},
        )


if __name__ == "__main__":
    unittest.main()
