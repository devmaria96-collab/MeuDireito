"""Testes da minuta sem chamar o Gemini e sem dados pessoais."""

import unittest
import zipfile
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.minutas import (
    exportar_docx,
    exportar_pdf,
    html_para_blocos,
    markdown_para_html,
    neutralizar_invencoes,
    preparar_minuta,
    texto_visivel,
    validar_campos,
)
from app.minutas import ErroFormulario


HTML_EXEMPLO = (
    "<h2>Objeto</h2>"
    '<p style="text-align: center"><strong>Parte A</strong> e Parte B.</p>'
    "<ul><li>Obrigação de entregar um relatório fictício.</li></ul>"
    "<script>alert(1)</script>"
    '<p onclick="roubar()">Texto visível.</p>'
)


class TesteMinuta(unittest.TestCase):
    def test_markdown_escapa_script(self) -> None:
        html = markdown_para_html("Texto <script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<p>", html)

    def test_html_remove_script_e_preserva_texto(self) -> None:
        blocos = html_para_blocos(HTML_EXEMPLO)
        texto = " ".join(trecho.texto for bloco in blocos for trecho in bloco.trechos)
        self.assertIn("Parte A", texto)
        self.assertIn("Texto visível.", texto)
        self.assertNotIn("alert", texto)
        self.assertNotIn("roubar", texto)
        centro = next(bloco for bloco in blocos if bloco.alinhamento == "center")
        self.assertTrue(centro.trechos[0].negrito)

    def test_nao_inventa_valor_nem_artigo(self) -> None:
        campos = {
            "tipo_contrato": "Prestação de serviços",
            "partes": "Parte A e Parte B",
            "objeto": "Consultoria fictícia",
            "obrigacoes": "",
            "valores": "R$ 1.000,00",
            "prazos": "",
            "rescisao": "",
        }
        saida = (
            "# Contrato de teste\n\n"
            "Parte A e Parte B.\n\n"
            "O valor é R$ 9.999,00, com base no artigo 999 do Código Civil.\n"
            "Documento autenticado digitalmente.\n"
            "________________\n"
        )
        pronta = preparar_minuta("contrato", saida, campos, set())
        visivel = " ".join(html_para_blocos(pronta.html)[0].trechos[0].texto for _ in [0])
        texto = ""
        for bloco in html_para_blocos(pronta.html):
            texto += " " + "".join(trecho.texto for trecho in bloco.trechos)
        self.assertIn("Parte A", texto)
        self.assertIn("R$ 1.000,00", neutralizar_invencoes("R$ 1.000,00", campos, set()))
        self.assertNotIn("9.999", texto)
        self.assertNotIn("artigo 999", texto.lower())
        self.assertNotIn("autenticado", texto.lower())
        self.assertIn("[INFORMAÇÃO PENDENTE]", texto)
        preenchido = preparar_minuta(
            "declaracao",
            "Eu, Declarante A, portador(a) dos dados cadastrados no sistema, declaro o teste.",
            {"declarante": "Declarante A", "teor": "declaro o teste", "finalidade": ""},
            set(),
        )
        self.assertNotIn("cadastrados", texto_visivel(preenchido.html).lower())
        peticao = preparar_minuta(
            "peticao_inicial",
            "# Petição de Facer\n\n[NOME DO AUTOR], já qualificado nos autos. Fatos: [não informado].",
            {
                "area": "Direito civil",
                "tipo_acao": "ação de obrigação de fazer",
                "partes": "[NOME DO AUTOR]",
                "fatos": "",
                "pedidos": "pedido de teste",
                "documentos": "",
                "fundamentos": "",
            },
            set(),
        )
        visivel_peticao = texto_visivel(peticao.html)
        self.assertNotIn("Facer", peticao.titulo)
        self.assertIn("Fazer", peticao.titulo)
        self.assertNotIn("Facer", visivel_peticao)
        self.assertNotIn("qualificado nos autos", visivel_peticao.lower())
        self.assertNotIn("[não informado]", visivel_peticao)
        self.assertIn("[INFORMAÇÃO PENDENTE]", visivel_peticao)
        self.assertNotIn("<script>", pronta.html)
        self.assertTrue(any("Obrigações" in item for item in pronta.pendencias))
        self.assertNotIn("visivel", visivel)

    def test_formulario_rejeita_campo_desconhecido_e_vazio(self) -> None:
        with self.assertRaises(ErroFormulario):
            validar_campos("contrato", {})
        with self.assertRaises(ErroFormulario):
            validar_campos("contrato", {"partes": "Parte A", "cpf": "000.000.000-00"})
        with self.assertRaises(ErroFormulario):
            validar_campos("declaracao", {"teor": "a" * 4001})

    def test_exporta_docx_e_pdf(self) -> None:
        docx = exportar_docx("Minuta de teste", HTML_EXEMPLO)
        self.assertTrue(docx.startswith(b"PK"))
        with zipfile.ZipFile(BytesIO(docx)) as arquivo:
            xml = arquivo.read("word/document.xml").decode("utf-8")
            nucleo = arquivo.read("docProps/core.xml").decode("utf-8")
        self.assertIn("Parte A", xml)
        self.assertIn("Obrigação", xml)
        self.assertIn("Objeto", xml)
        self.assertNotIn("alert", xml)
        self.assertNotIn("onclick", xml)
        self.assertNotIn("<script", xml)
        self.assertIn('w:val="center"', xml)
        self.assertNotIn("Maria", nucleo)
        pdf = exportar_pdf("Minuta de teste", HTML_EXEMPLO)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)
        self.assertNotIn(b"<script", pdf)


class TesteApiDocumentos(unittest.TestCase):
    def setUp(self) -> None:
        self.cliente = TestClient(app)

    def test_geracao_recusa_formulario_vazio(self) -> None:
        resposta = self.cliente.post("/documentos/gerar", json={"tipo": "contrato", "campos": {}})
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("pelo menos um campo", resposta.json()["detail"])

    def test_exportacao_pelos_endpoints(self) -> None:
        pdf = self.cliente.post(
            "/documentos/exportar",
            json={"formato": "pdf", "titulo": "Minuta de teste", "html": HTML_EXEMPLO},
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        word = self.cliente.post(
            "/documentos/exportar",
            json={"formato": "docx", "titulo": "Minuta de teste", "html": HTML_EXEMPLO},
        )
        self.assertEqual(word.status_code, 200)
        self.assertIn("wordprocessingml", word.headers["content-type"])
        self.assertTrue(word.content.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
