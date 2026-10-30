"""Lê o arquivo .env da raiz do projeto e coloca os valores nas variáveis de ambiente.

Não sobrescreve variáveis que já existem e ignora linhas vazias ou sem valor.
O .env está no .gitignore: nunca vai para o GitHub.
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def carregar_env() -> None:
    if not ENV_PATH.exists():
        return
    for linha in ENV_PATH.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(chave.strip(), valor)
