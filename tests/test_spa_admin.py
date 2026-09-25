"""Telas de administração: visão geral, conexões, DDL, schedules, inferir.

Pilot headless com `ServicosAdmin` mockado — nenhum teste toca em banco
de verdade. Cada tela de ação tem método público (`gerar`, `aplicar`,
`regenerar`, `inferir`, `instalar_driver`) usado pelo botão, pelo F8 e
pela paleta: um caminho só de execução.
"""

import asyncio

import pytest
from textual.widgets import Button, ContentSwitcher, Input, ListView, RichLog, Select

from conduto.i18n import definir_idioma
from conduto.tui.spa_admin import ServicosAdmin
from conduto.tui.spa_modelo import MODO_ADMINISTRAR
from conduto.tui.spa_shell import SpaApp


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


def _servicos_admin(**kw):
    base = dict(
        ler_conexoes=lambda d: ({"tipo": "postgresql", "host": "db01", "port": "5432",
                                 "database": "postgres", "user": "postgres",
                                 "password": "pw", "schema": "public"},
                                {"tipo": "duckdb", "host": "lake.duckdb", "port": "",
                                 "database": "lake.duckdb", "user": "",
                                 "password": "", "schema": "main"}),
        salvar_conexoes=lambda d, o, dest: None,
        ddl_texto=lambda d: "CREATE TABLE clientes (id INT);",
        ddl_aplicar=lambda d: 2,
        schedules=lambda d: ["clientes", "pedidos"],
        inferir=lambda d, t: ["clientes"],
        driver=lambda: "Driver ODBC 18 instalado.",
    )
    base.update(kw)
    return ServicosAdmin(**base)


ENV_EXEMPLO = """\
DB_ORIGEM_TYPE=postgresql
DB_ORIGEM_HOST=localhost
DB_ORIGEM_PORT=5432
DB_ORIGEM_NAME=postgres
DB_ORIGEM_USER=postgres
DB_ORIGEM_PASSWORD=postgres
DB_ORIGEM_SCHEMA=public
DB_DESTINO_TYPE=duckdb
DB_DESTINO_HOST=dest.duckdb
DB_DESTINO_PORT=
DB_DESTINO_NAME=dest.duckdb
DB_DESTINO_USER=
DB_DESTINO_PASSWORD=
DB_DESTINO_SCHEMA=main
"""

MAIN_EXEMPLO = 'version: "1.0"\nproject: demo\ntables:\n  - path: "schemas/clientes.yml"\n'


def _projeto(tmp_path):
    (tmp_path / ".env").write_text(ENV_EXEMPLO, encoding="utf-8")
    (tmp_path / "main.yml").write_text(MAIN_EXEMPLO, encoding="utf-8")
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "clientes.yml").write_text("table: clientes\ncolumns: []\n", encoding="utf-8")
    dagster = tmp_path / "conduto_dagster"
    dagster.mkdir()
    (dagster / "definitions.py").write_text("# defs\n", encoding="utf-8")
    return tmp_path


async def _ir_para(app, pilot, indice):
    menu = app.query_one(ListView)
    menu.focus()
    menu.index = indice
    await pilot.press("enter")
    await pilot.pause()


async def _rolar_ate(tela, pilot, seletor):
    tela.scroll_to_widget(tela.query_one(seletor), animate=False)
    await pilot.pause()


