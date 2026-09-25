"""Motor não-interativo do init (o que o painel executa no final).

Sem Textual e sem prompts: parâmetros explícitos, progresso via `relatar`
e erros como exceção (o painel exibe; o wizard legado segue intacto).
"""

from pathlib import Path

import pytest
import yaml

from conduto import init_exec
from conduto.init_exec import ParametrosInit, executar_init


def _credenciais(tipo="postgresql", database="postgres", schema="public"):
    return {
        "tipo": tipo,
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "postgres",
        "database": database,
        "schema": schema,
    }


def _params(tmp_path, **kw):
    base = dict(
        project_dir=tmp_path / "demo",
        nome_projeto="demo",
        origem=_credenciais(),
        destino=_credenciais(tipo="duckdb", database="dest.duckdb", schema="main"),
        gerar_automatico=False,
        gerar_schedules=True,
        aplicar_ddl=False,
    )
    base.update(kw)
    return ParametrosInit(**base)


@pytest.fixture
def _sem_uv(monkeypatch):
    """setup do ambiente uv e comando dagster: fora do teste de execução."""
    chamadas = []
    monkeypatch.setattr(
        init_exec, "setup_uv_environment", lambda *a, **k: chamadas.append("uv")
    )
    monkeypatch.setattr(
        init_exec, "gerar_comando_dagster", lambda *a, **k: chamadas.append("dagster")
    )
    return chamadas


def test_modo_manual_gera_env_schemas_main_e_schedules(tmp_path, _sem_uv):
    log = []
    resultado = executar_init(_params(tmp_path), relatar=log.append)

    projeto = tmp_path / "demo"
    assert (projeto / ".env").exists()
    assert (projeto / "main.yml").exists()
    assert list((projeto / "schemas").glob("*.yml"))
    dados = yaml.safe_load((projeto / "main.yml").read_text(encoding="utf-8"))
    assert dados["project"] == "demo"
    assert resultado.schedules is True
    assert resultado.ddl_aplicado is False
    assert _sem_uv == ["uv", "dagster"]
    assert log  # o painel mostra o progresso


def test_modo_manual_sem_schedules_pula_etapa(tmp_path, _sem_uv):
    resultado = executar_init(_params(tmp_path, gerar_schedules=False))
    assert resultado.schedules is False


def test_armazenamento_sqlite_grava_copia_sem_tirar_o_env(tmp_path, _sem_uv):
    from conduto.conexoes_store import carregar_conexoes

    resultado = executar_init(_params(tmp_path, armazenamento="sqlite"))
    projeto = tmp_path / "demo"
    assert (projeto / ".env").exists()  # runtime continua no .env
    assert (projeto / "conexoes.db").exists()
    origem, destino = carregar_conexoes(projeto, backend="sqlite")
    assert origem["host"] == "localhost"
    assert destino["tipo"] == "duckdb"
    assert resultado.env_path is not None


def test_armazenamento_yml_grava_copia(tmp_path, _sem_uv):
    executar_init(_params(tmp_path, armazenamento="yml"))
    assert (tmp_path / "demo" / "conexoes.yml").exists()
    assert not (tmp_path / "demo" / "conexoes.db").exists()


def test_modo_auto_usa_selecao_sem_perguntar(tmp_path, _sem_uv, monkeypatch):
    import conduto.schemas.schemas_auto as auto

    monkeypatch.setattr(
        auto, "listar_tabelas", lambda *a: [{"schema": "public", "table": "clientes"}]
    )
    monkeypatch.setattr(auto, "abrir_conexao", lambda *a, **k: None)
    monkeypatch.setattr(
        auto,
        "descrever_tabela",
        lambda *a, **k: {
            "table": "clientes",
            "schema": "public",
            "columns": [{"name": "id", "type": "integer", "nullable": False}],
        },
    )
    params = _params(
        tmp_path,
        gerar_automatico=True,
        tabelas=[{"schema": "public", "table": "clientes"}],
    )
    resultado = executar_init(params)

    projeto = tmp_path / "demo"
    assert (projeto / "schemas" / "clientes.yml").exists()
    assert resultado.schemas_gerados == 1


def test_modo_auto_sem_tabelas_validas_cai_para_exemplo(tmp_path, _sem_uv, monkeypatch):
    import conduto.schemas.schemas_auto as auto

    monkeypatch.setattr(auto, "listar_tabelas", lambda *a: [])
    resultado = executar_init(_params(tmp_path, gerar_automatico=True))

    projeto = tmp_path / "demo"
    assert list((projeto / "schemas").glob("*.yml"))
    assert resultado.schemas_gerados == 0


def test_aplicar_ddl_executa_no_destino(tmp_path, _sem_uv, monkeypatch):
    import conduto.schemas.schemas_auto as auto

    monkeypatch.setattr(
        auto, "listar_tabelas", lambda *a: [{"schema": "public", "table": "clientes"}]
    )
    monkeypatch.setattr(auto, "abrir_conexao", lambda *a, **k: None)
    monkeypatch.setattr(
        auto,
        "descrever_tabela",
        lambda *a, **k: {
            "table": "clientes",
            "schema": "public",
            "columns": [{"name": "id", "type": "integer", "nullable": False}],
        },
    )
    aplicadas = []
    monkeypatch.setattr(init_exec, "executar_ddl", lambda *a: aplicadas.append(a) or [])
    params = _params(
        tmp_path,
        gerar_automatico=True,
        tabelas=[{"schema": "public", "table": "clientes"}],
        aplicar_ddl=True,
    )
    resultado = executar_init(params)

    assert resultado.ddl_aplicado is True
    assert resultado.ddl_comandos >= 1
    assert aplicadas


def test_erro_no_ddl_vira_runtimeerror(tmp_path, _sem_uv, monkeypatch):
    monkeypatch.setattr(
        init_exec, "executar_ddl", lambda *a: [RuntimeError("boom")]
    )
    params = _params(tmp_path, aplicar_ddl=True)
    with pytest.raises(RuntimeError, match="boom"):
        executar_init(params)


def test_tipo_desconhecido_falha_cedo(tmp_path):
    params = _params(tmp_path, origem=_credenciais(tipo="oracle"))
    with pytest.raises((ValueError, RuntimeError)):
        executar_init(params)


def test_helpers_de_escolha_para_o_painel(monkeypatch):
    """O painel lista tabelas e monta choices sem prompt."""
    import conduto.schemas.schemas_auto as auto

    monkeypatch.setattr(
        auto, "listar_tabelas", lambda *a: [{"schema": "public", "table": "clientes"}]
    )
    tabelas = auto.listar_tabelas_origem(None, {})
    assert tabelas == [{"schema": "public", "table": "clientes"}]
    escolhas = auto.escolhas_de_tabelas(tabelas, Path("/inexistente"))
    assert [c.title for c in escolhas] == ["public.clientes"]
    assert escolhas[0].value == {"schema": "public", "table": "clientes"}
