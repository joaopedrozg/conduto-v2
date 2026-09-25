"""Dashboard do Conduto: menu lateral + formulários origem/destino.

Roda o app em headless (``App.run_test``/``Pilot``), como em
``test_tui_telas.py``. A regra de negócio (porta/placeholder/validação)
mora em :mod:`conduto.tui.conexoes`; aqui garantimos que a tela está
ligada nela: menu troca de tela, Select preenche porta, embedded
desabilita porta, Testar/Salvar usam o modelo (sem mocks na tabela).
"""

import asyncio

import pytest
from textual.widgets import Button, ContentSwitcher, DataTable, Input, ListView, Select

from conduto.i18n import definir_idioma
from conduto.tui.conexoes import ConfigConexao
from conduto.tui.dashboard import CondutoApp, FormularioConexao


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


def test_app_abre_no_inicio_com_menu_e_conteudo():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = app.query_one(ListView)
            assert [item.id for item in menu.children] == ["menu-inicio", "menu-conexoes"]
            switcher = app.query_one(ContentSwitcher)
            assert switcher.current == "tela-inicio"
        return None

    _rodar(cenario)


def test_menu_conexoes_troca_para_tela_de_conexoes():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = app.query_one(ListView)
            menu.index = 1
            # OptionList/ListView disparam `Selected` no enter/click.
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one(ContentSwitcher).current == "tela-conexoes"
        return None

    _rodar(cenario)


def test_formulario_tem_select_inputs_botoes_e_tabela():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            assert isinstance(form.query_one(Select), Select)
            for campo in ("host", "porta", "user", "senha"):
                assert len(form.query(f"#{form.papel}-{campo}")) == 1, campo
            assert form.query_one(f"#{form.papel}-senha", Input).password is True
            for botao in ("btn-testar", "btn-salvar"):
                assert form.query_one(f"#{form.papel}-{botao}", Button) is not None, botao
            tabela = form.query_one(DataTable)
            assert [str(c.label) for c in tabela.columns.values()] == ["Banco", "Host", "Usuário"]
            assert tabela.row_count == 0  # sem mocks na tabela
        return None

    _rodar(cenario)


def test_origem_e_destino_sao_independentes():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            origem = app.query_one("#form-origem", FormularioConexao)
            destino = app.query_one("#form-destino", FormularioConexao)
            origem.query_one("#origem-host", Input).value = "db-origem"
            await pilot.pause()
            assert destino.query_one("#destino-host", Input).value == ""
        return None

    _rodar(cenario)


def test_escolher_postgres_preenche_porta_e_host_de_servidor():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            form.query_one(Select).value = "postgresql"
            form.query_one(Select).post_message(Select.Changed(form.query_one(Select), "postgresql"))
            await pilot.pause()
            porta = form.query_one("#origem-porta", Input)
            assert porta.value == "5432"
            assert porta.disabled is False
            assert "localhost" in form.query_one("#origem-host", Input).placeholder.lower()
        return None

    _rodar(cenario)


def test_escolher_duckdb_limpa_e_desabilita_porta():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            form.query_one(Select).value = "postgresql"
            form.query_one(Select).post_message(Select.Changed(form.query_one(Select), "postgresql"))
            await pilot.pause()
            form.query_one(Select).value = "duckdb"
            form.query_one(Select).post_message(Select.Changed(form.query_one(Select), "duckdb"))
            await pilot.pause()
            porta = form.query_one("#origem-porta", Input)
            assert porta.value == ""
            assert porta.disabled is True
            assert "s3://" in form.query_one("#origem-host", Input).placeholder.lower()
        return None

    _rodar(cenario)


def _ir_para_conexoes(app) -> None:
    app.query_one(ContentSwitcher).current = "tela-conexoes"


def test_testar_conexao_ok_mostra_sucesso_sem_banco_de_verdade():
    async def cenario():
        app = CondutoApp(testar_fn=lambda cred: (True, "ok"))
        async with app.run_test() as pilot:
            await pilot.pause()
            _ir_para_conexoes(app)
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            form.query_one(Select).value = "postgresql"
            form.query_one("#origem-host", Input).value = "localhost"
            form.query_one("#origem-porta", Input).value = "5432"
            form.query_one("#origem-user", Input).value = "postgres"
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-testar")
            await pilot.pause()
            assert "sucesso" in form.status_texto.lower() or "ok" in form.status_texto.lower()
        return None

    _rodar(cenario)


def test_testar_conexao_com_falha_mostra_erro():
    async def cenario():
        app = CondutoApp(testar_fn=lambda cred: (False, "senha incorreta"))
        async with app.run_test() as pilot:
            await pilot.pause()
            _ir_para_conexoes(app)
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            form.query_one(Select).value = "postgresql"
            form.query_one("#origem-host", Input).value = "localhost"
            form.query_one("#origem-porta", Input).value = "5432"
            form.query_one("#origem-user", Input).value = "postgres"
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-testar")
            await pilot.pause()
            assert "senha incorreta" in form.status_texto.lower()
        return None

    _rodar(cenario)


def test_salvar_adiciona_linha_na_tabela_do_proprio_formulario():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            _ir_para_conexoes(app)
            await pilot.pause()
            origem = app.query_one("#form-origem", FormularioConexao)
            destino = app.query_one("#form-destino", FormularioConexao)
            origem.query_one(Select).value = "postgresql"
            origem.query_one("#origem-host", Input).value = "localhost"
            origem.query_one("#origem-porta", Input).value = "5432"
            origem.query_one("#origem-user", Input).value = "postgres"
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-salvar")
            await pilot.pause()
            assert origem.query_one(DataTable).row_count == 1
            assert destino.query_one(DataTable).row_count == 0
            # O registro vai para o modelo compartilhado do app.
            assert [(c.tipo, c.host) for c in app.registros.listar()] == [
                ("postgresql", "localhost")
            ]
        return None

    _rodar(cenario)


def test_salvar_invalido_nao_adiciona_e_mostra_pendencia():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            _ir_para_conexoes(app)
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            # Sem tipo/host: inválido.
            await pilot.click("#origem-btn-salvar")
            await pilot.pause()
            assert form.query_one(DataTable).row_count == 0
            assert form.status_texto.strip() != ""
        return None

    _rodar(cenario)


def test_ler_config_do_formulario_devolve_modelo_puro():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = app.query_one("#form-destino", FormularioConexao)
            form.query_one(Select).value = "clickhouse"
            form.query_one("#destino-host", Input).value = "ch.local"
            form.query_one("#destino-porta", Input).value = "8123"
            form.query_one("#destino-user", Input).value = "default"
            await pilot.pause()
            cfg = form.ler_config()
            assert isinstance(cfg, ConfigConexao)
            assert (cfg.tipo, cfg.host, cfg.porta, cfg.user) == (
                "clickhouse",
                "ch.local",
                "8123",
                "default",
            )
        return None

    _rodar(cenario)
