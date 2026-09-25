"""Setup uv do projeto: falha mostra o porquê, não só o exit code.

Regressão de um erro real no painel: `uv add dagster-webserver`
falhou com exit 2, mas a saída do uv ia para o silenciador do painel e
o `CalledProcessError` mostrava só o comando — impossível diagnosticar.
Agora o erro carrega o stderr junto.
"""

import subprocess
import types

import pytest

from conduto.i18n import definir_idioma
from conduto.project_base import gerar_project


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _resultado(codigo, stdout="", stderr="", args=()):
    return types.SimpleNamespace(returncode=codigo, stdout=stdout, stderr=stderr, args=args)


def _sem_uv(monkeypatch, saidas):
    """Troca o subprocess do setup: saídas por etapa (init/add)."""
    chamadas = []

    def _run(comando, **kwargs):
        chamadas.append(comando)
        etapa = comando[1] if len(comando) > 1 else ""
        return saidas.get(etapa, _resultado(0, args=comando))

    monkeypatch.setattr(subprocess, "run", _run)
    return chamadas


def test_falha_no_uv_add_mostra_stderr_e_codigo(tmp_path, monkeypatch):
    _sem_uv(monkeypatch, {
        "add": _resultado(2, stderr="error: No solution found when resolving dependencies"),
    })
    with pytest.raises(RuntimeError) as exc:
        gerar_project.setup_uv_environment(tmp_path, drivers=[])
    mensagem = str(exc.value)
    assert "2" in mensagem
    assert "No solution found" in mensagem


def test_falha_no_uv_init_mostra_stderr(tmp_path, monkeypatch):
    _sem_uv(monkeypatch, {
        "init": _resultado(1, stderr="error: permission denied"),
    })
    with pytest.raises(RuntimeError) as exc:
        gerar_project.setup_uv_environment(tmp_path, drivers=[])
    assert "permission denied" in str(exc.value)


def test_uv_add_ok_nao_levanta_e_pula_init_com_pyproject(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    chamadas = _sem_uv(monkeypatch, {
        "add": _resultado(0, stdout="Installed dagster-webserver"),
    })
    gerar_project.setup_uv_environment(tmp_path, drivers=[])
    assert [c[1] for c in chamadas] == ["add"]


def test_sem_pendentes_nem_chama_uv(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["pyyaml", "jinja2", "dagster", "dagster-webserver"]\n',
        encoding="utf-8",
    )
    chamadas = _sem_uv(monkeypatch, {})
    gerar_project.setup_uv_environment(tmp_path, drivers=[])
    assert chamadas == []
