"""Gera minutas de teste com dados fictícios e confere exportação e chat.

Não usa nome, CPF ou endereço reais.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "http://127.0.0.1:8000"

CASOS = {
    "contrato": {
        "tipo_contrato": "Prestação de serviços de consultoria",
        "partes": "Parte A (contratante) e Parte B (contratada)",
        "objeto": "Consultoria fictícia de organização de documentos",
        "obrigacoes": "Parte B entrega um relatório. Parte A paga o valor informado.",
        "valores": "R$ 1.000,00",
        "prazos": "30 dias",
        "rescisao": "Qualquer parte pode encerrar com aviso de 10 dias.",
    },
    "notificacao": {
        "notificante": "Notificante A",
        "notificado": "Notificado B",
        "fatos": "O Notificado B não entregou o relatório fictício combinado.",
        "solicitacao": "Entrega do relatório",
        "prazo_resposta": "5 dias",
    },
    "declaracao": {
        "declarante": "Declarante A",
        "teor": "Declara, para fins de teste, que participou de uma reunião fictícia.",
        "finalidade": "Comprovação em teste interno",
    },
    "peticao_inicial": {
        "area": "Direito civil",
        "tipo_acao": "ação de obrigação de fazer",
        "partes": "[NOME DO AUTOR] e [NOME DO RÉU]",
        "fatos": "",
        "pedidos": "condenar a parte ré a cumprir a obrigação descrita nos fatos",
        "documentos": "",
        "fundamentos": "artigo 15 da Lei 999999/2099",
    },
}


def post(caminho: str, corpo: dict[str, object], timeout: int = 180) -> tuple[int, str, bytes]:
    pedido = urllib.request.Request(
        BASE + caminho,
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return resposta.status, resposta.headers.get("Content-Type", ""), resposta.read()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.headers.get("Content-Type", ""), erro.read()


def texto_de(html: str) -> str:
    from app.minutas import texto_visivel

    return texto_visivel(html)


def main() -> None:
    minutas: dict[str, dict[str, object]] = {}
    for tipo, campos in CASOS.items():
        status, _, bruto = post("/documentos/gerar", {"tipo": tipo, "campos": campos, "perfil": "cidadao"})
        print(f"\n== {tipo} HTTP {status} ==", flush=True)
        if status != 200:
            print(bruto.decode("utf-8", "replace")[:500])
            continue
        dados = json.loads(bruto)
        minutas[tipo] = dados
        visivel = texto_de(dados["html"])
        print("titulo:", dados["titulo"])
        print("pendencias:", len(dados["pendencias"]))
        print(visivel[:2500])

    peticao = str(texto_de(str(minutas.get("peticao_inicial", {}).get("html", ""))))
    proibidos = ["João", "Maria", "Silva", "000.000.000-00", "R$"]
    print("\n== conferência da petição incompleta ==")
    print("marcador:", "[INFORMAÇÃO PENDENTE]" in peticao)
    print("area:", "civil" in peticao.lower())
    print("lei_informada:", "999999" in peticao or "15" in peticao)
    for termo in proibidos:
        print(f"contem_{termo}:", termo in peticao)

    if "contrato" in minutas:
        html = str(minutas["contrato"]["html"]) + "<p>Trecho incluído na edição manual de teste.</p>"
        status, tipo_midia, arquivo = post(
            "/documentos/exportar",
            {"formato": "docx", "titulo": "Contrato de teste", "html": html},
        )
        xml = ""
        if arquivo.startswith(b"PK"):
            with zipfile.ZipFile(BytesIO(arquivo)) as pacote:
                xml = pacote.read("word/document.xml").decode("utf-8")
        print("\n== edição e Word ==")
        print(status, tipo_midia, "edicao:", "Trecho incluído na edição manual de teste." in xml)
        print("parte:", "Parte A" in xml, "script:", "<script" in xml)
        status_pdf, tipo_pdf, pdf = post(
            "/documentos/exportar",
            {"formato": "pdf", "titulo": "Contrato de teste", "html": html},
        )
        print("== PDF ==")
        print(status_pdf, tipo_pdf, pdf.startswith(b"%PDF"), len(pdf))

    status, _, bruto = post("/conversar", {"pergunta": "Responda apenas com a palavra pronto.", "perfil": "cidadao"})
    print("\n== chat ==")
    print(status, bruto.decode("utf-8", "replace")[:200])


if __name__ == "__main__":
    main()
