"""Painel do `conduto init`: menu lateral + formulários por etapa.

Segue o padrão de `test_tui_dashboard.py` (Pilot headless). Serviços
externos (banco, execução) entram por `ServicosInit` mockado — nenhum
teste precisa de banco de verdade. A navegação usa o menu (como o
usuário faz) e o preenchimento usa os widgets (a sincronização lê os
widgets, então estado injetado direto seria apagado).
"""

import asyncio

import pytest
from textual.widgets import Button, ContentSwitcher, Input, ListView, RichLog, Select

from conduto.i18n import definir_idioma
from conduto.init_exec import ResultadoInit
from conduto.tui.dashboard import FormularioConexao
from conduto.tui.init_app import InitApp
from conduto.tui.init_modelo import MODO_AUTO
from conduto.tui.init_servicos import ServicosInit


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


def _servicos(**kw):
    base = dict(
        listar_bancos=lambda adapter, cred: ["db1", "db2"],
        listar_schemas=lambda adapter, cred: ["public", "stg"],
        criar_banco=lambda adapter, cred, nome: None,
        criar_schema=lambda adapter, cred, nome: None,
        carregar_tabelas=lambda adapter, cred: [{"schema": "public", "table": "clientes"}],
        executar=lambda params, relatar, silenciar: ResultadoInit(
            project_dir=params.project_dir,
            env_path=None,
            schemas_gerados=1,
            schedules=True,
            ddl_comandos=0,
            ddl_aplicado=False,
        ),
    )
    base.update(kw)
    return ServicosInit(**base)


async def _ir_para(app, pilot, indice):
    """Navega pelo menu (sincroniza tudo no caminho, como no uso real)."""
    menu = app.query_one(ListView)
    menu.focus()
    menu.index = indice
    await pilot.press("enter")
    await pilot.pause()


async def _rolar_ate(tela, pilot, seletor):
    """Rola a tela até o widget (telas longas passam da viewport)."""
    tela.scroll_to_widget(tela.query_one(seletor), animate=False)
    await pilot.pause()


async def _preencher_origem(app, pilot):
    tela = app.query_one("#tela-origem")
    tela.query_one("#origem-tipo", Select).value = "postgresql"
    await pilot.pause()  # Changed preenche a porta padrão
    tela.query_one("#origem-host", Input).value = "localhost"
    tela.query_one("#origem-porta", Input).value = "5432"
    tela.query_one("#origem-user", Input).value = "postgres"
    banco = tela.query_one("#origem-banco", Select)
    banco.set_options([("db1", "db1"), ("db2", "db2")])
    banco.value = "db1"
    await pilot.pause()  # Changed do banco carrega os schemas (mock)
    await pilot.pause()
    tela.query_one("#origem-schema", Select).value = "public"
    await pilot.pause()


async def _preencher_destino(app, pilot):
    tela = app.query_one("#tela-destino")
    tela.query_one("#destino-tipo", Select).value = "postgresql"
    await pilot.pause()
    tela.query_one("#destino-host", Input).value = "localhost"
    tela.query_one("#destino-porta", Input).value = "5432"
    tela.query_one("#destino-user", Input).value = "postgres"
    banco = tela.query_one("#destino-banco", Select)
    banco.set_options([("db1", "db1"), ("db2", "db2")])
    banco.value = "db2"
    await pilot.pause()
    await pilot.pause()
    tela.query_one("#destino-schema", Select).value = "stg"
    await pilot.pause()


def test_abre_no_inicio_com_seis_etapas():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = app.query_one(ListView)
            assert [i.id for i in menu.children] == [
                "menu-inicio",
                "menu-origem",
                "menu-destino",
                "menu-schemas",
                "menu-opcoes",
                "menu-revisao",
            ]
            assert app.query_one(ContentSwitcher).current == "tela-inicio"
            assert app.query_one("#init-nome", Input).value == "demo"
        return None

    _rodar(cenario)


def test_menu_troca_de_tela():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 2)
            assert app.query_one(ContentSwitcher).current == "tela-destino"
            assert app.query_one("#form-destino", FormularioConexao) is not None
        return None

    _rodar(cenario)


