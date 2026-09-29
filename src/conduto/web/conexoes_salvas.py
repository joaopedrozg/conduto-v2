"""Conexões salvas da Web UI (atalhos de preenchimento, por máquina).

Guarda em ``~/.conduto/conexoes.json`` — ``CONDUTO_CONEXOES`` sobrescreve o
caminho (mesmo padrão de ``CONDUTO_REGISTROS`` do shell da TUI). Inclui a
senha: é um atalho local e o backend escuta em localhost por padrão.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List

__all__ = ["arquivo", "listar", "remover", "salvar"]

_CHAVES = ("tipo", "host", "port", "user", "password", "database", "schema")


def arquivo() -> Path:
    """Caminho do JSON (env primeiro, como nos registros da TUI)."""
    alvo = os.environ.get("CONDUTO_CONEXOES")
    if alvo:
        return Path(alvo)
    return Path.home() / ".conduto" / "conexoes.json"


def _carregar() -> List[Dict]:
    try:
        dados = json.loads(arquivo().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return dados if isinstance(dados, list) else []


def _gravar(itens: List[Dict]) -> None:
    caminho = arquivo()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")


def listar() -> List[Dict]:
    """Todas as salvas (ordem alfabética de apelido)."""
    return sorted(_carregar(), key=lambda item: str(item.get("apelido", "")).lower())


def salvar(apelido: str, credenciais: Dict[str, str]) -> Dict:
    """Cria ou atualiza pelo apelido (vazio = `tipo@host/database`)."""
    apelido = (apelido or "").strip()
    limpas = {chave: credenciais.get(chave, "") for chave in _CHAVES}
    if not apelido:
        apelido = "{tipo}@{host}/{database}".format(
            tipo=limpas.get("tipo"), host=limpas.get("host"), database=limpas.get("database")
        )
    itens = _carregar()
    for item in itens:
        if item.get("apelido") == apelido:
            item["credenciais"] = limpas
            _gravar(itens)
            return item
    item = {"id": uuid.uuid4().hex[:12], "apelido": apelido, "credenciais": limpas}
    itens.append(item)
    _gravar(itens)
    return item


def remover(identificador: str) -> bool:
    """Remove pelo id. True se existia."""
    itens = _carregar()
    restantes = [item for item in itens if item.get("id") != identificador]
    if len(restantes) == len(itens):
        return False
    _gravar(restantes)
    return True
