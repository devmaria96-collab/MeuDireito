"""Sinais de alteração e revogação lidos só no texto recuperado."""

import unittest

from app.consulta_legislacao import encerrar_coleta, iniciar_coleta, sinais_normativos


class SinaisNormativosTeste(unittest.TestCase):
    def test_revogacao_nao_vira_vigencia(self) -> None:
        situacao, tipo, notas = sinais_normativos(
            "Art. 1º (Revogado pela Lei nº 9.999, de 2000).",
            "https://www.planalto.gov.br/ccivil_03/leis/l1234.htm",
        )
        self.assertEqual(situacao, "dispositivo_revogado")
        self.assertEqual(tipo, "pagina_oficial")
        self.assertTrue(notas)
        self.assertTrue(notas[0].startswith("caput — revogação:"))
        self.assertIn("Revogado pela Lei nº 9.999", notas[0])

    def test_compilado_e_alteracao(self) -> None:
        situacao, tipo, notas = sinais_normativos(
            "Art. 6 Redacao dada pela Lei n 14.181, de 2021.",
            "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        )
        self.assertEqual(situacao, "dispositivo_alterado")
        self.assertEqual(tipo, "compilado")
        self.assertTrue(any(nota.startswith("caput — alteração:") and "Redacao dada pela Lei" in nota for nota in notas))

    def test_constituicao_e_compilada_sem_nota(self) -> None:
        situacao, tipo, notas = sinais_normativos(
            "Art. 5 Todos sao iguais perante a lei.",
            "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
        )
        self.assertEqual(situacao, "texto_recuperado")
        self.assertEqual(tipo, "compilado")
        self.assertEqual(notas, ())

    def test_nota_de_inciso_nao_vale_para_o_artigo(self) -> None:
        situacao, tipo, notas = sinais_normativos(
            "Art. 5º Todos são iguais perante a lei.\n"
            "LXXVIII - a todos são assegurados a razoável duração do processo. "
            "(Incluído pela Emenda Constitucional nº 45, de 2004)",
            "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
        )
        self.assertEqual(situacao, "texto_recuperado")
        self.assertEqual(tipo, "compilado")
        self.assertEqual(len(notas), 1)
        self.assertTrue(notas[0].startswith("inciso LXXVIII — inclusão:"))
        self.assertIn("Emenda Constitucional nº 45", notas[0])

    def test_paragrafo_revogado_nao_revoga_o_artigo(self) -> None:
        situacao, _, notas = sinais_normativos(
            "Art. 10 O contrato é escrito.\n"
            "§ 2º (Revogado pela Lei nº 9.999, de 2000.)\n"
            "§ 3º O prazo é de trinta dias.",
            "https://www.planalto.gov.br/ccivil_03/leis/l1234.htm",
        )
        self.assertEqual(situacao, "texto_recuperado")
        self.assertTrue(notas[0].startswith("parágrafo 2 — revogação:"))

    def test_norma_revogada_so_no_preambulo(self) -> None:
        situacao, _, notas = sinais_normativos(
            "Art. 2º O texto permanece.",
            "https://www.planalto.gov.br/ccivil_03/leis/l1234.htm",
            "Ementa. Revogada pela Lei nº 1.234, de 2010.",
        )
        self.assertEqual(situacao, "norma_revogada")
        self.assertTrue(notas[0].startswith("norma — revogação:"))

    def test_revoga_outra_lei_nao_revoga_esta(self) -> None:
        situacao, _, notas = sinais_normativos(
            "Art. 5 O direito não fica revogado por esta cláusula.",
            "https://www.planalto.gov.br/ccivil_03/leis/l1234.htm",
            "Revoga a Lei nº 1.234, de 1990.",
        )
        self.assertEqual(situacao, "texto_recuperado")
        self.assertEqual(notas, ())

    def test_coleta_so_existe_durante_a_resposta(self) -> None:
        from app.consulta_legislacao import consultar

        token = iniciar_coleta()
        resultado = consultar("")
        self.assertFalse(resultado.verificada)
        self.assertFalse(resultado.vigencia_confirmada)
        coletados = encerrar_coleta(token)
        self.assertEqual(len(coletados), 1)
        self.assertIn("VERIFICACAO: nao", coletados[0].como_texto())
        self.assertNotIn("https://", coletados[0].como_texto())


if __name__ == "__main__":
    unittest.main()