def test_inicio_mostra_checklist_e_pendencias():
    async def cenario():
        app = InitApp(project_name="", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            tela = app.query_one("#tela-inicio")
            assert "Origem" in tela.checklist_texto
            assert "Destino" in tela.checklist_texto
            assert tela.pendencias_texto.strip() != ""
        return None

    _rodar(cenario)


def test_origem_carregar_listas_preenche_bancos():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            tela.query_one("#origem-tipo", Select).value = "postgresql"
            await pilot.pause()
            tela.query_one("#origem-host", Input).value = "localhost"
            tela.query_one("#origem-porta", Input).value = "5432"
            tela.query_one("#origem-user", Input).value = "postgres"
            await pilot.pause()
            await pilot.pause()
            await _rolar_ate(tela, pilot, "#origem-btn-carregar")
            await pilot.click("#origem-btn-carregar")
            await pilot.pause()
            await pilot.pause()
            assert tela.opcoes_banco == ["db1", "db2"]
        return None

    _rodar(cenario)


def test_origem_com_falha_no_servico_mostra_status():
    def _boom(adapter, cred):
        raise RuntimeError("rede fora")

    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos(listar_bancos=_boom))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            tela.query_one("#origem-tipo", Select).value = "postgresql"
            await pilot.pause()
            tela.query_one("#origem-host", Input).value = "localhost"
            tela.query_one("#origem-porta", Input).value = "5432"
            tela.query_one("#origem-user", Input).value = "postgres"
            await pilot.pause()
            await pilot.pause()
            await _rolar_ate(tela, pilot, "#origem-btn-carregar")
            await pilot.click("#origem-btn-carregar")
            await pilot.pause()
            await pilot.pause()
            assert "rede fora" in tela.status_listas
        return None

    _rodar(cenario)


def test_destino_criar_banco_chama_servico_e_recarega():
    chamadas = []

    def _criar(adapter, cred, nome):
        chamadas.append(nome)

    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos(criar_banco=_criar))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 2)
            tela = app.query_one("#tela-destino")
            # Criar exige conexão válida (é nela que o banco é criado).
            tela.query_one("#destino-tipo", Select).value = "postgresql"
            await pilot.pause()
            tela.query_one("#destino-host", Input).value = "localhost"
            tela.query_one("#destino-porta", Input).value = "5432"
            tela.query_one("#destino-user", Input).value = "postgres"
            tela.query_one("#destino-novo-banco", Input).value = "novo_db"
            await pilot.pause()
            await pilot.pause()
            await _rolar_ate(tela, pilot, "#destino-btn-criar-banco")
            await pilot.click("#destino-btn-criar-banco")
            await pilot.pause()
            await pilot.pause()
        return None

    _rodar(cenario)
    assert chamadas == ["novo_db"]


def test_schemas_carregar_tabelas_monta_painel_marcavel():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _ir_para(app, pilot, 3)
            tela = app.query_one("#tela-schemas")
            await pilot.click("#schemas-btn-carregar")
            await pilot.pause()
            await pilot.pause()
            assert tela.painel is not None
            assert tela.painel.modelo.contagem == (0, 1, 1)
            tela.painel.modelo.alternar(0)
            tela.sincronizar_estado()
            assert app.estado.tabelas_escolhidas == [
                {"schema": "public", "table": "clientes"}
            ]
        return None

    _rodar(cenario)


def test_revisao_bloqueia_criar_com_pendencias():
    chamadas = []

    def _executar(params, relatar, silenciar):
        chamadas.append(params)
        raise AssertionError("não deveria executar")

    async def cenario():
        app = InitApp(project_name="", servicos=_servicos(executar=_executar))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 5)
            await pilot.click("#rev-btn-criar")
            await pilot.pause()
            assert chamadas == []
            assert app.query_one("#tela-revisao").pendencias_texto.strip() != ""
        return None

    _rodar(cenario)


def test_revisao_executa_e_mostra_resultado_e_log():
    vistos = []

    def _executar(params, relatar, silenciar):
        vistos.append(params)
        relatar("Projeto em: /tmp/demo")
        return ResultadoInit(
            project_dir=params.project_dir,
            env_path=None,
            schemas_gerados=1,
            schedules=True,
            ddl_comandos=0,
            ddl_aplicado=False,
        )

    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos(executar=_executar))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _ir_para(app, pilot, 2)
            await _preencher_destino(app, pilot)
            app.estado.modo_schemas = MODO_AUTO
            app.estado.tabelas_escolhidas = [{"schema": "public", "table": "clientes"}]
            await _ir_para(app, pilot, 5)
            tela = app.query_one("#tela-revisao")
            assert tela.pendencias_texto.strip() == "", tela.pendencias_texto
            await pilot.click("#rev-btn-criar")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert "1" in tela.resultado_texto
            assert len(app.query_one("#rev-log", RichLog).lines) >= 1
            assert len(app.query("#rev-btn-dagster")) == 1
        return None

    _rodar(cenario)
    assert len(vistos) == 1
    assert vistos[0].origem["database"] == "db1"
    assert vistos[0].destino["database"] == "db2"


