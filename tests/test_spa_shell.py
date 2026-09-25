"""Casca SPA: header, menu, conteúdo, footer do conteúdo, timeline e footer.

Segue o padrão dos outros testes TUI (Pilot headless, serviços mockados).
A regra (modo, timeline, comandos) mora em `spa_modelo`; aqui garantimos
que a casca a desenha e que F1/F2/Ctrl+Q + atalhos do form funcionam.
"""

import asyncio

import pytest
from textual.widgets import ContentSwitcher, Input, ListView, OptionList

from conduto import __version__
from conduto.i18n import definir_idioma
from conduto.init_exec import ResultadoInit
from conduto.tui.init_servicos import ServicosInit
from conduto.tui.spa_admin import ServicosAdmin
from conduto.tui.spa_modelo import MODO_ADMINISTRAR, MODO_CRIAR
from conduto.tui.spa_shell import SpaApp


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


def _servicos_criar(**kw):
    base = dict(
        listar_bancos=lambda adapter, cred: ["db1", "db2"],
        listar_schemas=lambda adapter, cred: ["public", "stg"],
        criar_banco=lambda adapter, cred, nome: None,
        criar_schema=lambda adapter, cred, nome: None,
        carregar_tabelas=lambda adapter, cred: [{"schema": "public", "table": "clientes"}],
        executar=lambda params, relatar, silenciar: ResultadoInit(
            project_dir=params.project_dir, env_path=None, schemas_gerados=1,
            schedules=True, ddl_comandos=0, ddl_aplicado=False,
        ),
    )
    base.update(kw)
    return ServicosInit(**base)


def _servicos_admin(**kw):
    base = dict(
        ler_conexoes=lambda d: ({"tipo": "postgresql", "host": "h", "port": "5432",
                                 "database": "db", "user": "u", "password": "p", "schema": "public"},
                                {"tipo": "duckdb", "host": "d.duckdb", "port": "",
                                 "database": "d.duckdb", "user": "", "password": "", "schema": "main"}),
        salvar_conexoes=lambda d, o, dest: None,
        ddl_texto=lambda d: "CREATE TABLE a (id INT);",
        ddl_aplicar=lambda d, relatar: 1,
        schedules=lambda d, relatar: ["clientes"],
        inferir=lambda d, t, relatar: ["clientes"],
        driver=lambda relatar: "ok",
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
    return tmp_path


async def _ir_para(app, pilot, indice):
    menu = app.query_one(ListView)
    menu.focus()
    menu.index = indice
    await pilot.press("enter")
    await pilot.pause()


# ---------------------------------------------------------------------------
# Casca: header, menu, timeline, footer do conteúdo
# ---------------------------------------------------------------------------


def test_painel_honra_nome_absoluto_mesmo_em_projeto_uv(tmp_path):
    alvo = tmp_path / "teste"
    app = SpaApp(MODO_CRIAR, project_name=str(alvo), em_projeto_uv=True)
    assert app.project_dir_previsto() == alvo


def test_header_traz_marca_versao_e_contexto():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            marca = app.query_one("#marca").marca_texto
            assert "conduto" in marca
            assert __version__ in marca
            assert "demo" in marca
        return None

    _rodar(cenario)


def test_menu_do_criar_tem_as_seis_etapas_e_comeca_no_inicio():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = app.query_one(ListView)
            assert [i.id for i in menu.children] == [
                "menu-inicio", "menu-origem", "menu-destino",
                "menu-schemas", "menu-opcoes", "menu-revisao",
            ]
            assert app.query_one(ContentSwitcher).current == "tela-inicio"
        return None

    _rodar(cenario)


def test_timeline_comeca_com_inicio_atual_e_resto_pendente():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#timeline").texto == (
                "● Início  ○ Origem  ○ Destino  ○ Schemas  ○ Opções  ○ Revisão"
            )
        return None

    _rodar(cenario)


def test_navegar_atualiza_conteudo_timeline_e_atalhos_do_form():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            assert app.query_one(ContentSwitcher).current == "tela-origem"
            assert app.query_one("#timeline").texto == (
                "✓ Início  ● Origem  ○ Destino  ○ Schemas  ○ Opções  ○ Revisão"
            )
            atalhos = app.query_one("#atalhos-conteudo").texto
            assert "F5" in atalhos
            assert "Testar" in atalhos
        return None

    _rodar(cenario)


