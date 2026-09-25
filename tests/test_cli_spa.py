"""CLI da SPA: help só mostra o init; init despacha criar/administrar.

Os demais comandos seguem registrados (scripts/CI usam sem TTY), mas
escondidos do help — a interface lista e executa eles na paleta F1.
"""

import pytest
from typer.testing import CliRunner

from conduto import cli


@pytest.fixture()
def terminal(monkeypatch):
    """Finge terminal interativo (o conftest desliga a TUI por padrão)."""
    monkeypatch.setattr("conduto.tui.prompts._tem_terminal", lambda: True)


@pytest.fixture()
def sem_terminal(monkeypatch):
    monkeypatch.setattr("conduto.tui.prompts._tem_terminal", lambda: False)


def _spa_fake(monkeypatch, resultados):
    """SpaApp duble: registra como foi aberto e devolve ações em fila."""
    chamadas = []

    class SpaFake:
        def __init__(self, *args, **kwargs):
            chamadas.append({"modo": args[0] if args else None, **kwargs})

        def run(self):
            return resultados.pop(0) if resultados else None

    monkeypatch.setattr("conduto.tui.spa_shell.SpaApp", SpaFake)
    return chamadas


def test_help_mostra_como_iniciar_e_esconde_o_resto():
    resultado = CliRunner().invoke(cli.app, ["--help"])
    assert resultado.exit_code == 0
    assert "init" in resultado.output
    for comando in ("ddl", "schedules", "dagster", "docs", "inferir",
                    "install-sqlserver-driver", "dashboard"):
        assert comando not in resultado.output


def test_comandos_seguem_registrados_para_scripts():
    from typer.main import get_command

    grupo = get_command(cli.app)
    nomes = {cmd for cmd in grupo.commands}
    assert {"init", "ddl", "schedules", "dagster", "docs", "inferir",
            "install-sqlserver-driver", "dashboard"} <= nomes
    for nome in ("ddl", "schedules", "dagster", "docs", "inferir",
                 "install-sqlserver-driver", "dashboard"):
        assert grupo.commands[nome].hidden is True
    assert grupo.commands["init"].hidden is False


def test_init_com_nome_abre_o_painel_de_criacao(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    chamadas = _spa_fake(monkeypatch, [None])

    resultado = CliRunner().invoke(cli.app, ["init", "demo"])

    assert resultado.exit_code == 0
    [chamada] = chamadas
    assert chamada["modo"] == "criar"
    assert chamada["project_name"] == "demo"


def test_init_ponto_no_projeto_administra_o_atual(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.yml").write_text('project: demo\n', encoding="utf-8")
    chamadas = _spa_fake(monkeypatch, [None])

    resultado = CliRunner().invoke(cli.app, ["init", "."])

    assert resultado.exit_code == 0
    [chamada] = chamadas
    assert chamada["modo"] == "administrar"
    assert chamada["project_dir"] == tmp_path


def test_init_sem_nome_no_projeto_administra(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.yml").write_text('project: demo\n', encoding="utf-8")
    chamadas = _spa_fake(monkeypatch, [None])

    resultado = CliRunner().invoke(cli.app, ["init"])

    assert resultado.exit_code == 0
    [chamada] = chamadas
    assert chamada["modo"] == "administrar"


def test_init_com_nome_em_pasta_que_ja_e_projeto_administra(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "main.yml").write_text('project: demo\n', encoding="utf-8")
    chamadas = _spa_fake(monkeypatch, [None])

    resultado = CliRunner().invoke(cli.app, ["init", "demo"])

    assert resultado.exit_code == 0
    [chamada] = chamadas
    assert chamada["modo"] == "administrar"


def test_init_sem_terminal_mantem_o_fluxo_legado(tmp_path, monkeypatch, sem_terminal):
    monkeypatch.chdir(tmp_path)
    chamadas = []
    monkeypatch.setattr(cli, "rodar_no_shell", lambda *a, **k: chamadas.append((a, k)))

    resultado = CliRunner().invoke(cli.app, ["init", "demo"])

    assert resultado.exit_code == 0
    assert len(chamadas) == 1


def test_init_fora_de_projeto_sem_nome_erra_com_dica(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)

    resultado = CliRunner().invoke(cli.app, ["init"])

    assert resultado.exit_code == 1
    assert "meu_projeto" in resultado.output


def test_criar_devolve_administrar_e_o_cli_reabre_no_projeto(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    alvos = [tmp_path / "demo"]
    chamadas = _spa_fake(monkeypatch, [
        {"acao": "administrar", "project_dir": str(tmp_path / "demo")},
        None,
    ])

    resultado = CliRunner().invoke(cli.app, ["init", "demo"])

    assert resultado.exit_code == 0
    assert len(chamadas) == 2
    assert chamadas[0]["modo"] == "criar"
    assert chamadas[1]["modo"] == "administrar"
    assert chamadas[1]["project_dir"] == alvos[0]


def test_sair_para_dagster_sobe_o_servidor(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.yml").write_text('project: demo\n', encoding="utf-8")
    _spa_fake(monkeypatch, [{"acao": "dagster", "project_dir": str(tmp_path)}])
    chamadas = []
    monkeypatch.setattr(cli, "_subir_servidor_dagster", lambda d: chamadas.append(d))

    resultado = CliRunner().invoke(cli.app, ["init", "."])

    assert resultado.exit_code == 0
    assert chamadas == [tmp_path]


def test_sair_para_docs_abre_a_documentacao(tmp_path, monkeypatch, terminal):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.yml").write_text('project: demo\n', encoding="utf-8")
    _spa_fake(monkeypatch, [{"acao": "docs", "project_dir": str(tmp_path)}])
    chamadas = []
    monkeypatch.setattr(cli, "servir_docs", lambda *a, **k: chamadas.append((a, k)))

    resultado = CliRunner().invoke(cli.app, ["init"])

    assert resultado.exit_code == 0
    assert chamadas and chamadas[0][0][0] == tmp_path