def test_revisao_leva_armazenamento_ate_a_execucao():
    vistos = []

    def _executar(params, relatar, silenciar):
        vistos.append(params)
        return ResultadoInit(
            project_dir=params.project_dir,
            env_path=None,
            schemas_gerados=1,
            schedules=True,
            ddl_comandos=0,
            ddl_aplicado=False,
        )

    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos(executar=_executar))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _ir_para(app, pilot, 2)
            await _preencher_destino(app, pilot)
            app.estado.modo_schemas = MODO_AUTO
            app.estado.tabelas_escolhidas = [{"schema": "public", "table": "clientes"}]
            await _ir_para(app, pilot, 4)
            app.query_one("#tela-opcoes").query_one("#op-armazenamento", Select).value = "sqlite"
            await pilot.pause()
            await _ir_para(app, pilot, 5)
            await pilot.click("#rev-btn-criar")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
        return None

    _rodar(cenario)
    assert [v.armazenamento for v in vistos] == ["sqlite"]


def test_subir_dagster_devolve_acao_para_o_cli():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _ir_para(app, pilot, 2)
            await _preencher_destino(app, pilot)
            app.estado.modo_schemas = MODO_AUTO
            app.estado.tabelas_escolhidas = [{"schema": "public", "table": "clientes"}]
            await _ir_para(app, pilot, 5)
            await pilot.click("#rev-btn-criar")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await _rolar_ate(app.query_one("#tela-revisao"), pilot, "#rev-btn-dagster")
            await pilot.click("#rev-btn-dagster")
            await pilot.pause()
        return app.return_value

    resultado = _rodar(cenario)
    assert resultado["acao"] == "dagster"
    assert "demo" in str(resultado["project_dir"])


async def _adicionar_banco(app, pilot, papel, banco):
    tela = app.query_one(f"#tela-{papel}")
    escolha = tela.query_one(f"#{papel}-banco", Select)
    escolha.set_options([(banco, banco)])
    escolha.value = banco
    await pilot.pause()
    await pilot.pause()
    await _rolar_ate(tela, pilot, f"#{papel}-btn-adicionar")
    await pilot.click(f"#{papel}-btn-adicionar")
    await pilot.pause()
    return tela


def test_banco_adicionar_salva_na_tabela_e_no_estado():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = await _adicionar_banco(app, pilot, "origem", "db1")
            from textual.widgets import DataTable
            assert tela.query_one("#origem-tabela-bancos", DataTable).row_count == 1
            await _ir_para(app, pilot, 2)
            assert app.estado.origem_bancos == ["db1"]
        return None

    _rodar(cenario)


def test_banco_adicionar_sem_selecao_avisa():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            await _rolar_ate(tela, pilot, "#origem-btn-adicionar")
            await pilot.click("#origem-btn-adicionar")
            await pilot.pause()
            from textual.widgets import DataTable
            assert tela.query_one("#origem-tabela-bancos", DataTable).row_count == 0
            assert tela.status_listas.strip() != ""
        return None

    _rodar(cenario)


def test_banco_adicionar_duplicado_avisa_e_nao_duplica():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _adicionar_banco(app, pilot, "origem", "db1")
            tela = await _adicionar_banco(app, pilot, "origem", "db1")
            from textual.widgets import DataTable
            assert tela.query_one("#origem-tabela-bancos", DataTable).row_count == 1
            assert "db1" in tela.status_listas
            await _ir_para(app, pilot, 2)
            assert app.estado.origem_bancos == ["db1"]
        return None

    _rodar(cenario)


def _servicos_por_banco(esquemas):
    return _servicos(listar_schemas=lambda adapter, cred: esquemas[cred["database"]])


def test_schemas_vem_somente_dos_bancos_adicionados():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos_por_banco({"db1": ["public"], "db2": ["stg"]}))
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _adicionar_banco(app, pilot, "origem", "db1")
            await _adicionar_banco(app, pilot, "origem", "db2")
            tela = app.query_one("#tela-origem")
            await _rolar_ate(tela, pilot, "#origem-btn-carregar-schemas")
            await pilot.click("#origem-btn-carregar-schemas")
            await pilot.pause()
            await pilot.pause()
            assert tela.opcoes_schemas == [("db1.public", "public"), ("db2.stg", "stg")]
        return None

    _rodar(cenario)


