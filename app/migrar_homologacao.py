"""Migra só um PostgreSQL de homologação já conferido.

Não usa o banco local de desenvolvimento. Não imprime usuário, senha nem chave.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def carregar_ambiente() -> None:
    from dotenv import dotenv_values

    valores = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    for nome, valor in valores.items():
        if nome and valor and nome not in os.environ:
            os.environ[nome] = valor


def main() -> int:
    carregar_ambiente()
    from app.banco import url_do_banco
    from app.homologacao import ambiente, descrever_destino, migracao_de_postgres_permitida, url_normalizada

    url = url_do_banco()
    if not url:
        print("Recusado: DATABASE_URL vazia. Nada foi migrado.")
        return 2
    normal = url_normalizada(url)
    print(descrever_destino(normal).resumo())
    if ambiente() != "homologacao":
        print("Recusado: AMBIENTE não é homologacao. Nada foi migrado.")
        return 2
    permitida, motivo = migracao_de_postgres_permitida(normal)
    if not permitida:
        print(motivo)
        return 2
    from alembic import command
    from alembic.config import Config

    configuracao = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    configuracao.set_main_option("sqlalchemy.url", normal)
    command.upgrade(configuracao, "head")
    print("Migração de homologação aplicada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