def test_f5_na_origem_carrega_as_listas():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            from textual.widgets import Select
            tela.query_one("#origem-tipo", Select).value = "postgresql"
            await pilot.pause()
            tela.query_one("#origem-host", Input).value = "localhost"
            tela.query_one("#origem-porta", Input).value = "5432"
            tela.query_one("#origem-user", Input).value = "postgres"
            tela.query_one("#origem-host", Input).focus()
            await pilot.press("f5")
            await pilot.pause()
            await pilot.pause()
            assert tela.opcoes_banco == ["db1", "db2"]
        return None

    _rodar(cenario)


def test_ctrl_t_na_origem_testa_sem_banco_de_verdade():
    chamadas = []

    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            form = tela.query_one("#form-origem")
            form._testar_fn = lambda cred: chamadas.append(cred) or (True, "ok")
            from textual.widgets import Select
            tela.query_one("#origem-tipo", Select).value = "postgresql"
            await pilot.pause()
            tela.query_one("#origem-host", Input).value = "localhost"
            tela.query_one("#origem-porta", Input).value = "5432"
            tela.query_one("#origem-user", Input).value = "postgres"
            tela.query_one("#origem-host", Input).focus()
            await pilot.press("ctrl+t")
            await pilot.pause()
            assert len(chamadas) == 1
            assert "sucesso" in form.status_texto.lower()
        return None

    _rodar(cenario)


def test_f2_volta_o_foco_para_o_menu():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            app.query_one("#origem-host", Input).focus()
            await pilot.press("f2")
            await pilot.pause()
            assert app.query_one(ListView).has_focus
        return None

    _rodar(cenario)


def test_ctrl_q_encerra_a_interface():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+q")
            await pilot.pause()
        return app.return_value

    assert _rodar(cenario) is None


# ---------------------------------------------------------------------------
# Paleta F1: filtrar, navegar, executar, fechar
# ---------------------------------------------------------------------------


def test_f1_abre_a_paleta_com_todos_os_comandos_do_modo():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            assert app.screen.query_one("#cmd-filtro", Input) is not None
            assert app.screen.query_one("#cmd-lista", OptionList).option_count == 6
        return None

    _rodar(cenario)


def test_filtro_da_paleta_estreita_a_lista():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            await pilot.press("c", "r", "i", "a", "r")
            await pilot.pause()
            assert app.screen.query_one("#cmd-lista", OptionList).option_count == 1
        return None

    _rodar(cenario)


def test_enter_na_paleta_navega_e_fecha():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            await pilot.press("c", "r", "i", "a", "r")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one(ContentSwitcher).current == "tela-revisao"
            assert len(app.screen_stack) == 1
        return None

    _rodar(cenario)


def test_esc_fecha_a_paleta_sem_fazer_nada():
    async def cenario():
        app = SpaApp(MODO_CRIAR, project_name="demo", servicos=_servicos_criar())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1
            assert app.query_one(ContentSwitcher).current == "tela-inicio"
        return None

    _rodar(cenario)


# ---------------------------------------------------------------------------
# Modo administrar: menu, visão geral, paleta executa com log
# ---------------------------------------------------------------------------


def test_admin_tem_menu_proprio_e_abre_na_visao_geral(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = app.query_one(ListView)
            assert [i.id for i in menu.children] == [
                "menu-visao", "menu-conexoes", "menu-ddl",
                "menu-schedules", "menu-inferir", "menu-servidores",
            ]
            assert app.query_one(ContentSwitcher).current == "tela-visao"
            assert "demo" in app.query_one("#tela-visao").resumo_texto
            assert app.query_one("#timeline").texto.startswith("● Visão geral")
        return None

    _rodar(cenario)


def test_admin_paleta_executa_ddl_gerar_na_tela_com_log(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            await pilot.press("d", "d", "l", ":", " ", "g")
            await pilot.pause()
            assert app.screen.query_one("#cmd-lista", OptionList).option_count == 1
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            assert app.query_one(ContentSwitcher).current == "tela-ddl"
            from textual.widgets import RichLog
            assert len(app.query_one("#ddl-log", RichLog).lines) >= 1
        return None

    _rodar(cenario)


def test_admin_paleta_dagster_sai_com_acao_para_o_cli(tmp_path):
    async def cenario():
        app = SpaApp(MODO_ADMINISTRAR, project_dir=_projeto(tmp_path),
                     servicos_admin=_servicos_admin())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f1")
            await pilot.pause()
            await pilot.press("s", "u", "b", "i", "r")
            await pilot.pause()
            assert app.screen.query_one("#cmd-lista", OptionList).option_count == 1
            await pilot.press("enter")
            await pilot.pause()
        return app.return_value

    resultado = _rodar(cenario)
    assert resultado["acao"] == "dagster"
    assert "test_admin_paleta_dagster" in resultado["project_dir"]