def test_schemas_sem_bancos_adicionados_usa_o_selecionado():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            tela = app.query_one("#tela-origem")
            await _rolar_ate(tela, pilot, "#origem-btn-carregar-schemas")
            await pilot.click("#origem-btn-carregar-schemas")
            await pilot.pause()
            await pilot.pause()
            assert tela.opcoes_schemas == [("db1.public", "public"), ("db1.stg", "stg")]
        return None

    _rodar(cenario)


def test_schema_adicionar_salva_na_tabela_e_no_estado():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            tela = app.query_one("#tela-origem")
            tela.query_one("#origem-schema", Select).value = "public"
            await pilot.pause()
            await _rolar_ate(tela, pilot, "#origem-btn-adicionar-schema")
            await pilot.click("#origem-btn-adicionar-schema")
            await pilot.pause()
            from textual.widgets import DataTable
            assert tela.query_one("#origem-tabela-schemas", DataTable).row_count == 1
            await _ir_para(app, pilot, 2)
            assert app.estado.origem_schemas == ["public"]
        return None

    _rodar(cenario)


def test_tabelas_dividem_as_colunas_pelo_espaco():
    async def cenario():
        from textual.widgets import DataTable

        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await pilot.pause()
            bancos = app.query_one("#origem-tabela-bancos", DataTable)
            schemas = app.query_one("#origem-tabela-schemas", DataTable)
            largura_bancos = list(bancos.columns.values())[0].width
            largura_schemas = list(schemas.columns.values())[0].width
            assert largura_bancos > 0
            assert largura_bancos == largura_schemas
        return None

    _rodar(cenario)


def test_revisitar_reconstroi_tabelas_do_estado():
    async def cenario():
        from textual.widgets import DataTable

        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            app.estado.origem_bancos = ["db1", "db2"]
            app.estado.origem_schemas = ["public"]
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            assert tela.query_one("#origem-tabela-bancos", DataTable).row_count == 2
            assert tela.query_one("#origem-tabela-schemas", DataTable).row_count == 1
        return None

    _rodar(cenario)


def test_tela_origem_dividida_config_a_esquerda_selecao_a_direita():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            tela = app.query_one("#tela-origem")
            config = tela.query_one("#origem-col-config")
            selecao = tela.query_one("#origem-col-selecao")
            # Esquerda: só o formulário de conexão.
            assert config.query_one(FormularioConexao) is not None
            # Direita: banco/schema + carregar (nada do form).
            assert selecao.query_one("#origem-banco", Select) is not None
            assert selecao.query_one("#origem-schema", Select) is not None
            assert selecao.query_one("#origem-btn-carregar", Button) is not None
            assert len(selecao.query(FormularioConexao)) == 0
            # Lado a lado: mesma linha, mesma largura.
            assert config.region.y == selecao.region.y
            assert config.region.width == selecao.region.width
        return None

    _rodar(cenario)


def test_tela_destino_traz_criacao_no_lado_direito():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 2)
            tela = app.query_one("#tela-destino")
            selecao = tela.query_one("#destino-col-selecao")
            assert selecao.query_one("#destino-novo-banco", Input) is not None
            assert selecao.query_one("#destino-btn-criar-banco", Button) is not None
            assert selecao.query_one("#destino-novo-schema", Input) is not None
            assert selecao.query_one("#destino-btn-criar-schema", Button) is not None
            config = tela.query_one("#destino-col-config")
            assert config.query_one(FormularioConexao) is not None
            assert config.region.y == selecao.region.y
        return None

    _rodar(cenario)


def test_preenchimento_atravessa_as_colunas():
    """O split é só visual: banco da direita + conexão da esquerda sincronizam."""
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 1)
            await _preencher_origem(app, pilot)
            await _ir_para(app, pilot, 2)
            await _preencher_destino(app, pilot)
            await _ir_para(app, pilot, 3)  # sair sincroniza destino
            assert app.estado.origem_database == "db1"
            assert app.estado.origem_schema == "public"
            assert app.estado.destino_database == "db2"
            assert app.estado.destino_schema == "stg"
            assert app.estado.status_origem() is True
            assert app.estado.status_destino() is True
        return None

    _rodar(cenario)


def test_opcoes_guarda_onde_guardar_conexoes():
    async def cenario():
        app = InitApp(project_name="demo", servicos=_servicos())
        async with app.run_test() as pilot:
            await pilot.pause()
            await _ir_para(app, pilot, 4)
            assert app.estado.armazenamento == "env"
            app.query_one("#tela-opcoes").query_one("#op-armazenamento", Select).value = "sqlite"
            await pilot.pause()
            await _ir_para(app, pilot, 5)
            assert app.estado.armazenamento == "sqlite"
        return None

    _rodar(cenario)
