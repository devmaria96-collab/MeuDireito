"""Histórico autenticado: cada conta vê só as próprias conversas."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.banco import exigir_fabrica, preparar_banco, redefinir_banco
from app.consulta_legislacao import ResultadoConsulta
from app.limite import zerar
from app.main import app
from app.modelos import ConversaRegistro, Perfil, Usuario


def _consulta() -> ResultadoConsulta:
    return ResultadoConsulta(
        verificada=True,
        norma="Constituição da República Federativa do Brasil",
        numero=None,
        ano="1988",
        artigo="5º",
        texto_oficial="Art. 5º Todos são iguais perante a lei.",
        url="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
        consultado_em="2026-11-18",
        aviso="Texto lido no Portal do Planalto.",
        situacao="texto_obtido",
        tipo_texto="constituicao",
        notas_fonte=("Caput lido na página oficial.",),
    )


class HistoricoContaTeste(unittest.TestCase):
    def setUp(self) -> None:
        zerar()
        self._anterior = os.environ.get("DATABASE_URL")
        pasta = tempfile.mkdtemp()
        self.arquivo = Path(pasta) / "historico.db"
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

    def _cadastrar(self, cliente: TestClient, email: str, nome: str) -> str:
        resposta = cliente.post(
            "/conta/cadastrar",
            json={"email": email, "senha": "senha-segura", "confirmar_senha": "senha-segura", "nome": nome},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return str(resposta.json()["csrf"])

    def _entrar(self, cliente: TestClient, email: str) -> str:
        resposta = cliente.post("/conta/entrar", json={"email": email, "senha": "senha-segura"})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return str(resposta.json()["csrf"])

    def test_visitante_pesquisa_e_nao_abre_historico(self) -> None:
        with patch("app.main.responder", new=AsyncMock(return_value=("Texto de teste.", []))):
            resposta = self.cliente.post("/conversar", json={"pergunta": "O que diz o artigo 5º?"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["resposta"], "Texto de teste.")
        bloqueada = self.cliente.get("/conta/conversas")
        self.assertEqual(bloqueada.status_code, 401)

    def test_criar_continuar_renomear_excluir_e_persistir(self) -> None:
        csrf = self._cadastrar(self.cliente, "ana@exemplo.com", "Ana")
        agente = AsyncMock(return_value=("Resposta isolada.", [_consulta()]))
        with patch("app.rotas_historico.responder", new=agente):
            with self.assertLogs("meu_direito", level="INFO") as registros:
                criada = self.cliente.post(
                    "/conta/conversas/perguntar",
                    json={"pergunta": "primeira pergunta isolada", "perfil": "estudante"},
                    headers={"X-CSRF-Token": csrf},
                )
        self.assertEqual(criada.status_code, 200, criada.text)
        conversa = criada.json()["conversa"]
        self.assertEqual(conversa["mensagens"][0]["conteudo"], "primeira pergunta isolada")
        self.assertEqual(conversa["mensagens"][1]["conteudo"], "Resposta isolada.")
        self.assertTrue(conversa["mensagens"][1]["referencias"][0]["verificada"])
        self.assertEqual(conversa["mensagens"][1]["referencias"][0]["artigo"], "5º")
        self.assertNotIn("primeira pergunta isolada", " ".join(registros.output))
        self.assertEqual(agente.await_args.args[0], "primeira pergunta isolada")

        with patch("app.rotas_historico.responder", new=agente):
            seguida = self.cliente.post(
                "/conta/conversas/perguntar",
                json={"pergunta": "segunda pergunta isolada", "conversa_id": conversa["id"]},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(seguida.status_code, 200, seguida.text)
        self.assertEqual(seguida.json()["conversa"]["id"], conversa["id"])
        self.assertEqual(len(seguida.json()["conversa"]["mensagens"]), 4)
        self.assertEqual(agente.await_args.args[0], "segunda pergunta isolada")
        self.assertNotIn("primeira", agente.await_args.args[0])

        renomeada = self.cliente.patch(
            f"/conta/conversas/{conversa['id']}",
            json={"titulo": "Habeas corpus"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(renomeada.status_code, 200)
        lista = self.cliente.get("/conta/conversas")
        self.assertEqual(lista.json()["conversas"][0]["titulo"], "Habeas corpus")
        self.assertNotIn("mensagens", lista.json()["conversas"][0])

        redefinir_banco()
        preparar_banco()
        with TestClient(app) as outro:
            token = self._entrar(outro, "ana@exemplo.com")
            detalhe = outro.get(f"/conta/conversas/{conversa['id']}")
            self.assertEqual(detalhe.status_code, 200)
            self.assertEqual(detalhe.json()["conversa"]["mensagens"][1]["referencias"][0]["artigo"], "5º")
            apagada = outro.delete(f"/conta/conversas/{conversa['id']}", headers={"X-CSRF-Token": token})
            self.assertEqual(apagada.status_code, 204)
            self.assertEqual(outro.get(f"/conta/conversas/{conversa['id']}").status_code, 404)

    def test_falha_do_modelo_preserva_a_pergunta(self) -> None:
        csrf = self._cadastrar(self.cliente, "falha@exemplo.com", "Falha")
        with patch("app.rotas_historico.responder", new=AsyncMock(side_effect=RuntimeError("segredo-da-pergunta-nao-logar"))):
            with self.assertLogs("meu_direito", level="WARNING") as registros:
                resposta = self.cliente.post(
                    "/conta/conversas/perguntar",
                    json={"pergunta": "pergunta que nao pode sumir"},
                    headers={"X-CSRF-Token": csrf},
                )
        self.assertEqual(resposta.status_code, 500)
        detalhe = resposta.json()["detail"]
        self.assertNotIn("segredo-da-pergunta-nao-logar", detalhe["mensagem"])
        self.assertEqual(detalhe["conversa"]["mensagens"][0]["conteudo"], "pergunta que nao pode sumir")
        self.assertNotIn("pergunta que nao pode sumir", " ".join(registros.output))
        self.assertNotIn("segredo-da-pergunta-nao-logar", " ".join(registros.output))

        with patch("app.rotas_historico.responder", new=AsyncMock(return_value=("Resposta depois da falha.", []))):
            nova = self.cliente.post(
                "/conta/conversas/perguntar",
                json={"pergunta": "pergunta que nao pode sumir", "conversa_id": detalhe["conversa"]["id"]},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(nova.status_code, 200, nova.text)
        papeis = [item["papel"] for item in nova.json()["conversa"]["mensagens"]]
        self.assertEqual(papeis, ["usuario", "agente"])

    def test_importacao_nao_duplica_e_isolamento(self) -> None:
        ana = TestClient(app)
        bruno = TestClient(app)
        ana.__enter__()
        bruno.__enter__()
        try:
            csrf_ana = self._cadastrar(ana, "ana-iso@exemplo.com", "Ana")
            csrf_bruno = self._cadastrar(bruno, "bruno-iso@exemplo.com", "Bruno")
            pacote = {
                "conversas": [
                    {
                        "id": "conversa-local-1",
                        "titulo": "Artigo 5",
                        "mensagens": [
                            {"papel": "usuario", "conteudo": "O que diz o artigo 5º?"},
                            {
                                "papel": "agente",
                                "conteudo": "É uma cláusula geral.",
                                "referencias": [
                                    {
                                        "id": "ref-local",
                                        "verificada": True,
                                        "artigo": "5º",
                                        "aviso": "Texto lido no Planalto.",
                                        "url": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
                                    }
                                ],
                            },
                        ],
                    }
                ]
            }
            primeira = ana.post("/conta/conversas/importar", json=pacote, headers={"X-CSRF-Token": csrf_ana})
            segunda = ana.post("/conta/conversas/importar", json=pacote, headers={"X-CSRF-Token": csrf_ana})
            self.assertEqual(primeira.status_code, 200, primeira.text)
            self.assertEqual(primeira.json()["importadas"], 1)
            self.assertNotIn("apagar", primeira.text)
            self.assertEqual(segunda.json()["importadas"], 0)
            self.assertEqual(segunda.json()["ignoradas"], 1)
            lista = ana.get("/conta/conversas")
            self.assertEqual(len(lista.json()["conversas"]), 1)
            detalhe = ana.get(f"/conta/conversas/{lista.json()['conversas'][0]['id']}")
            self.assertEqual(detalhe.json()["conversa"]["mensagens"][1]["referencias"][0]["artigo"], "5º")

            do_bruno = bruno.post("/conta/conversas/importar", json=pacote, headers={"X-CSRF-Token": csrf_bruno})
            self.assertEqual(do_bruno.json()["importadas"], 1)
            id_ana = lista.json()["conversas"][0]["id"]
            self.assertEqual(bruno.get(f"/conta/conversas/{id_ana}").status_code, 404)
            self.assertEqual(bruno.patch(f"/conta/conversas/{id_ana}", json={"titulo": "Invasão"}, headers={"X-CSRF-Token": csrf_bruno}).status_code, 404)
            self.assertEqual(bruno.delete(f"/conta/conversas/{id_ana}", headers={"X-CSRF-Token": csrf_bruno}).status_code, 404)
            self.assertEqual(ana.get(f"/conta/conversas/{id_ana}").status_code, 200)
            self.assertEqual(bruno.get("/conta/conversas").json()["conversas"][0]["titulo"], "Artigo 5")

            banco = exigir_fabrica()()
            try:
                total = banco.scalar(select(func.count()).select_from(ConversaRegistro))
                consentimentos = banco.scalars(select(Perfil.consentimento_sincronizacao).join(Usuario)).all()
            finally:
                banco.close()
            self.assertEqual(total, 2)
            self.assertEqual(consentimentos, [True, True])
        finally:
            ana.__exit__(None, None, None)
            bruno.__exit__(None, None, None)

    def test_apagar_tudo_nao_atinge_outra_conta(self) -> None:
        ana = TestClient(app)
        bruno = TestClient(app)
        ana.__enter__()
        bruno.__enter__()
        try:
            csrf_ana = self._cadastrar(ana, "ana-del@exemplo.com", "Ana")
            csrf_bruno = self._cadastrar(bruno, "bruno-del@exemplo.com", "Bruno")
            with patch("app.rotas_historico.responder", new=AsyncMock(return_value=("Uma.", []))):
                ana.post("/conta/conversas/perguntar", json={"pergunta": "Pergunta da Ana"}, headers={"X-CSRF-Token": csrf_ana})
                bruno.post("/conta/conversas/perguntar", json={"pergunta": "Pergunta do Bruno"}, headers={"X-CSRF-Token": csrf_bruno})
            apagou = ana.delete("/conta/conversas", headers={"X-CSRF-Token": csrf_ana})
            self.assertEqual(apagou.status_code, 204)
            self.assertEqual(ana.get("/conta/conversas").json()["conversas"], [])
            self.assertEqual(len(bruno.get("/conta/conversas").json()["conversas"]), 1)
        finally:
            ana.__exit__(None, None, None)
            bruno.__exit__(None, None, None)

    def test_dois_clientes_da_mesma_conta(self) -> None:
        csrf = self._cadastrar(self.cliente, "dois@exemplo.com", "Dois")
        with patch("app.rotas_historico.responder", new=AsyncMock(return_value=("Resposta compartilhada.", []))):
            criada = self.cliente.post(
                "/conta/conversas/perguntar",
                json={"pergunta": "Pergunta no primeiro aparelho"},
                headers={"X-CSRF-Token": csrf},
            )
        with TestClient(app) as outro:
            self._entrar(outro, "dois@exemplo.com")
            lista = outro.get("/conta/conversas")
            self.assertEqual(lista.json()["conversas"][0]["id"], criada.json()["conversa"]["id"])
            detalhe = outro.get(f"/conta/conversas/{criada.json()['conversa']['id']}")
            self.assertEqual(detalhe.json()["conversa"]["mensagens"][0]["conteudo"], "Pergunta no primeiro aparelho")


if __name__ == "__main__":
    unittest.main()
