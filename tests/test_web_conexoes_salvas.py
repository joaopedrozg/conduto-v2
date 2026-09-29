"""Conexões salvas da Web UI (store local + endpoints)."""

from fastapi.testclient import TestClient

from conduto.web import conexoes_salvas as salvas
from conduto.web.app import criar_app


def test_salvar_listar_upsert_remover(monkeypatch, tmp_path):
    monkeypatch.setenv("CONDUTO_CONEXOES", str(tmp_path / "conexoes.json"))
    base = {"tipo": "postgresql", "host": "h", "port": "5432", "user": "u",
            "password": "s", "database": "d", "schema": "public"}
    um = salvas.salvar("casa", base)
    assert um["id"] and um["apelido"] == "casa"
    # Apelido repetido atualiza em vez de duplicar.
    dois = salvas.salvar("casa", {**base, "host": "outro"})
    assert dois["id"] == um["id"]
    assert salvas.listar()[0]["credenciais"]["host"] == "outro"
    # Sem apelido gera `tipo@host/database`.
    auto = salvas.salvar("", base)
    assert auto["apelido"] == "postgresql@h/d"
    assert salvas.remover(um["id"]) is True
    assert salvas.remover("inexistente") is False


def test_endpoints_salvas(monkeypatch, tmp_path):
    monkeypatch.setenv("CONDUTO_CONEXOES", str(tmp_path / "conexoes.json"))
    client = TestClient(criar_app())
    corpo = {"apelido": "x", "credenciais": {"tipo": "postgresql", "host": "h"}}
    criado = client.post("/api/conexoes/salvas", json=corpo)
    assert criado.status_code == 200
    lista = client.get("/api/conexoes/salvas")
    assert [c["apelido"] for c in lista.json()["conexoes"]] == ["x"]
    ruim = client.post("/api/conexoes/salvas", json={
        "apelido": "y", "credenciais": {"tipo": "oracle", "host": "h"},
    })
    assert ruim.status_code == 400
    apagado = client.delete(f"/api/conexoes/salvas/{criado.json()['id']}")
    assert apagado.json() == {"ok": True}
    assert client.delete("/api/conexoes/salvas/inexistente").status_code == 404
