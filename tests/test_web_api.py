"""Web UI: a TUI segue intacta; aqui cobrimos só o backend FastAPI."""

import pytest
from fastapi.testclient import TestClient

from conduto.web.app import criar_app


def test_saude_e_sgbds():
    client = TestClient(criar_app())
    saude = client.get("/api/saude")
    assert saude.status_code == 200
    assert saude.json()["ok"] is True

    sgbds = client.get("/api/sgbds")
    assert sgbds.status_code == 200
    tipos = {s["tipo"] for s in sgbds.json()}
    assert {"postgresql", "mysql", "sqlserver", "clickhouse", "duckdb", "deltalake"} <= tipos


def test_tipo_desconhecido_da_400():
    client = TestClient(criar_app())
    resposta = client.post(
        "/api/conexoes/testar",
        json={"credenciais": {"tipo": "oracle", "host": "x"}},
    )
    assert resposta.status_code == 400


def test_resumo_projeto_vazio(tmp_path):
    client = TestClient(criar_app())
    resposta = client.get("/api/projeto/resumo", params={"project_dir": str(tmp_path)})
    assert resposta.status_code == 200
    assert resposta.json()["tem_main"] is False


def test_drivers_faltantes_e_odbc():
    client = TestClient(criar_app())
    resposta = client.get("/api/drivers/faltantes", params={"tipo": "sqlserver"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["tipo"] == "sqlserver"
    assert "faltantes" in corpo and "requisicoes" in corpo

    desconhecido = client.get("/api/drivers/faltantes", params={"tipo": "oracle"})
    assert desconhecido.status_code == 400

    odbc = client.get("/api/drivers/sqlserver-odbc")
    assert odbc.status_code == 200
    assert "ok" in odbc.json() and "instalados" in odbc.json()


def test_pastas_lista_tmp(tmp_path):
    (tmp_path / "sub").mkdir()
    client = TestClient(criar_app())
    resposta = client.get("/api/sistema/pastas", params={"caminho": str(tmp_path)})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["pastas"] == ["sub"]
    assert corpo["casa"] and corpo["servidor_cwd"]

    inexistente = client.get("/api/sistema/pastas", params={"caminho": str(tmp_path / "nada")})
    assert inexistente.status_code == 400


def test_cron_invalido_rejeitado(tmp_path):
    (tmp_path / "main.yml").write_text("version: '1.0'\nproject: x\ntables: []\n", encoding="utf-8")
    (tmp_path / "schemas").mkdir()
    client = TestClient(criar_app())
    resposta = client.post(
        "/api/projeto/schedules", json={"project_dir": str(tmp_path), "cron": "invalido"}
    )
    assert resposta.status_code == 400


def test_schedules_com_cron_preset(tmp_path):
    (tmp_path / "main.yml").write_text("version: '1.0'\nproject: x\ntables: []\n", encoding="utf-8")
    (tmp_path / "schemas").mkdir()
    client = TestClient(criar_app())
    resposta = client.post(
        "/api/projeto/schedules", json={"project_dir": str(tmp_path), "cron": "diario"}
    )
    assert resposta.status_code == 200
    assert resposta.json()["cron_aplicado"] == "0 0 * * *"


def test_dagster_status_parado(tmp_path):
    client = TestClient(criar_app())
    resposta = client.get("/api/projeto/resumo", params={"project_dir": str(tmp_path)})
    assert resposta.status_code == 200
    status = client.get("/api/servidores/dagster", params={"project_dir": str(tmp_path)})
    assert status.status_code == 200
    corpo = status.json()
    # Sem processo gerenciado: externo reflete se há algo na porta 3000
    # (o ambiente pode ter um Dagster de verdade rodando).
    assert corpo["rodando"] is False
    assert corpo["externo"] == corpo["responde"]
    assert corpo["url"] == "http://localhost:3000"


def test_catalogo_tabelas_filtra_schemas(monkeypatch):
    import conduto.schemas.schemas_auto as auto

    monkeypatch.setattr(
        auto,
        "listar_tabelas_origem",
        lambda adapter, cred: [
            {"schema": "dbo", "table": "a"},
            {"schema": "rh", "table": "b"},
        ],
    )
    client = TestClient(criar_app())
    corpo = {"credenciais": {"tipo": "sqlserver", "host": "h"}}
    todas = client.post("/api/catalogo/tabelas", json=corpo)
    assert todas.status_code == 200
    assert len(todas.json()["tabelas"]) == 2
    filtradas = client.post("/api/catalogo/tabelas", json={**corpo, "schemas": ["rh"]})
    assert filtradas.status_code == 200
    assert filtradas.json()["tabelas"] == [{"schema": "rh", "table": "b"}]


def test_diretorio_frontend_compilado_ou_ausente():
    from conduto.web.app import diretorio_frontend

    onde = diretorio_frontend()
    # Com build: pasta com index.html; sem build (CI limpo): None.
    assert onde is None or (onde / "index.html").exists()


def test_spa_fallback_e_api_convivem():
    from conduto.web.app import diretorio_frontend

    if diretorio_frontend() is None:
        pytest.skip("sem build Angular")
    from fastapi.testclient import TestClient

    from conduto.web.app import criar_app

    client = TestClient(criar_app())
    criar = client.get("/criar", params={"nome": "x"})
    assert criar.status_code == 200
    assert "conduto-root" in criar.text
    assert client.get("/api/saude").status_code == 200
    assert client.get("/api/rota_inexistente").status_code == 404
