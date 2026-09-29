"""Conexões salvas da Web UI, guardadas no PROJETO (`conexoes.json`).

É atalho de preenchimento do wizard: mora junto do projeto (viaja com
ele), não em cache da máquina nem no browser. Inclui a senha, como o
`.env` do projeto já faz — não versione o arquivo.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List

__all__ = ["arquivo", "listar", "remover", "salvar"]

NOME_ARQUIVO = "conexoes.json"

_CHAVES = ("tipo", "host", "port", "user", "password", "database", "schema")


def arquivo(project_dir: str | Path = ".") -> Path:
    """Caminho do JSON dentro do projeto."""
    return Path(project_dir or ".") / NOME_ARQUIVO


def _carregar(project_dir: str | Path) -> List[Dict]:
    try:
        dados = json.loads(arquivo(project_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return dados if isinstance(dados, list) else []


def _gravar(project_dir: str | Path, itens: List[Dict]) -> None:
    caminho = arquivo(project_dir)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")


def listar(project_dir: str | Path = ".") -> List[Dict]:
    """Todas as salvas do projeto (ordem alfabética de apelido)."""
    return sorted(_carregar(project_dir), key=lambda item: str(item.get("apelido", "")).lower())


def salvar(apelido: str, credenciais: Dict[str, str], project_dir: str | Path = ".") -> Dict:
    """Cria ou atualiza pelo apelido (vazio = `tipo@host/database`)."""
    apelido = (apelido or "").strip()
    limpas = {chave: credenciais.get(chave, "") for chave in _CHAVES}
    if not apelido:
        apelido = "{tipo}@{host}/{database}".format(
            tipo=limpas.get("tipo"), host=limpas.get("host"), database=limpas.get("database")
        )
    itens = _carregar(project_dir)
    for item in itens:
        if item.get("apelido") == apelido:
            item["credenciais"] = limpas
            _gravar(project_dir, itens)
            return item
    item = {"id": uuid.uuid4().hex[:12], "apelido": apelido, "credenciais": limpas}
    itens.append(item)
    _gravar(project_dir, itens)
    return item


def remover(identificador: str, project_dir: str | Path = ".") -> bool:
    """Remove pelo id. True se existia."""
    itens = _carregar(project_dir)
    restantes = [item for item in itens if item.get("id") != identificador]
    if len(restantes) == len(itens):
        return False
    _gravar(project_dir, restantes)
    return True