def test_visao_geral_mostra_saude_do_projeto(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            texto = app.query_one("#tela-visao").resumo_texto
            assert "demo" in texto
            assert "clientes" in texto
            assert "postgresql" in texto
            assert "duckdb" in texto
        return None

    _rodar(cenario)


def test_conexoes_vem_preenchidas_do_env(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-conexoes")
            assert tela.query_one("#origem-tipo", Select).value == "postgresql"
            assert tela.query_one("#origem-host", Input).value == "db01"
            assert tela.query_one("#admin-origem-schema", Input).value == "public"
            assert tela.query_one("#destino-tipo", Select).value == "duckdb"
        return None

    _rodar(cenario)


def test_conexoes_vem_do_sqlite_quando_existe(tmp_path):
    """Fiação real: store sqlite -> default ler_conexoes -> pré-preenche."""
    from conduto.conexoes_store import salvar_conexoes

    _projeto(tmp_path)
    salvar_conexoes(tmp_path, {"tipo": "mysql", "host": "db02", "port": "3306",
                               "user": "root", "password": "", "database": "loja",
                               "schema": "loja"},
                    {"tipo": "duckdb", "host": "lake.duckdb", "port": "",
                     "database": "lake.duckdb", "user": "", "password": "",
                     "schema": "main"}, backend="sqlite")

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=tmp_path,
                     servicos_admin=ServicosAdmin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-conexoes")
            assert tela.query_one("#origem-tipo", Select).value == "mysql"
            assert tela.query_one("#origem-host", Input).value == "db02"
        return None

    _rodar(cenario)


def test_conexoes_salvar_grava_no_env_e_marca_na_timeline(tmp_path):
    chamadas = []

    def _salvar(d, origem, destino):
        chamadas.append((origem["host"], destino["host"]))

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin(salvar_conexoes=_salvar))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-conexoes")
            await _rolar_ate(tela, pilot, "#admin-btn-salvar")
            await pilot.click("#admin-btn-salvar")
            await pilot.pause()
            assert "salv" in tela.status_texto.lower()
            await _ir_para(app, pilot, 0)
            assert "✓ Conexões" in app.query_one("#timeline").texto
        return None

    _rodar(cenario)
    assert chamadas == [("db01", "lake.duckdb")]


def test_ddl_gerar_mostra_o_sql_no_log(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 2)
            tela = app.query_one("#tela-ddl")
            await _rolar_ate(tela, pilot, "#ddl-btn-gerar")
            await pilot.click("#ddl-btn-gerar")
            await pilot.pause()
            await pilot.pause()
            linhas = "\n".join(line.text for line in app.query_one("#ddl-log", RichLog).lines)
            assert "CREATE TABLE clientes" in linhas
        return None

    _rodar(cenario)


def test_ddl_aplicar_roda_e_marca_na_timeline(tmp_path):
    chamadas = []

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin(ddl_aplicar=lambda d, relatar: chamadas.append(d) or 2))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 2)
            tela = app.query_one("#tela-ddl")
            await _rolar_ate(tela, pilot, "#ddl-btn-aplicar")
            await pilot.click("#ddl-btn-aplicar")
            await pilot.pause()
            await pilot.pause()
            assert "2" in tela.status_texto
            await _ir_para(app, pilot, 0)
            assert "✓ DDL" in app.query_one("#timeline").texto
        return None

    _rodar(cenario)
    assert len(chamadas) == 1


def test_schedules_regenerar_roda_com_log(tmp_path):
    chamadas = []

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin(schedules=lambda d, relatar: chamadas.append(d) or ["clientes"]))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 3)
            await _rolar_ate(app.query_one("#tela-schedules"), pilot, "#sched-btn-regenerar")
            await pilot.click("#sched-btn-regenerar")
            await pilot.pause()
            await pilot.pause()
            linhas = "\n".join(line.text for line in app.query_one("#sched-log", RichLog).lines)
            assert "clientes" in linhas
        return None

    _rodar(cenario)
    assert len(chamadas) == 1


def test_inferir_usa_a_tabela_digitada(tmp_path):
    chamadas = []

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin(inferir=lambda d, t, relatar: chamadas.append(t) or ["pedidos"]))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 4)
            app.query_one("#inferir-tabela", Input).value = "pedidos"
            await _rolar_ate(app.query_one("#tela-inferir"), pilot, "#inferir-btn")
            await pilot.click("#inferir-btn")
            await pilot.pause()
            await pilot.pause()
            linhas = "\n".join(line.text for line in app.query_one("#inferir-log", RichLog).lines)
            assert "pedidos" in linhas
        return None

    _rodar(cenario)
    assert chamadas == ["pedidos"]


def test_servidores_dagster_e_docs_saem_com_acao(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 5)
            tela = app.query_one("#tela-servidores")
            await _rolar_ate(tela, pilot, "#srv-btn-docs")
            await pilot.click("#srv-btn-docs")
            await pilot.pause()
        return app.return_value

    assert _rodar(cenario)["acao"] == "docs"


def test_servidores_driver_instala_com_log(tmp_path):
    chamadas = []

    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin(driver=lambda relatar: chamadas.append(1) or "Driver ok."))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 5)
            tela = app.query_one("#tela-servidores")
            await _rolar_ate(tela, pilot, "#srv-btn-driver")
            await pilot.click("#srv-btn-driver")
            await pilot.pause()
            await pilot.pause()
            linhas = "\n".join(line.text for line in app.query_one("#srv-log", RichLog).lines)
            assert "Driver ok." in linhas
            assert app.query_one("#srv-btn-dagster", Button) is not None
        return None

    _rodar(cenario)
    assert chamadas == [1]
