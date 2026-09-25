"""Dashboard do Conduto: menu lateral + formulários origem/destino.

Substitui o passo a passo do wizard por um painel único: o menu troca
o conteúdo (``ContentSwitcher``) e cada lado (origem/destino) é o mesmo
widget :class:`FormularioConexao`, parametrizado pelo ``papel`` — sem
duplicação de blocos origem/destino.

A regra de negócio (portas, placeholders, validação) mora em
:mod:`conduto.tui.conexoes` (pura, sem terminal); aqui só desenhamos e
ligamos os botões nela. ``testar_fn`` é injetável para os testes não
precisarem de banco de verdade; por padrão usa ``testar_conexao`` real.
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional, Tuple

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
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
    Select,
    Static,
)

from conduto.database.adapters import ADAPTERS
from conduto.database import drivers as drivers_mod
from conduto.i18n import t
from conduto.tui.conexoes import (
    OPCOES_BANCO,
    ConfigConexao,
    RegistroConexoes,
    placeholder_host_para,
    porta_padrao_para,
    precisa_porta,
    texto_de_select,
)
from conduto.tui.tema import CSS_TEMA

__all__ = ["CondutoApp", "FormularioConexao", "PaginaInicial", "TelaConexoes"]

TestarFn = Callable[[dict], Tuple[bool, str]]

#: Altura da linha tipo-do-banco + Instalar: iguala os dois widgets.
#: O `Select` estreito enrola o prompt e cresce sozinho; o `Button` do
#: tema tem altura 1 e o CSS do componente não vence o do app — por
#: isso as duas alturas são aplicadas inline no `on_mount`.
ALTURA_LINHA_TIPO = 3


def _adapter_por_tipo(tipo: str):
    for adapter in ADAPTERS.values():
        if adapter.tipo == tipo:
            return adapter
    return None


def _testar_real(credenciais: dict) -> Tuple[bool, str]:
    from conduto.database.adapters import testar_conexao

    adapter = _adapter_por_tipo(credenciais.get("tipo", ""))
    if adapter is None:
        return False, f"Tipo de SGBD desconhecido: {credenciais.get('tipo')!r}"
    return testar_conexao(adapter, credenciais)


class PaginaInicial(Static):
    """Boas-vindas (conteúdo da primeira entrada do menu)."""

    def compose(self) -> ComposeResult:
        yield Label(t("Bem-vindo ao painel do Conduto.\nSelecione uma opção no menu ao lado."))


class FormularioConexao(Static):
    """Formulário de conexão reutilizável (origem ou destino, via ``papel``).

    Ids seguem ``{papel}-...`` para os dois lados coexistirem sem colisão.
    A tabela começa vazia — linhas vêm de ``registros`` via Salvar.
    """

    # Só layout (sem variáveis: o CSS do componente não as enxerga).
    DEFAULT_CSS = f"""
    .tipo-linha {{
        height: auto;
    }}
    .tipo-linha Select {{
        width: 1fr;
        height: {ALTURA_LINHA_TIPO};
    }}
    .tipo-linha Button {{
        width: auto;
        margin-left: 2;
    }}
    """

    def __init__(
        self,
        papel: str = "origem",
        *,
        testar_fn: Optional[TestarFn] = None,
        registros: Optional[RegistroConexoes] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.papel = papel
        self.id = f"form-{papel}"
        self._testar_fn: TestarFn = testar_fn or _testar_real
        self.registros = registros if registros is not None else RegistroConexoes()
        self._status_texto = ""
        #: Pergunta de driver em vigor (para limpar o status ao trocar de SGBD).
        self._driver_pergunta = ""

    @property
    def status_texto(self) -> str:
        """Último status (texto puro, sem cor) — útil para testes e logs."""
        return self._status_texto

    def compose(self) -> ComposeResult:
        titulo = (
            t("Configuração de Banco de Dados DE ORIGEM")
            if self.papel == "origem"
            else t("Configuração de Banco de Dados DE DESTINO")
        )
        yield Label(titulo)
        with Horizontal(classes="tipo-linha"):
            yield Select(OPCOES_BANCO, prompt=t("Selecione o Tipo de Banco"), id=f"{self.papel}-tipo")
            yield Button(t("Instalar"), id=f"{self.papel}-btn-driver")
        yield Input(placeholder=placeholder_host_para("postgresql"), id=f"{self.papel}-host")
        yield Input(placeholder=t("Porta (ex: 5432)"), id=f"{self.papel}-porta")
        yield Input(placeholder=t("Usuário"), id=f"{self.papel}-user")
        yield Input(placeholder=t("Senha"), password=True, id=f"{self.papel}-senha")
        with Horizontal(classes="botoes-container"):
            yield Button(t("Testar Conexão"), classes="btn-testar", id=f"{self.papel}-btn-testar")
            yield Button(t("Salvar"), classes="btn-salvar", id=f"{self.papel}-btn-salvar")
        yield Static("", id=f"{self.papel}-status", classes="status-conexao")
        yield DataTable(id=f"tabela-{self.papel}", classes="tabela-conexoes")

    def on_mount(self) -> None:
        tabela = self.query_one(DataTable)
        tabela.add_columns(t("Banco"), t("Host"), t("Usuário"))
        # Sem SGBD escolhido não há o que instalar: o botão nasce desligado.
        # Altura inline: o CSS do componente não vence o `Button` do tema.
        botao = self.query_one(f"#{self.papel}-btn-driver", Button)
        botao.disabled = True
        botao.styles.height = ALTURA_LINHA_TIPO

    def ler_config(self) -> ConfigConexao:
        """Lê os campos para o modelo puro (sem tocar em banco)."""
        tipo = texto_de_select(self.query_one(f"#{self.papel}-tipo", Select).value)
        return ConfigConexao(
            tipo=tipo,
            host=self.query_one(f"#{self.papel}-host", Input).value,
            porta=self.query_one(f"#{self.papel}-porta", Input).value,
            user=self.query_one(f"#{self.papel}-user", Input).value,
            senha=self.query_one(f"#{self.papel}-senha", Input).value,
        )

    def _definir_status(self, texto: str) -> None:
        self._status_texto = texto
        try:
            self.query_one(f"#{self.papel}-status", Static).update(texto)
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        tipo = texto_de_select(event.value)
        if tipo:
            porta = self.query_one(f"#{self.papel}-porta", Input)
            host = self.query_one(f"#{self.papel}-host", Input)
            porta.value = porta_padrao_para(tipo)
            porta.disabled = not precisa_porta(tipo)
            host.placeholder = placeholder_host_para(tipo)
        self._oferecer_driver(tipo)

    def _oferecer_driver(self, tipo: str) -> None:
        """Pergunta no status e liga o botão quando falta driver do SGBD.

        Sem mexer no layout (só texto + ``disabled``): mostrar/esconder
        caixas quebrava o posicionamento dos botões no Textual.
        """
        try:
            faltantes = drivers_mod.drivers_faltantes(tipo) if tipo else ()
        except Exception:
            faltantes = ()
        self.query_one(f"#{self.papel}-btn-driver", Button).disabled = not faltantes
        if not faltantes:
            if self._status_texto == self._driver_pergunta:
                self._definir_status("")
            self._driver_pergunta = ""
            return
        self._driver_pergunta = t(
            "Driver ausente ({modulos}): instalar agora?", modulos=", ".join(faltantes)
        )
        self._definir_status(self._driver_pergunta)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self.papel}-btn-testar":
            self.testar()
        elif event.button.id == f"{self.papel}-btn-salvar":
            self.salvar()
        elif event.button.id == f"{self.papel}-btn-driver":
            self._instalar_agora()

    def _instalar_agora(self) -> None:
        """Instala em worker (o pip bloqueia) com status de progresso."""
        tipo = texto_de_select(self.query_one(f"#{self.papel}-tipo", Select).value)
        if not tipo:
            return
        self.query_one(f"#{self.papel}-btn-driver", Button).disabled = True
        self._definir_status(t("Instalando dependências..."))
        self.app.run_worker(self._instalar_driver(tipo))

    async def _instalar_driver(self, tipo: str) -> None:
        ok, mensagem = await asyncio.to_thread(drivers_mod.instalar_drivers, tipo)
        try:
            restantes = drivers_mod.drivers_faltantes(tipo)
        except Exception:
            restantes = ()
        self.query_one(f"#{self.papel}-btn-driver", Button).disabled = not restantes
        self._driver_pergunta = ""
        self._definir_status(mensagem)

    def testar(self) -> None:
        """Testa a conexão e mostra o resultado no status."""
        cfg = self.ler_config()
        erros = cfg.validar()
        if erros:
            self._definir_status(erros[0])
            return
        ok, mensagem = self._testar_fn(cfg.para_credenciais())
        if ok:
            self._definir_status(t("Conexão testada com sucesso!"))
        else:
            self._definir_status(f"{t('Falha na conexão')}: {mensagem}")

    def salvar(self) -> None:
        """Valida, guarda no registro e adiciona a linha na tabela."""
        cfg = self.ler_config()
        erros = cfg.validar()
        if erros:
            self._definir_status(erros[0])
            return
        self.registros.adicionar(cfg)
        adapter = _adapter_por_tipo(cfg.tipo)
        rotulo = adapter.nome if adapter is not None else cfg.tipo
        self.query_one(DataTable).add_row(rotulo, cfg.host, cfg.user or "—")
        self._definir_status(t("Conexão salva."))


class TelaConexoes(Static):
    """Lado a lado origem/destino (conteúdo da segunda entrada do menu)."""

    def __init__(self, app_ref: "CondutoApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self._app_ref = app_ref

    def compose(self) -> ComposeResult:
        with Horizontal(classes="forms-wrapper"):
            with Vertical(classes="form-container"):
                yield FormularioConexao(
                    "origem",
                    testar_fn=self._app_ref._testar_fn,
                    registros=self._app_ref.registros,
                )
            with Vertical(classes="form-container"):
                yield FormularioConexao(
                    "destino",
                    testar_fn=self._app_ref._testar_fn,
                    registros=self._app_ref.registros,
                )


class CondutoApp(App):
    """Painel do Conduto: menu lateral + conteúdo trocável."""

    CSS = (
        CSS_TEMA
        + """
    .app-container { height: 100%; }
    ListView { width: 24; border-right: solid $cor-borda; }
    ContentSwitcher { width: 1fr; padding: 1; }

    .forms-wrapper { height: 1fr; }
    .form-container { width: 1fr; padding: 0 2; }
    .form-container Label { padding-bottom: 1; text-style: bold; color: $cor-titulo; }

    Select { margin-bottom: 1; }
    Input { margin-bottom: 1; }

    .botoes-container {
        height: auto;
        margin-top: 1;
        align: right middle;
    }
    .botoes-container Button { margin-left: 2; }

    .btn-salvar { background: $cor-primaria; color: $cor-titulo; }

    .status-conexao { height: auto; padding: 1 0 0 0; color: $status-neutro; }

    .tabela-conexoes { margin-top: 1; height: 1fr; }
    """
    )

    def __init__(self, testar_fn: Optional[TestarFn] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._testar_fn: TestarFn = testar_fn or _testar_real
        self.registros = RegistroConexoes()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="app-container"):
            yield ListView(
                ListItem(Label(t("Início")), id="menu-inicio"),
                ListItem(Label(t("Configurar conexões")), id="menu-conexoes"),
            )
            with ContentSwitcher(initial="tela-inicio"):
                yield PaginaInicial(id="tela-inicio")
                yield TelaConexoes(self, id="tela-conexoes")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Conduto"
        self.sub_title = t("Gerenciamento de Pipelines")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        switcher = self.query_one(ContentSwitcher)
        if event.item.id == "menu-inicio":
            switcher.current = "tela-inicio"
        elif event.item.id == "menu-conexoes":
            switcher.current = "tela-conexoes"
