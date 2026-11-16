"""Ferramentas que o agente pode utilizar.

Novas ferramentas devem ser decoradas com ``function_tool`` e incluídas
na lista ``FERRAMENTAS``, consumida em ``app.agente``.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from agents import function_tool

from app.consulta_legislacao import consultar, dividir_consultas
from app.legislacao import descrever_fontes_oficiais


@function_tool
def obter_data_hora() -> str:
    """Retorna a data e a hora atuais no fuso horário de Brasília."""
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    return agora.strftime("%d/%m/%Y %H:%M:%S")


@function_tool
def listar_fontes_oficiais() -> str:
    """Lista portais oficiais. Não lê o conteúdo deles nem confirma artigo ou decisão."""
    return descrever_fontes_oficiais()


@function_tool
def consultar_legislacao(consulta: str) -> str:
    """Lê um ou mais artigos de lei federal no Portal da Legislação do Planalto.

    Use antes de explicar uma lei ou um artigo específico. Em comparação ou
    conflito, chame uma vez para cada artigo, no máximo quatro, por exemplo
    "artigo 5 da Constituição Federal" e "artigo 6 do Código de Defesa do Consumidor".
    Cada nota de alteração ou revogação vale só para o dispositivo nomeado.
    Se a resposta disser VERIFICACAO: nao, nenhum texto foi confirmado.
    Tribunais não são consultados por esta ferramenta.
    """
    partes = dividir_consultas(consulta)[:4]
    blocos = [consultar(parte).como_texto() for parte in partes]
    return "\n\n----\n\n".join(blocos)


FERRAMENTAS = [obter_data_hora, listar_fontes_oficiais, consultar_legislacao]
