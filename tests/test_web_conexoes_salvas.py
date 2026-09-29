"""Conexões salvas da Web UI (store no projeto + endpoints)."""

from fastapi.testclient import TestClient

from conduto.web import conexoes_salvas as salvas
from conduto.web.app import criar_app


def test_salvar_listar_upsert_remover(tmp_path):
    base = {"tipo": "postgresql", "host": "h", "port": "5432", "user": "u",
            "password": "s", "database": "d", "schema": "public"}
    um = salvas.salvar("casa", base, tmp_path)
    assert um["id"] and um["apelido"] == "casa"
    assert (tmp_path / "conexoes.json").exists()
    # Apelido repetido atualiza em vez de duplicar.
    dois = salvas.salvar("casa", {**base, "host": "outro"}, tmp_path)
    assert dois["id"] == um["id"]
    assert salvas.listar(tmp_path)[0]["credenciais"]["host"] == "outro"
    # Sem apelido gera `tipo@host/database`.
    auto = salvas.salvar("", base, tmp_path)
    assert auto["apelido"] == "postgresql@h/d"
    # Outro projeto não enxerga.
    assert salvas.listar(tmp_path / "outro") == []
    assert salvas.remover(um["id"], tmp_path) is True
    assert salvas.remover("inexistente", tmp_path) is False


def test_endpoints_salvas(tmp_path):
    client = TestClient(criar_app())
    corpo = {"apelido": "x", "credenciais": {"tipo": "postgresql", "host": "h"},
             "project_dir": str(tmp_path)}
    criado = client.post("/api/conexoes/salvas", json=corpo)
    assert criado.status_code == 200
    lista = client.get("/api/conexoes/salvas", params={"project_dir": str(tmp_path)})
    assert [c["apelido"] for c in lista.json()["conexoes"]] == ["x"]
    ruim = client.post("/api/conexoes/salvas", json={
        "apelido": "y", "credenciais": {"tipo": "oracle", "host": "h"},
        "project_dir": str(tmp_path),
    })
    assert ruim.status_code == 400
    apagado = client.delete(
        f"/api/conexoes/salvas/{criado.json()['id']}", params={"project_dir": str(tmp_path)}
    )
    assert apagado.json() == {"ok": True}
    assert client.delete(
        "/api/conexoes/salvas/inexistente", params={"project_dir": str(tmp_path)}
    ).status_code == 404
