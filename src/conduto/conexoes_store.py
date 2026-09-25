"""Guarda das conexões de origem/destino: .env, SQLite ou YAML.

O `.env` é o contrato de runtime — o código gerado, o DDL e o inferir
leem dele — e por isso a criação sempre o escreve. O painel pode pedir
cópia em SQLite (`conexoes.db`) ou YAML (`conexoes.yml`) e reler de
qualquer backend depois (detecção automática: sqlite > yml > env).

Senhas vão em claro nos três formatos, como já vão no `.env` hoje.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Tuple

__all__ = [
    "ARQUIVO_SQLITE",
    "ARQUIVO_YML",
    "BACKENDS",
    "carregar_conexoes",
    "detectar_backend",
    "salvar_conexoes",
]

#: Backends na ordem de preferência da detecção automática.
BACKENDS = ("env", "sqlite", "yml")

ARQUIVO_SQLITE = "conexoes.db"
ARQUIVO_YML = "conexoes.yml"

_CHAVES = ("tipo", "host", "port", "user", "password", "database", "schema")


def _exigir_backend(backend: str) -> str:
    if backend not in BACKENDS:
        raise ValueError(
            f"Backend de conexões desconhecido: {backend!r} (use: {', '.join(BACKENDS)})"
        )
    return backend


def _nome_projeto(project_dir: Path) -> str:
    """Nome do main.yml (ou da pasta) para renderizar o .env."""
    main = Path(project_dir) / "main.yml"
    if main.exists():
        try:
            import yaml

            dados = yaml.safe_load(main.read_text(encoding="utf-8")) or {}
            if dados.get("project"):
                return str(dados["project"])
        except Exception:
            pass
    return Path(project_dir).name


def _validar_tipo(lado: Dict[str, str], rotulo: str) -> None:
    from conduto.database.adapters import ADAPTERS

    tipo = lado.get("tipo")
    if not any(a.tipo == tipo for a in ADAPTERS.values()):
        raise ValueError(f"Tipo de SGBD de {rotulo} não suportado: {tipo!r}")


def _limpar(lado: Dict[str, str]) -> Dict[str, str]:
    """Só as chaves de conexão (nada de resto do formulário)."""
    return {chave: lado.get(chave, "") for chave in _CHAVES}


def salvar_conexoes(
    project_dir: Path,
    origem: Dict[str, str],
    destino: Dict[str, str],
    backend: str = "env",
) -> Path:
    """Guarda (origem, destino) no backend e devolve o arquivo escrito."""
    _exigir_backend(backend)
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    origem, destino = _limpar(dict(origem)), _limpar(dict(destino))
    if backend == "env":
        from conduto.env.env_render import env_render

        env_render(
            {"project_name": _nome_projeto(project_dir), "origem": origem, "destino": destino},
            output_dir=project_dir,
        )
        return project_dir / ".env"
    if backend == "yml":
        import yaml

        caminho = project_dir / ARQUIVO_YML
        caminho.write_text(
            yaml.safe_dump({"origem": origem, "destino": destino}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return caminho
    caminho = project_dir / ARQUIVO_SQLITE
    conexao = sqlite3.connect(caminho)
    try:
        conexao.execute(
            "CREATE TABLE IF NOT EXISTS conexoes (papel TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        for papel, lado in (("origem", origem), ("destino", destino)):
            conexao.execute(
                "INSERT OR REPLACE INTO conexoes (papel, payload) VALUES (?, ?)",
                (papel, json.dumps(lado, ensure_ascii=False)),
            )
        conexao.commit()
    finally:
        conexao.close()
    return caminho


def detectar_backend(project_dir: Path) -> str:
    """Backend a ler: o primeiro existente (sqlite > yml > env)."""
    project_dir = Path(project_dir)
    if (project_dir / ARQUIVO_SQLITE).exists():
        return "sqlite"
    if (project_dir / ARQUIVO_YML).exists():
        return "yml"
    return "env"


def carregar_conexoes(
    project_dir: Path, backend: str | None = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Devolve (origem, destino) do backend (None = detecta sozinho).

    Sem arquivo levanta FileNotFoundError; tipo desconhecido ou YAML
    quebrado levantam ValueError — como ``ler_conexoes_env``.
    """
    project_dir = Path(project_dir)
    backend = detectar_backend(project_dir) if backend is None else _exigir_backend(backend)
    if backend == "env":
        from conduto.ddl.ddl_render import ler_env

        env = ler_env(project_dir)  # FileNotFoundError sem .env, como antes

        def _lado(prefixo: str, rotulo: str) -> Dict[str, str]:
            from conduto.database.adapters import ADAPTERS
            from conduto.database.admin import schema_padrao_sgbd

            tipo = env.get(f"{prefixo}_TYPE")
            adapter = next((a for a in ADAPTERS.values() if a.tipo == tipo), None)
            if adapter is None:
                raise ValueError(f"Tipo de SGBD de {rotulo} não suportado no .env: {tipo!r}")
            credenciais = {
                "tipo": tipo,
                "host": env.get(f"{prefixo}_HOST", adapter.host_padrao),
                "port": env.get(f"{prefixo}_PORT", adapter.porta_padrao),
                "database": env.get(f"{prefixo}_NAME", adapter.banco_padrao),
                "user": env.get(f"{prefixo}_USER", adapter.usuario_padrao),
                "password": env.get(f"{prefixo}_PASSWORD", adapter.senha_padrao),
            }
            credenciais["schema"] = env.get(f"{prefixo}_SCHEMA") or schema_padrao_sgbd(
                adapter, credenciais
            )
            return credenciais

        return _lado("DB_ORIGEM", "origem"), _lado("DB_DESTINO", "destino")
    if backend == "yml":
        import yaml

        caminho = project_dir / ARQUIVO_YML
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo {ARQUIVO_YML} não encontrado em: {project_dir}")
        try:
            dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
            origem, destino = _limpar(dados["origem"]), _limpar(dados["destino"])
        except (KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
            raise ValueError(f"Arquivo {ARQUIVO_YML} inválido em: {project_dir} ({exc})") from exc
        _validar_tipo(origem, "origem")
        _validar_tipo(destino, "destino")
        return origem, destino
    caminho = project_dir / ARQUIVO_SQLITE
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo {ARQUIVO_SQLITE} não encontrado em: {project_dir}")
    conexao = sqlite3.connect(caminho)
    try:
        linhas = {
            papel: json.loads(payload)
            for papel, payload in conexao.execute("SELECT papel, payload FROM conexoes")
        }
    except Exception as exc:
        raise ValueError(f"Arquivo {ARQUIVO_SQLITE} inválido em: {project_dir} ({exc})") from exc
    finally:
        conexao.close()
    try:
        origem, destino = _limpar(linhas["origem"]), _limpar(linhas["destino"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"Arquivo {ARQUIVO_SQLITE} inválido em: {project_dir} ({exc})") from exc
    _validar_tipo(origem, "origem")
    _validar_tipo(destino, "destino")
    return origem, destino
