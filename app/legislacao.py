"""Catálogo de fontes oficiais do Direito brasileiro.

Este módulo não consulta a internet. Ele apenas identifica portais oficiais
para uma integração futura. Nenhuma resposta daqui confirma texto legal vigente.
"""

from typing import TypedDict


class FonteOficial(TypedDict):
    nome: str
    url: str
    descricao: str


FONTES_OFICIAIS: list[FonteOficial] = [
    {
        "nome": "Portal da Legislação do Planalto",
        "url": "https://www.planalto.gov.br/legislacao",
        "descricao": "Publicação oficial de normas federais.",
    },
    {
        "nome": "Supremo Tribunal Federal",
        "url": "https://portal.stf.jus.br/",
        "descricao": "Portal oficial do STF.",
    },
    {
        "nome": "Superior Tribunal de Justiça",
        "url": "https://www.stj.jus.br/",
        "descricao": "Portal oficial do STJ.",
    },
    {
        "nome": "Conselho Nacional de Justiça",
        "url": "https://www.cnj.jus.br/",
        "descricao": "Portal oficial do CNJ.",
    },
]

AVISO_SEM_CONSULTA = (
    "Nenhuma fonte oficial foi consultada agora. "
    "Artigos, súmulas, números de processos e decisões não foram confirmados."
)


def descrever_fontes_oficiais() -> str:
    """Descreve os portais conhecidos e deixa explícita a ausência de consulta."""
    linhas = [
        "Verificação em tempo real: não realizada.",
        AVISO_SEM_CONSULTA,
        "Portais oficiais que a pessoa pode consultar por conta própria:",
    ]
    for fonte in FONTES_OFICIAIS:
        linhas.append(f"- {fonte['nome']}: {fonte['url']} ({fonte['descricao']})")
    linhas.append(
        "Tribunais estaduais, regionais e superiores também possuem portais oficiais próprios. "
        "Eles não são consultados por este sistema."
    )
    return "\n".join(linhas)
