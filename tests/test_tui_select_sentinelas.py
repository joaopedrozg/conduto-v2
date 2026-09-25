"""Sentinelas do Select nunca viram nome de banco/credencial.

Regressão de um erro real: ao trocar o banco com SQL Server, um
``Select.Changed`` com valor ``Select.NULL`` passava pelo guarda
``!= Select.BLANK`` e o ``str()`` dele (``"Select.NULL"``) ia parar no
``DATABASE`` da connection string do ODBC:

    Cannot open database "Select.NUL" requested by the login.

A regra (pura, sem UI) mora em ``texto_de_select``; aqui garantimos que
nenhum caminho de leitura de Select deixa sentinel vazar.
"""

import asyncio

import pytest
from textual.widgets import Button, ContentSwitcher, Input, Select

from conduto.database import drivers as drivers_mod
from conduto.i18n import definir_idioma
from conduto.tui.conexoes import texto_de_select
from conduto.tui.dashboard import CondutoApp, FormularioConexao


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


# ---------------------------------------------------------------------------
# Regra pura
# ---------------------------------------------------------------------------


def test_texto_de_select_so_aceita_str():
    assert texto_de_select("postgresql") == "postgresql"
    assert texto_de_select("") == ""
    assert texto_de_select(None) == ""
    assert texto_de_select(Select.BLANK) == ""
    assert texto_de_select(Select.NULL) == ""
    assert texto_de_select(False) == ""
    assert texto_de_select(0) == ""


def test_str_do_null_e_o_texto_do_erro_reportado():
    # Amarração explícita com o bug: se isso vazar, o ODBC recebe o nome.
    assert "Select.NUL" in str(Select.NULL)
    assert texto_de_select(Select.NULL) == ""


# ---------------------------------------------------------------------------
# Form: Changed(NULL) não pergunta driver nem quebra nada
# ---------------------------------------------------------------------------


def test_changed_null_no_tipo_nao_oferece_driver(monkeypatch):
    chamadas = []

    async def cenario():
        monkeypatch.setattr(
            drivers_mod, "drivers_faltantes", lambda tipo: chamadas.append(tipo) or ("psycopg",)
        )
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(ContentSwitcher).current = "tela-conexoes"
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            select = form.query_one(Select)
            select.post_message(Select.Changed(select, Select.NULL))
            await pilot.pause()
            await pilot.pause()
            # NULL não é tipo: nem checa driver, nem mexe no status.
            assert chamadas == []
            assert form.query_one("#origem-btn-driver", Button).disabled is True
            assert form.status_texto == ""
            assert form.ler_config().tipo == ""
        return None

    _rodar(cenario)


# ---------------------------------------------------------------------------
# Tela de conexão do init: Changed(NULL) no banco não lista schemas
# ---------------------------------------------------------------------------


def test_changed_null_no_banco_nao_lista_schemas(monkeypatch):
    from conduto.tui.init_app import InitApp
    from conduto.tui.init_servicos import ServicosInit

    chamadas = []

    async def cenario():
        servicos = ServicosInit(
            listar_bancos=lambda a, c: ["db1"],
            listar_schemas=lambda a, c: chamadas.append(c["database"]) or ["public"],
            criar_banco=lambda a, c, n: None,
            criar_schema=lambda a, c, n: None,
            carregar_tabelas=lambda a, c: [],
            executar=lambda p, r, s: None,
        )
        app = InitApp(project_name="demo", servicos=servicos)
        async with app.run_test() as pilot:
            await pilot.pause()
            tela = app.query_one("#tela-origem")
            tela.query_one("#origem-tipo", Select).value = "sqlserver"
            await pilot.pause()
            tela.query_one("#origem-host", Input).value = "srv"
            tela.query_one("#origem-porta", Input).value = "1433"
            tela.query_one("#origem-user", Input).value = "sa"
            banco = tela.query_one("#origem-banco", Select)
            banco.set_options([("db1", "db1")])
            banco.post_message(Select.Changed(banco, Select.NULL))
            await pilot.pause()
            await pilot.pause()
            # Nenhuma listagem com nome fantasma; estado fica vazio, não sujo.
            assert chamadas == []
            tela.sincronizar_estado()
            assert app.estado.origem_database == ""
        return None

    _rodar(cenario)


def test_valor_do_banco_com_null_sincroniza_vazio(monkeypatch):
    from conduto.tui.init_app import InitApp
    from conduto.tui.init_servicos import ServicosInit

    async def cenario():
        servicos = ServicosInit(
            listar_bancos=lambda a, c: [],
            listar_schemas=lambda a, c: [],
            criar_banco=lambda a, c, n: None,
            criar_schema=lambda a, c, n: None,
            carregar_tabelas=lambda a, c: [],
            executar=lambda p, r, s: None,
        )
        app = InitApp(project_name="demo", servicos=servicos)
        async with app.run_test() as pilot:
            await pilot.pause()
            tela = app.query_one("#tela-origem")
            banco = tela.query_one("#origem-banco", Select)
            banco.set_options([("db1", "db1")])
            banco.post_message(Select.Changed(banco, Select.NULL))
            await pilot.pause()
            tela.sincronizar_estado()
            assert app.estado.origem_database == ""
            assert app.estado.origem_schema == ""
        return None

    _rodar(cenario)
