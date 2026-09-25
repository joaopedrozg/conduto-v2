"""Painel do `conduto init`: menu lateral + formulários por etapa.

O wizard legado pergunta tudo em sequência (mantido como fallback sem
terminal); aqui cada etapa é uma tela com formulários e a execução roda
uma vez só na revisão, via :mod:`conduto.init_exec`. Serviços externos
(banco, execução) entram por :class:`ServicosInit` — mockável nos testes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    ContentSwitcher,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Select,
    Static,
)

from conduto.i18n import t
from conduto.schemas.schemas_auto import escolhas_de_tabelas
from conduto.tui.conexoes import adapter_por_tipo, texto_de_select
from conduto.tui.dashboard import FormularioConexao
from conduto.tui.init_modelo import (
    ARMAZENAMENTOS,
    MODO_AUTO,
    MODO_MANUAL,
    TIPOS_SCHEMA_IGUAL_A_BANCO,
    EstadoInit,
    dir_do_projeto,
)
from conduto.tui.init_servicos import ServicosInit
from conduto.tui.modelo import MULTIPLA, ModeloSelecao
from conduto.tui.paineis import PainelSelecao
from conduto.tui.tema import CSS_TEMA

__all__ = ["InitApp", "TelaConexao", "TelaInicio", "TelaOpcoes", "TelaRevisao", "TelaSchemas"]

#: Menu (item) -> tela do ContentSwitcher.
TELAS = {
    "menu-inicio": "tela-inicio",
    "menu-origem": "tela-origem",
    "menu-destino": "tela-destino",
    "menu-schemas": "tela-schemas",
    "menu-opcoes": "tela-opcoes",
    "menu-revisao": "tela-revisao",
}


def _unir(guardados: list, atuais: list) -> list:
    """Une listas preservando a ordem e sem repetir (sem remover)."""
    return list(dict.fromkeys(list(guardados) + list(atuais)))


class _Tela(VerticalScroll):
    """Base: acesso ao app/estado/serviços + dupla sincronizar/atualizar.

    Rolável: os formulários (conexão + listas) passam da viewport em
    terminais pequenos e o usuário rola em vez de perder o conteúdo.

    A mesma tela roda no InitApp e na SPA (``_app_ref`` é o hospedeiro
    da vez) — por isso ``_app()`` não prende o tipo do app.
    """

    def _app(self) -> Any:
        return self._app_ref

    def sincronizar_estado(self) -> None:
        """Widgets -> estado (o app chama ao trocar de tela e antes de criar)."""

    def atualizar(self) -> None:
        """Estado -> widgets (o app chama ao exibir a tela)."""

    def atalhos(self) -> list:
        """Atalhos deste form para o footer do conteúdo (a SPA completa com F1)."""
        return []


class TelaInicio(_Tela):
    """Nome do projeto + checklist das etapas e pendências."""

    def __init__(self, app_ref: "InitApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "tela-inicio"
        self._app_ref = app_ref
        self._checklist = ""
        self._pendencias = ""

    @property
    def checklist_texto(self) -> str:
        return self._checklist

    @property
    def pendencias_texto(self) -> str:
        return self._pendencias

    def compose(self) -> ComposeResult:
        yield Label(t("Novo projeto"))
        yield Input(
            value=self._app_ref.estado.nome_projeto,
            placeholder=t("Nome do projeto (ex: meu_projeto)"),
            id="init-nome",
        )
        if self._app_ref.em_projeto_uv:
            yield Label(t("Projeto uv detectado: a estrutura será adaptada ao atual."))
        yield Label(t("Etapas"))
        yield Static("", id="init-checklist")
        yield Static("", id="init-pendencias", classes="pendencias")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "init-nome":
            self._app_ref.estado.nome_projeto = event.value

    def sincronizar_estado(self) -> None:
        try:
            self._app_ref.estado.nome_projeto = self.query_one("#init-nome", Input).value
        except Exception:
            pass

    def atualizar(self) -> None:
        estado = self._app_ref.estado
        marcas = [
            (t("Origem"), estado.status_origem()),
            (t("Destino"), estado.status_destino()),
            (t("Schemas"), estado.status_schemas()),
        ]
        linhas = [f"{'✓' if ok else '○'} {rotulo}" for rotulo, ok in marcas]
        self._checklist = "\n".join(linhas)
        self._pendencias = "\n".join(estado.pendencias())
        self.query_one("#init-checklist", Static).update(self._checklist)
        self.query_one("#init-pendencias", Static).update(self._pendencias)


class TelaConexao(_Tela):
    """Conexão + banco/schema de um papel (origem ou destino).

    O destino permite criar banco/schema; a origem só escolhe.
    """

    BINDINGS = [
        Binding("f5", "carregar", "Carregar listas"),
        Binding("ctrl+t", "testar", "Testar"),
    ]

    def __init__(self, app_ref: "InitApp", papel: str = "origem", **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = f"tela-{papel}"
        self.papel = papel
        self._app_ref = app_ref
        self._status = ""
        self._opcoes_banco: list = []
        self._opcoes_schemas: list = []
        #: Bancos/schemas adicionados (listas de trabalho; vão ao estado no sync).
        self._bancos: list = []
        self._schemas: list = []

    def atalhos(self) -> list:
        return [("F5", t("Carregar listas")), ("Ctrl+T", t("Testar conexão"))]

    @property
    def status_listas(self) -> str:
        return self._status

    @property
    def opcoes_banco(self) -> list:
        """Bancos carregados (sem o item em branco do Select)."""
        return list(self._opcoes_banco)

    @property
    def opcoes_schemas(self) -> list:
        """Schemas carregados como (rótulo, valor)."""
        return list(self._opcoes_schemas)

    def _servicos(self) -> ServicosInit:
        return self._app_ref.servicos

    def _form(self) -> FormularioConexao:
        return self.query_one(FormularioConexao)

    def compose(self) -> ComposeResult:
        with Horizontal(id=f"{self.papel}-colunas", classes="colunas-conexao"):
            with Vertical(id=f"{self.papel}-col-config", classes="col-config"):
                yield FormularioConexao(self.papel)
            with Vertical(id=f"{self.papel}-col-selecao", classes="col-selecao"):
                yield Label(t("Banco e schema"))
                yield Label(t("Banco de dados"))
                yield Select([], prompt=t("Carregue as listas..."), id=f"{self.papel}-banco")
                with Horizontal(classes="botoes-container"):
                    yield Button(t("Carregar lista"), id=f"{self.papel}-btn-carregar")
                    yield Button(t("Adicionar"), id=f"{self.papel}-btn-adicionar")
                yield DataTable(id=f"{self.papel}-tabela-bancos", classes="tabela-conexoes")
                yield Label(t("Schema"))
                yield Select([], prompt=t("Carregue as listas..."), id=f"{self.papel}-schema")
                with Horizontal(classes="botoes-container"):
                    yield Button(t("Carregar schemas"), id=f"{self.papel}-btn-carregar-schemas")
                    yield Button(t("Adicionar"), id=f"{self.papel}-btn-adicionar-schema")
                yield DataTable(id=f"{self.papel}-tabela-schemas", classes="tabela-conexoes")
                yield Static("", id=f"{self.papel}-status-listas", classes="status-listas")
                if self.papel == "destino":
                    yield Label(t("Criar banco/schema no destino"))
                    yield Input(placeholder=t("Nome do novo banco"), id="destino-novo-banco")
                    yield Button(t("Criar banco"), id="destino-btn-criar-banco")
                    yield Input(placeholder=t("Nome do novo schema"), id="destino-novo-schema")
                    yield Button(t("Criar schema"), id="destino-btn-criar-schema")

    def on_mount(self) -> None:
        for sufixo, rotulo in (("bancos", t("Banco")), ("schemas", t("Schema"))):
            self.query_one(f"#{self.papel}-tabela-{sufixo}", DataTable).add_column(t(rotulo))
        self._dividir_colunas()

    def on_resize(self, event) -> None:
        del event
        self._dividir_colunas()

    def _dividir_colunas(self) -> None:
        """Colunas fixas dividindo o espaço disponível (uma por tabela aqui)."""
        for sufixo in ("bancos", "schemas"):
            try:
                tabela = self.query_one(f"#{self.papel}-tabela-{sufixo}", DataTable)
            except Exception:
                continue
            colunas = list(tabela.columns.values())
            if not colunas:
                continue
            try:
                disponivel = tabela.scrollable_content_region.width
            except Exception:
                disponivel = 0
            largura = max(disponivel // len(colunas), 8)
            for coluna in colunas:
                coluna.width = largura

    def _avisar(self, texto: str) -> None:
        self._status = texto
        try:
            self.query_one(f"#{self.papel}-status-listas", Static).update(texto)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        clicado = event.button.id or ""
        if clicado == f"{self.papel}-btn-carregar":
            self.carregar()
        elif clicado == f"{self.papel}-btn-adicionar":
            self.adicionar_banco()
        elif clicado == f"{self.papel}-btn-carregar-schemas":
            self.carregar_schemas()
        elif clicado == f"{self.papel}-btn-adicionar-schema":
            self.adicionar_schema()
        elif clicado == f"{self.papel}-btn-criar-banco":
            self._app().run_worker(self._criar("banco"))
        elif clicado == f"{self.papel}-btn-criar-schema":
            self._app().run_worker(self._criar("schema"))

    def action_carregar(self) -> None:
        """F5: carrega bancos (o mesmo do botão)."""
        self.carregar()

    def action_testar(self) -> None:
        """Ctrl+T: testa a conexão do form."""
        self._form().testar()

    def carregar(self) -> None:
        self._avisar(t("Carregando..."))
        self._app().run_worker(self._carregar_listas())

    def carregar_schemas(self) -> None:
        """Carrega schemas dos bancos adicionados (botão explícito)."""
        self._avisar(t("Carregando..."))
        self._app().run_worker(self._carregar_schemas())

    def adicionar_banco(self) -> None:
        """Salva o banco selecionado na tabela de adicionados."""
        banco = self._valor(f"#{self.papel}-banco")
        if not banco:
            self._avisar(t("Selecione um banco antes de adicionar."))
            return
        if banco in self._bancos:
            self._avisar(t("'{nome}' já adicionado.", nome=banco))
            return
        self._bancos.append(banco)
        self.query_one(f"#{self.papel}-tabela-bancos", DataTable).add_row(banco)
        self._avisar("")

    def adicionar_schema(self) -> None:
        """Salva o schema selecionado na tabela de adicionados."""
        schema = self._valor(f"#{self.papel}-schema")
        if not schema:
            self._avisar(t("Selecione um schema antes de adicionar."))
            return
        if schema in self._schemas:
            self._avisar(t("'{nome}' já adicionado.", nome=schema))
            return
        self._schemas.append(schema)
        self.query_one(f"#{self.papel}-tabela-schemas", DataTable).add_row(schema)
        self._avisar("")

    def _credenciais_atuais(self):
        cfg = self._form().ler_config()
        erros = cfg.validar()
        if erros:
            return None, None, erros[0]
        adapter = adapter_por_tipo(cfg.tipo)
        if adapter is None:
            return None, None, t("Tipo de SGBD desconhecido.")
        return adapter, cfg.para_credenciais(), ""

    async def _carregar_listas(self) -> None:
        adapter, cred, erro = self._credenciais_atuais()
        if erro:
            self._avisar(erro)
            return
        try:
            bancos = await asyncio.to_thread(self._servicos().listar_bancos, adapter, cred)
        except Exception as exc:
            self._avisar(str(exc))
            return
        self.query_one(f"#{self.papel}-banco", Select).set_options([(b, b) for b in bancos])
        self._opcoes_banco = list(bancos)
        if self._form().ler_config().tipo in TIPOS_SCHEMA_IGUAL_A_BANCO:
            self.query_one(f"#{self.papel}-schema", Select).set_options([])
        self._avisar(t("Escolha o banco para listar os schemas."))

    def on_select_changed(self, event: Select.Changed) -> None:
        banco = texto_de_select(event.value)
        if event.select.id == f"{self.papel}-banco" and banco:
            if self._form().ler_config().tipo in TIPOS_SCHEMA_IGUAL_A_BANCO:
                escolha = self.query_one(f"#{self.papel}-schema", Select)
                escolha.set_options([(banco, banco)])
                escolha.value = banco
            else:
                self._app().run_worker(self._carregar_schemas(banco))

    async def _carregar_schemas(self, banco: Optional[str] = None) -> None:
        """Schemas dos bancos adicionados; sem adicionados, do banco dado/selecionado.

        O rótulo leva o banco (``db.schema``) e o valor é o schema puro —
        o estado continua guardando um schema só, como sempre.
        """
        alvos = list(self._bancos)
        if not alvos:
            unico = banco or self._valor(f"#{self.papel}-banco")
            alvos = [unico] if unico else []
        if not alvos:
            self._avisar(t("Adicione bancos antes de carregar os schemas."))
            return
        adapter, cred, erro = self._credenciais_atuais()
        if erro:
            self._avisar(erro)
            return
        opcoes = []
        vistos = set()
        for alvo in alvos:
            cred_alvo = {**cred, "database": alvo}
            try:
                schemas = await asyncio.to_thread(
                    self._servicos().listar_schemas, adapter, cred_alvo
                )
            except Exception as exc:
                self._avisar(str(exc))
                return
            for schema in schemas:
                if schema not in vistos:
                    vistos.add(schema)
                    opcoes.append((f"{alvo}.{schema}", schema))
        self.query_one(f"#{self.papel}-schema", Select).set_options(opcoes)
        self._opcoes_schemas = list(opcoes)
        self._avisar("")

    async def _criar(self, o_que: str) -> None:
        campo = f"#{self.papel}-novo-{o_que}"
        nome = self.query_one(campo, Input).value.strip()
        if not nome:
            self._avisar(t("Informe o nome para criar."))
            return
        adapter, cred, erro = self._credenciais_atuais()
        if erro:
            self._avisar(erro)
            return
        servico = self._servicos().criar_banco if o_que == "banco" else self._servicos().criar_schema
        try:
            await asyncio.to_thread(servico, adapter, cred, nome)
        except Exception as exc:
            self._avisar(str(exc))
            return
        await self._carregar_listas()

    def sincronizar_estado(self) -> None:
        estado = self._app_ref.estado
        cfg = self._form().ler_config()
        banco = self._valor(f"#{self.papel}-banco")
        schema = self._valor(f"#{self.papel}-schema")
        if self.papel == "origem":
            estado.origem = cfg
            estado.origem_database = banco
            estado.origem_schema = schema
            estado.origem_bancos = _unir(estado.origem_bancos, self._bancos)
            estado.origem_schemas = _unir(estado.origem_schemas, self._schemas)
        else:
            estado.destino = cfg
            estado.destino_database = banco
            estado.destino_schema = schema
            estado.destino_bancos = _unir(estado.destino_bancos, self._bancos)
            estado.destino_schemas = _unir(estado.destino_schemas, self._schemas)

    def _valor(self, seletor: str) -> str:
        try:
            valor = self.query_one(seletor, Select).value
        except Exception:
            return ""
        return texto_de_select(valor)

    def atualizar(self) -> None:
        """Reconstrói as tabelas a partir do estado (revisita sem perder)."""
        estado = self._app_ref.estado
        if self.papel == "origem":
            self._bancos = list(estado.origem_bancos)
            self._schemas = list(estado.origem_schemas)
        else:
            self._bancos = list(estado.destino_bancos)
            self._schemas = list(estado.destino_schemas)
        self._desenhar_tabelas()

    def _desenhar_tabelas(self) -> None:
        for sufixo, itens in (("bancos", self._bancos), ("schemas", self._schemas)):
            try:
                tabela = self.query_one(f"#{self.papel}-tabela-{sufixo}", DataTable)
            except Exception:
                continue
            tabela.clear()
            for item in itens:
                tabela.add_row(item)
        self._dividir_colunas()


class TelaSchemas(_Tela):
    """Modo dos schemas: automático (escolha de tabelas) ou manual (schema)."""

    BINDINGS = [Binding("f5", "carregar", "Carregar")]

    def __init__(self, app_ref: "InitApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "tela-schemas"
        self._app_ref = app_ref
        self.painel = None
        self._status = ""

    def atalhos(self) -> list:
        return [("F5", t("Carregar"))]

    def compose(self) -> ComposeResult:
        yield Label(t("Como deseja configurar os schemas das tabelas?"))
        yield Select(
            [(t("Gerar automaticamente a partir do banco de origem"), MODO_AUTO),
             (t("Configurar manualmente (gerar exemplos)"), MODO_MANUAL)],
            value=self._app_ref.estado.modo_schemas,
            id="schemas-modo",
        )
        with Vertical(id="schemas-auto-bloco"):
            yield Button(t("Carregar tabelas da origem"), id="schemas-btn-carregar")
            yield Vertical(id="schemas-painel-slot")
        with Vertical(id="schemas-manual-bloco"):
            yield Label(t("Schema de origem (modo manual)"))
            yield Select([], prompt=t("Carregue..."), id="schemas-origem-schema")
            yield Button(t("Carregar schemas"), id="schemas-btn-carregar-schema")
        yield Static("", id="schemas-status", classes="status-listas")

    def on_mount(self) -> None:
        self._alternar_blocos(self._app_ref.estado.modo_schemas)

    def _alternar_blocos(self, modo: str) -> None:
        try:
            self.query_one("#schemas-auto-bloco").display = modo == MODO_AUTO
            self.query_one("#schemas-manual-bloco").display = modo == MODO_MANUAL
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        modo = texto_de_select(event.value)
        if event.select.id == "schemas-modo" and modo:
            self._app_ref.estado.modo_schemas = modo
            self._alternar_blocos(modo)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        clicado = event.button.id or ""
        if clicado == "schemas-btn-carregar":
            self.carregar()
        elif clicado == "schemas-btn-carregar-schema":
            self._app().run_worker(self._carregar_schemas_origem())

    def action_carregar(self) -> None:
        """F5: carrega tabelas (auto) ou schemas (manual), conforme o modo."""
        self.carregar()

    def carregar(self) -> None:
        if self._app_ref.estado.modo_schemas == MODO_MANUAL:
            self._app().run_worker(self._carregar_schemas_origem())
            return
        self._avisar(t("Carregando..."))
        self._app().run_worker(self._carregar_tabelas())

    def _avisar(self, texto: str) -> None:
        self._status = texto
        try:
            self.query_one("#schemas-status", Static).update(texto)
        except Exception:
            pass

    async def _carregar_tabelas(self) -> None:
        self._app()._sincronizar_tudo()
        estado = self._app_ref.estado
        erros = estado.origem.validar()
        if erros or not estado.origem_database:
            self._avisar(t("Complete a origem antes (conexão e banco)."))
            return
        adapter = adapter_por_tipo(estado.origem.tipo)
        cred = {**estado.origem.para_credenciais(), "database": estado.origem_database}
        try:
            tabelas = await asyncio.to_thread(
                self._app_ref.servicos.carregar_tabelas, adapter, cred
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        if not tabelas:
            self._avisar(t("Nenhuma tabela encontrada no banco de origem."))
            return
        escolhas = escolhas_de_tabelas(tabelas, self._app().project_dir_previsto())
        modelo = ModeloSelecao(escolhas, modo=MULTIPLA)
        slot = self.query_one("#schemas-painel-slot", Vertical)
        await slot.remove_children()
        self.painel = PainelSelecao(
            pergunta=t("Selecione as tabelas para gerar os schemas:"),
            modelo=modelo,
            instrucao=t("espaço marca, a marca todas, l limpa, / filtra"),
        )
        await slot.mount(self.painel)
        self.painel.focus()
        self._avisar("")

    async def _carregar_schemas_origem(self) -> None:
        self._app()._sincronizar_tudo()
        estado = self._app_ref.estado
        erros = estado.origem.validar()
        if erros or not estado.origem_database:
            self._avisar(t("Complete a origem antes (conexão e banco)."))
            return
        adapter = adapter_por_tipo(estado.origem.tipo)
        cred = {**estado.origem.para_credenciais(), "database": estado.origem_database}
        try:
            schemas = await asyncio.to_thread(
                self._app_ref.servicos.listar_schemas, adapter, cred
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self.query_one("#schemas-origem-schema", Select).set_options([(s, s) for s in schemas])
        self._avisar("")

    def sincronizar_estado(self) -> None:
        estado = self._app_ref.estado
        try:
            modo = texto_de_select(self.query_one("#schemas-modo", Select).value)
            if modo:
                estado.modo_schemas = modo
        except Exception:
            pass
        if estado.modo_schemas == MODO_AUTO and self.painel is not None:
            estado.tabelas_escolhidas = [
                {"schema": v.get("schema", ""), "table": v.get("table", "")}
                for v in self.painel.modelo.selecionados()
            ]
        elif estado.modo_schemas == MODO_MANUAL:
            try:
                valor = texto_de_select(self.query_one("#schemas-origem-schema", Select).value)
                estado.schema_origem_manual = valor
            except Exception:
                pass

    def atualizar(self) -> None:
        pass


class TelaOpcoes(_Tela):
    """Schedules, DDL e Dagster: três sim/não do final do init."""

    def __init__(self, app_ref: "InitApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "tela-opcoes"
        self._app_ref = app_ref

    def compose(self) -> ComposeResult:
        yield Label(t("Deseja gerenciar os schedules automaticamente?"))
        yield Select([(t("Sim"), "sim"), (t("Não"), "nao")], value="sim", id="op-schedules")
        yield Label(t("Deseja aplicar o DDL no banco de destino?"))
        yield Select(
            [(t("Aplicar agora no banco de destino"), "aplicar"),
             (t("Apenas gerar o DDL (aplicar depois)"), "gerar")],
            value="gerar",
            id="op-ddl",
        )
        yield Label(t("Deseja subir o servidor Dagster ao concluir?"))
        yield Select([(t("Não"), "nao"), (t("Sim"), "sim")], value="nao", id="op-dagster")
        yield Label(t("Onde guardar as conexões?"))
        yield Select(
            [(".env", "env"), ("SQLite", "sqlite"), ("YAML", "yml")],
            value="env",
            id="op-armazenamento",
        )

    def _opcao(self, seletor: str, padrao: str) -> str:
        try:
            valor = texto_de_select(self.query_one(seletor, Select).value)
        except Exception:
            return padrao
        return valor or padrao

    def sincronizar_estado(self) -> None:
        estado = self._app_ref.estado
        estado.gerar_schedules = self._opcao("#op-schedules", "sim") == "sim"
        estado.aplicar_ddl = self._opcao("#op-ddl", "gerar") == "aplicar"
        estado.subir_dagster = self._opcao("#op-dagster", "nao") == "sim"
        armazenamento = self._opcao("#op-armazenamento", "env")
        estado.armazenamento = armazenamento if armazenamento in ARMAZENAMENTOS else "env"

    def atualizar(self) -> None:
        pass


class TelaRevisao(_Tela):
    """Resumo + Criar projeto (executa o motor com log) + saída."""

    BINDINGS = [Binding("f8", "criar", "Criar projeto")]

    def __init__(self, app_ref: "InitApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "tela-revisao"
        self._app_ref = app_ref
        self._pendencias = ""
        self._resultado = ""
        self._params = None

    def atalhos(self) -> list:
        return [("F8", t("Criar projeto"))]

    @property
    def pendencias_texto(self) -> str:
        return self._pendencias

    @property
    def resultado_texto(self) -> str:
        return self._resultado

    def compose(self) -> ComposeResult:
        yield Label(t("Revisão"))
        yield Static("", id="rev-resumo")
        yield Static("", id="rev-pendencias", classes="pendencias")
        yield Button(t("Criar projeto"), id="rev-btn-criar")
        yield RichLog(id="rev-log", highlight=False)
        yield Static("", id="rev-resultado")
        with Horizontal(id="rev-saida"):
            yield Button(t("Subir Dagster agora"), id="rev-btn-dagster")
            yield Button(t("Administrar projeto"), id="rev-btn-administrar")
            yield Button(t("Fechar"), id="rev-btn-fechar")

    def on_mount(self) -> None:
        self.query_one("#rev-saida").display = False

    def sincronizar_estado(self) -> None:
        pass

    def atualizar(self) -> None:
        self._app()._sincronizar_tudo()
        estado = self._app_ref.estado
        origem = f"{estado.origem.tipo}@{estado.origem.host}/{estado.origem_database}"
        destino = f"{estado.destino.tipo}@{estado.destino.host}/{estado.destino_database}"
        tabelas = (
            str(len(estado.tabelas_escolhidas))
            if estado.modo_schemas == MODO_AUTO
            else estado.schema_origem_manual or "—"
        )
        resumo = "\n".join([
            f"{t('Projeto')}: {estado.nome_projeto or '—'}",
            f"{t('Origem')}: {origem}",
            f"{t('Destino')}: {destino}",
            f"{t('Schemas')}: {estado.modo_schemas} ({tabelas})",
            f"Schedules: {t('Sim') if estado.gerar_schedules else t('Não')}",
            f"DDL: {t('aplicar') if estado.aplicar_ddl else t('só gerar')}",
        ])
        self._pendencias = "\n".join(estado.pendencias())
        self.query_one("#rev-resumo", Static).update(resumo)
        self.query_one("#rev-pendencias", Static).update(self._pendencias)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        clicado = event.button.id or ""
        if clicado == "rev-btn-criar":
            self.criar()
        elif clicado == "rev-btn-dagster":
            self._app().exit({"acao": "dagster", "project_dir": str(self._params.project_dir)})
        elif clicado == "rev-btn-administrar":
            self._app().exit({"acao": "administrar", "project_dir": str(self._params.project_dir)})
        elif clicado == "rev-btn-fechar":
            self._app().exit({"acao": "fechar", "project_dir": str(self._params.project_dir)})

    def action_criar(self) -> None:
        """F8: cria o projeto (o mesmo do botão)."""
        self.criar()

    def criar(self) -> None:
        self._app().run_worker(self._criar())

    def _relatar(self, mensagem: str) -> None:
        self._app().call_from_thread(self._anexar_log, mensagem)

    def _anexar_log(self, mensagem: str) -> None:
        self.query_one("#rev-log", RichLog).write(mensagem)

    def _mostrar_resultado(self, texto: str) -> None:
        self._resultado = texto
        try:
            self.query_one("#rev-resultado", Static).update(texto)
        except Exception:
            pass

    async def _criar(self) -> None:
        self._app()._sincronizar_tudo()
        estado = self._app_ref.estado
        self._pendencias = "\n".join(estado.pendencias())
        self.query_one("#rev-pendencias", Static).update(self._pendencias)
        if self._pendencias:
            return
        botao = self.query_one("#rev-btn-criar", Button)
        botao.disabled = True
        try:
            self._params = self._montar_params(estado)
            resultado = await asyncio.to_thread(
                self._app_ref.servicos.executar, self._params, self._relatar, True
            )
        except Exception as exc:
            self._mostrar_resultado(f"{t('Falha ao criar o projeto')}: {exc}")
            botao.disabled = False
            return
        self._mostrar_resultado(
            f"{t('Projeto criado em')}: {resultado.project_dir} "
            f"({resultado.schemas_gerados} schema(s))"
        )
        self.query_one("#rev-saida").display = True
        botao.disabled = False

    def _montar_params(self, estado: EstadoInit):
        from conduto.init_exec import ParametrosInit

        origem = {
            **estado.origem.para_credenciais(),
            "database": estado.origem_database,
            "schema": estado.origem_schema,
        }
        destino = {
            **estado.destino.para_credenciais(),
            "database": estado.destino_database,
            "schema": estado.destino_schema,
        }
        return ParametrosInit(
            project_dir=self._app().project_dir_previsto(),
            nome_projeto=estado.nome_projeto.strip(),
            origem=origem,
            destino=destino,
            gerar_automatico=estado.modo_schemas == MODO_AUTO,
            tabelas=list(estado.tabelas_escolhidas),
            gerar_schedules=estado.gerar_schedules,
            aplicar_ddl=estado.aplicar_ddl,
            armazenamento=estado.armazenamento,
        )


class InitApp(App):
    """Painel do `conduto init`: menu lateral + formulários por etapa."""

    CSS = (
        CSS_TEMA
        + """
    .app-container { height: 100%; }
    ListView { width: 26; border-right: solid $cor-borda; }
    ContentSwitcher { width: 1fr; padding: 1; }

    #tela-origem, #tela-destino { height: 1fr; }
    /* Origem/destino em duas colunas: config à esquerda, seleção à direita. */
    .colunas-conexao { height: auto; }
    .col-config, .col-selecao { width: 1fr; height: auto; padding: 0 1; }
    .col-selecao Label:first-child { text-style: bold; color: $cor-titulo; padding-bottom: 1; }
    /* No init a tabela do form é um resumo: altura fixa para o resto caber. */
    #tela-origem .tabela-conexoes, #tela-destino .tabela-conexoes { height: 6; }
    .status-listas { height: auto; padding: 1 0 0 0; color: $status-neutro; }
    .pendencias { height: auto; padding: 1 0 0 0; color: $status-aviso; }
    #schemas-painel-slot { height: 12; }
    #rev-log { height: 10; margin-top: 1; border: solid $cor-borda; }
    #rev-resultado { height: auto; padding: 1 0 0 0; color: $status-ok; }
    #rev-saida { height: auto; margin-top: 1; }
    #rev-saida Button { margin-right: 2; }
    """
    )

    def __init__(
        self,
        project_name: Optional[str] = None,
        em_projeto_uv: bool = False,
        servicos: Optional[ServicosInit] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.servicos = servicos or ServicosInit()
        self.em_projeto_uv = em_projeto_uv
        self.estado = EstadoInit(nome_projeto=project_name or "")

    def project_dir_previsto(self) -> Path:
        """Onde o projeto será criado (o painel mostra "já existe" por aqui)."""
        return dir_do_projeto(self.estado.nome_projeto, self.em_projeto_uv, Path.cwd())

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="app-container"):
            yield ListView(
                ListItem(Label(t("Início")), id="menu-inicio"),
                ListItem(Label(t("Origem")), id="menu-origem"),
                ListItem(Label(t("Destino")), id="menu-destino"),
                ListItem(Label(t("Schemas")), id="menu-schemas"),
                ListItem(Label(t("Opções")), id="menu-opcoes"),
                ListItem(Label(t("Revisão")), id="menu-revisao"),
            )
            with ContentSwitcher(initial="tela-inicio"):
                yield TelaInicio(self)
                yield TelaConexao(self, "origem")
                yield TelaConexao(self, "destino")
                yield TelaSchemas(self)
                yield TelaOpcoes(self)
                yield TelaRevisao(self)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Conduto"
        self.sub_title = t("Novo projeto")
        self.query_one("#tela-inicio", TelaInicio).atualizar()

    def _telas(self) -> list:
        return [
            self.query_one("#tela-inicio", TelaInicio),
            self.query_one("#tela-origem", TelaConexao),
            self.query_one("#tela-destino", TelaConexao),
            self.query_one("#tela-schemas", TelaSchemas),
            self.query_one("#tela-opcoes", TelaOpcoes),
            self.query_one("#tela-revisao", TelaRevisao),
        ]

    def _sincronizar_tudo(self) -> None:
        for tela in self._telas():
            tela.sincronizar_estado()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        destino = TELAS.get(event.item.id or "")
        if not destino:
            return
        self._sincronizar_tudo()
        self.query_one(ContentSwitcher).current = destino
        self.query_one(f"#{destino}").atualizar()
