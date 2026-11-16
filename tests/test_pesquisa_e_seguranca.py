"""Pesquisa com vários artigos, avaliação e proteções que não dependem de rede."""

import json
import unittest
from pathlib import Path

from app.agente import pesquisa_aprofundada
from app.consulta_legislacao import dividir_consultas
from app.feedback import registrar_feedback
from app.limite import consumir, zerar
from app.main import _texto_sem_credenciais


class PesquisaAprofundadaTeste(unittest.TestCase):
    def test_pergunta_simples_nao_dispara_comparacao(self) -> None:
        self.assertFalse(pesquisa_aprofundada("O que é habeas corpus?"))

    def test_dois_artigos_disparam_comparacao(self) -> None:
        self.assertTrue(pesquisa_aprofundada("Compare o artigo 5 da Constituição com o artigo 6 do CDC."))

    def test_conflito_dispara_comparacao(self) -> None:
        self.assertTrue(pesquisa_aprofundada("Há conflito entre essas normas?"))

    def test_divide_dois_artigos_da_mesma_norma(self) -> None:
        partes = dividir_consultas("artigos 5 e 6 da Constituição Federal")
        self.assertEqual(partes, ["artigo 5 da Constituição Federal", "artigo 6 da Constituição Federal"])

    def test_divide_normas_diferentes(self) -> None:
        partes = dividir_consultas("artigo 5 da constituição com o artigo 6 do CDC")
        self.assertEqual(len(partes), 2)
        self.assertIn("artigo 5", partes[0])
        self.assertIn("artigo 6", partes[1])

    def test_consulta_unica_permanece_inteira(self) -> None:
        self.assertEqual(dividir_consultas("artigo 6 do CDC"), ["artigo 6 do CDC"])


class AvaliacaoTeste(unittest.TestCase):
    def test_positiva_nao_guarda_motivo_nem_conversa(self) -> None:
        destino = Path(__file__).with_name("_feedback_teste.jsonl")
        if destino.exists():
            destino.unlink()
        registro = registrar_feedback("positiva", "incorreta", destino)
        self.assertEqual(registro["avaliacao"], "positiva")
        self.assertIsNone(registro["motivo"])
        gravado = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(set(gravado), {"id", "em", "avaliacao", "motivo"})
        self.assertNotIn("pergunta", gravado)
        self.assertNotIn("resposta", gravado)
        destino.unlink()

    def test_negativa_guarda_so_o_motivo(self) -> None:
        destino = Path(__file__).with_name("_feedback_teste.jsonl")
        registro = registrar_feedback("negativa", "desatualizada", destino)
        self.assertEqual(registro["motivo"], "desatualizada")
        destino.unlink()

    def test_motivo_livre_e_descartado(self) -> None:
        destino = Path(__file__).with_name("_feedback_teste.jsonl")
        registro = registrar_feedback("negativa", "meu CPF é 000.000.000-00", destino)
        self.assertIsNone(registro["motivo"])
        destino.unlink()


class SegurancaTeste(unittest.TestCase):
    def tearDown(self) -> None:
        zerar()

    def test_limite_de_requisicoes(self) -> None:
        self.assertTrue(consumir("teste", limite=2, janela=60, agora=100))
        self.assertTrue(consumir("teste", limite=2, janela=60, agora=101))
        self.assertFalse(consumir("teste", limite=2, janela=60, agora=102))

    def test_chave_nao_volta_na_mensagem(self) -> None:
        texto = _texto_sem_credenciais(RuntimeError("falha AQ.abcdefghij123 no provedor"))
        self.assertNotIn("AQ.", texto)
        self.assertNotIn("abcdefghij123", texto)

    def test_frontend_nao_carrega_chave(self) -> None:
        raiz = Path(__file__).parents[1] / "frontend" / "src"
        for arquivo in raiz.rglob("*"):
            if arquivo.suffix not in {".ts", ".tsx", ".css", ".html"}:
                continue
            conteudo = arquivo.read_text(encoding="utf-8")
            self.assertNotIn("GEMINI_API_KEY=", conteudo)
            self.assertNotRegex(conteudo, r"AIza[0-9A-Za-z\-_]{8,}")
            self.assertNotRegex(conteudo, r"AQ\.[A-Za-z0-9_\-.]{8,}")


if __name__ == "__main__":
    unittest.main()
