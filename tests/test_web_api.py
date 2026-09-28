"""Web UI: a TUI segue intacta; aqui cobrimos só o backend FastAPI."""

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
    assert resposta.json()["pastas"] == ["sub"]

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
    assert status.json()["rodando"] is False
