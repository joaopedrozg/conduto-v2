"""Guarda das conexões: .env, SQLite ou YAML.

O `.env` é o contrato de runtime (o código gerado, o DDL e o inferir
leem dele); o painel pode persistir a mesma informação em SQLite ou
YAML e reler de qualquer backend depois (detecção: sqlite > yml > env).
"""

import pytest

from conduto.conexoes_store import (
    ARQUIVO_SQLITE,
    ARQUIVO_YML,
    BACKENDS,
    carregar_conexoes,
    detectar_backend,
    salvar_conexoes,
)


def _origem(**kw):
    base = dict(tipo="postgresql", host="localhost", port="5432", user="postgres",
                password="pw", database="postgres", schema="public")
    base.update(kw)
    return base


def _destino(**kw):
    base = dict(tipo="duckdb", host="dest.duckdb", port="", user="",
                password="", database="dest.duckdb", schema="main")
    base.update(kw)
    return base


def test_backends_conhecidos():
    assert BACKENDS == ("env", "sqlite", "yml")


def test_yml_round_trip(tmp_path):
    origem, destino = _origem(), _destino()
    caminho = salvar_conexoes(tmp_path, origem, destino, backend="yml")
    assert caminho == tmp_path / ARQUIVO_YML
    assert caminho.exists()
    assert carregar_conexoes(tmp_path, backend="yml") == (origem, destino)


def test_sqlite_round_trip(tmp_path):
    origem, destino = _origem(), _destino()
    caminho = salvar_conexoes(tmp_path, origem, destino, backend="sqlite")
    assert caminho == tmp_path / ARQUIVO_SQLITE
    assert carregar_conexoes(tmp_path, backend="sqlite") == (origem, destino)


def test_sqlite_salvar_duas_vezes_troca(tmp_path):
    salvar_conexoes(tmp_path, _origem(), _destino(), backend="sqlite")
    outra = _origem(host="db02")
    salvar_conexoes(tmp_path, outra, _destino(), backend="sqlite")
    lida, _ = carregar_conexoes(tmp_path, backend="sqlite")
    assert lida["host"] == "db02"


def test_env_round_trip_usa_o_formato_do_projeto(tmp_path):
    (tmp_path / "main.yml").write_text('project: demo\n', encoding="utf-8")
    origem, destino = _origem(), _destino()
    caminho = salvar_conexoes(tmp_path, origem, destino, backend="env")
    assert caminho == tmp_path / ".env"
    lida_o, lida_d = carregar_conexoes(tmp_path, backend="env")
    assert (lida_o["tipo"], lida_o["host"], lida_o["database"]) == ("postgresql", "localhost", "postgres")
    assert (lida_d["tipo"], lida_d["database"]) == ("duckdb", "dest.duckdb")


def test_backend_desconhecido_levanta(tmp_path):
    with pytest.raises(ValueError, match="[Bb]ackend"):
        salvar_conexoes(tmp_path, _origem(), _destino(), backend="oracle")


def test_carregar_sem_arquivo_falha_como_o_env(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_conexoes(tmp_path, backend="sqlite")
    with pytest.raises(FileNotFoundError):
        carregar_conexoes(tmp_path, backend="yml")


def test_carregar_tipo_desconhecido_falha(tmp_path):
    salvar_conexoes(tmp_path, _origem(tipo="oracle"), _destino(), backend="yml")
    with pytest.raises(ValueError, match="oracle"):
        carregar_conexoes(tmp_path, backend="yml")


def test_carregar_yml_quebrado_falha(tmp_path):
    (tmp_path / ARQUIVO_YML).write_text("origem: [ok\n", encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_conexoes(tmp_path, backend="yml")


def test_detectar_prefere_sqlite_yml_env(tmp_path):
    assert detectar_backend(tmp_path) == "env"
    (tmp_path / ".env").write_text("DB_ORIGEM_TYPE=postgresql\n", encoding="utf-8")
    assert detectar_backend(tmp_path) == "env"
    salvar_conexoes(tmp_path, _origem(), _destino(), backend="yml")
    assert detectar_backend(tmp_path) == "yml"
    salvar_conexoes(tmp_path, _origem(), _destino(), backend="sqlite")
    assert detectar_backend(tmp_path) == "sqlite"


def test_carregar_sem_backend_detecta_sozinho(tmp_path):
    salvar_conexoes(tmp_path, _origem(), _destino(), backend="sqlite")
    origem, _ = carregar_conexoes(tmp_path)
    assert origem["host"] == "localhost"
