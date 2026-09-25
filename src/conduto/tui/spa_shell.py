"""Casca SPA: header, menu, conteúdo, footer do conteúdo e timeline.

Um App só, dois modos: criar (telas de :mod:`conduto.tui.init_app`) e
administrar (telas de :mod:`conduto.tui.spa_admin`). O F1 abre a paleta
de comandos internos; Dagster/Docs fecham a interface e o CLI assume
no terminal de verdade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    ContentSwitcher,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from conduto import __version__
from conduto.i18n import t
from conduto.tui.init_modelo import EstadoInit
from conduto.tui.init_servicos import ServicosInit
from conduto.tui.spa_admin import ADMIN_TELAS
from conduto.tui.spa_modelo import (
    MODO_ADMINISTRAR,
    MODO_CRIAR,
    PASSO_ATUAL,
    PASSO_FEITO,
    PASSO_PENDENTE,
    PASSOS_ADMIN,
    PASSOS_CRIAR,
    AdminEstado,
    Comando,
    comandos_para,
    resumir_projeto,
    texto_timeline,
)
from conduto.tui.tema import CSS_TEMA, Status, cor

__all__ = ["BarraAtalhos", "Marca", "SpaApp", "TelaComandos", "Timeline"]


class Marca(Static):
    """Header estiloso: marca + versão + contexto (criar/administrar)."""

    def __init__(self, contexto: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "marca"
        self._texto = ""

    @property
    def marca_texto(self) -> str:
        """Texto puro da marca (nome, versão e contexto) — testável sem TTY."""
        return self._texto

    def definir(self, contexto: str) -> None:
        texto = Text()
        texto.append("◢ conduto", style=f"{cor(Status.INFO)} bold")
        texto.append(f" {__version__}", style=cor(Status.NEUTRO))
        texto.append(f"  ·  {contexto}", style=cor(Status.INFO))
        self._texto = f"conduto {__version__} · {contexto}"
        try:
            self.update(texto)
        except Exception:
            pass

    def on_mount(self) -> None:
        if not self._texto:
            self.definir("")


class BarraAtalhos(Static):
    """Footer do conteúdo: os atalhos do form ativo (não os globais)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "atalhos-conteudo"
        self._texto = ""

    @property
    def texto(self) -> str:
        return self._texto

    def definir(self, atalhos: List[Tuple[str, str]]) -> None:
        partes = [f"{tecla} {rotulo}" for tecla, rotulo in atalhos]
        self._texto = "  ·  ".join(partes)
        try:
            self.update(Text(self._texto, style=cor(Status.NEUTRO)))
        except Exception:
            pass


class Timeline(Static):
    """Entre conteúdo e footer: ✓ feito · ● atual · ○ pendente por passo."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.id = "timeline"
        self._texto = ""

    @property
    def texto(self) -> str:
        return self._texto

    def definir(self, passos: List[Tuple[str, str]]) -> None:
        desenhada = texto_timeline(passos)
        self._texto = desenhada.plain
        try:
            self.update(desenhada)
        except Exception:
            pass


class TelaComandos(Screen):
    """Paleta F1: filtra os comandos internos e executa o escolhido."""

    BINDINGS = [Binding("escape", "fechar", "Fechar", priority=True)]

    def __init__(self, comandos: List[Comando], ao_escolher: Callable[[Comando], None], **kwargs) -> None:
        super().__init__(**kwargs)
        self._todos = list(comandos)
        self._ao_escolher = ao_escolher
        self._visiveis: List[Comando] = list(comandos)

    def compose(self) -> ComposeResult:
        yield Label(t("Comandos (digite para filtrar, enter executa, esc fecha)"))
        yield Input(placeholder=t("Filtrar comandos..."), id="cmd-filtro")
        yield OptionList(id="cmd-lista")

    def on_mount(self) -> None:
        self._desenhar("")
        self.query_one("#cmd-filtro", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "cmd-filtro":
            self._desenhar(event.value)

    def _desenhar(self, filtro: str) -> None:
        consulta = (filtro or "").strip().lower()
        self._visiveis = [
            c for c in self._todos
            if not consulta or consulta in f"{c.titulo} {c.descricao}".lower()
        ]
        lista = self.query_one("#cmd-lista", OptionList)
        lista.clear_options()
        lista.add_options([
            Option(f"{c.titulo} — {c.descricao}", id=c.id) for c in self._visiveis
        ])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._escolher_indice(event.option_index)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter no filtro confirma o destacado (ou o primeiro da lista)."""
        if event.input.id != "cmd-filtro" or not self._visiveis:
            return
        lista = self.query_one("#cmd-lista", OptionList)
        destacado = lista.highlighted if lista.highlighted is not None else 0
        self._escolher_indice(destacado)

    def _escolher_indice(self, indice: int) -> None:
        if 0 <= indice < len(self._visiveis):
            comando = self._visiveis[indice]
            self.dismiss(None)
            self._ao_escolher(comando)

    def action_fechar(self) -> None:
        self.dismiss(None)


class SpaApp(App):
    """A interface do conduto: SPA com header, menu, conteúdo e timeline."""

    CSS = (
        CSS_TEMA
        + """
    #marca {
        height: 1;
        padding: 0 1;
        background: $cor-fundo-alt;
        color: $cor-titulo;
    }
    .app-container { height: 1fr; }
    #menu {
        width: 24;
        border-right: solid $cor-borda;
    }
    #conteudo { width: 1fr; height: 1fr; }
    ContentSwitcher { width: 1fr; height: 1fr; padding: 1; }
    #atalhos-conteudo {
        height: 1;
        padding: 0 1;
        background: $cor-fundo-alt;
        color: $status-neutro;
    }
    #timeline {
        height: 1;
        padding: 0 1;
        background: $cor-fundo;
        color: $status-neutro;
        border-top: solid $cor-borda;
    }
    """
    )
    BINDINGS = [
        Binding("f1", "comandos", "Comandos"),
        Binding("f2", "menu", "Menu"),
        Binding("ctrl+q", "sair", "Sair"),
    ]

    def __init__(
        self,
        modo: str = MODO_CRIAR,
        project_name: Optional[str] = None,
        em_projeto_uv: bool = False,
        project_dir: Optional[Path] = None,
        servicos: Optional[ServicosInit] = None,
        servicos_admin: Optional[object] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.modo = modo
        self.em_projeto_uv = em_projeto_uv
        #: Passos já visitados (a timeline marca "opções" ao passar por lá).
        self._visitadas: set = set()
        if modo == MODO_ADMINISTRAR:
            from conduto.tui.spa_admin import ServicosAdmin

            self.project_dir = Path(project_dir) if project_dir is not None else Path.cwd()
            self.servicos_admin = servicos_admin or ServicosAdmin()
            self.admin_estado = AdminEstado()
        else:
            self.servicos = servicos or ServicosInit()
            self.estado = EstadoInit(nome_projeto=project_name or "")

    # ------------------------------------------------------------------
    # Interface que as telas de criar esperam (igual à do InitApp)
    # ------------------------------------------------------------------

    def project_dir_previsto(self) -> Path:
        from conduto.tui.init_modelo import dir_do_projeto

        return dir_do_projeto(self.estado.nome_projeto, self.em_projeto_uv, Path.cwd())

    def _telas_criar(self) -> list:
        from conduto.tui.init_app import (
            TelaConexao,
            TelaInicio,
            TelaOpcoes,
            TelaRevisao,
            TelaSchemas,
        )

        return [
            self.query_one("#tela-inicio", TelaInicio),
            self.query_one("#tela-origem", TelaConexao),
            self.query_one("#tela-destino", TelaConexao),
            self.query_one("#tela-schemas", TelaSchemas),
            self.query_one("#tela-opcoes", TelaOpcoes),
            self.query_one("#tela-revisao", TelaRevisao),
        ]

    def _sincronizar_tudo(self) -> None:
        if self.modo != MODO_CRIAR:
            return
        for tela in self._telas_criar():
            tela.sincronizar_estado()

    # ------------------------------------------------------------------
    # Composição por modo
    # ------------------------------------------------------------------

    def _contexto(self) -> str:
        if self.modo == MODO_ADMINISTRAR:
            return f"{t('Administrar')}: {self.project_dir.name}"
        nome = self.estado.nome_projeto.strip() or "…"
        return f"{t('Criar projeto')}: {nome}"

    def _itens_menu(self) -> List[Tuple[str, str]]:
        passos = PASSOS_ADMIN if self.modo == MODO_ADMINISTRAR else PASSOS_CRIAR
        return [(f"menu-{passo}", titulo) for passo, titulo in passos]

    def compose(self) -> ComposeResult:
        yield Marca("")
        with Horizontal(classes="app-container"):
            yield ListView(
                *[ListItem(Label(t(titulo)), id=item) for item, titulo in self._itens_menu()],
                id="menu",
            )
            with Vertical(id="conteudo"):
                with ContentSwitcher(initial=self._tela_inicial()):
                    for tela in self._telas():
                        yield tela
                yield BarraAtalhos()
        yield Timeline()
        yield Footer()

    def _tela_inicial(self) -> str:
        return "tela-visao" if self.modo == MODO_ADMINISTRAR else "tela-inicio"

    def _telas(self) -> list:
        if self.modo == MODO_ADMINISTRAR:
            from conduto.tui.spa_admin import (
                TelaConexoesAdmin,
                TelaDdlAdmin,
                TelaInferirAdmin,
                TelaSchedulesAdmin,
                TelaServidoresAdmin,
                TelaVisaoGeral,
            )

            return [
                TelaVisaoGeral(self),
                TelaConexoesAdmin(self),
                TelaDdlAdmin(self),
                TelaSchedulesAdmin(self),
                TelaInferirAdmin(self),
                TelaServidoresAdmin(self),
            ]
        from conduto.tui.init_app import (
            TelaConexao,
            TelaInicio,
            TelaOpcoes,
            TelaRevisao,
            TelaSchemas,
        )

        return [
            TelaInicio(self),
            TelaConexao(self, "origem"),
            TelaConexao(self, "destino"),
            TelaSchemas(self),
            TelaOpcoes(self),
            TelaRevisao(self),
        ]

    def _mapa_telas(self) -> Dict[str, str]:
        if self.modo == MODO_ADMINISTRAR:
            return dict(ADMIN_TELAS)
        from conduto.tui.init_app import TELAS

        return dict(TELAS)

    def on_mount(self) -> None:
        self.title = "conduto"
        self.query_one("#marca", Marca).definir(self._contexto())
        self._atualizar_tela(self._tela_inicial())
        self.atualizar_cromado()

    # ------------------------------------------------------------------
    # Cromado: timeline + footer do conteúdo acompanham a tela
    # ------------------------------------------------------------------

    def _passo_da_tela(self, tela_id: str) -> str:
        return tela_id.removeprefix("tela-")

    def _passos_atuais(self, tela_id: str) -> List[Tuple[str, str]]:
        atual = self._passo_da_tela(tela_id)
        if self.modo == MODO_ADMINISTRAR:
            resumo = resumir_projeto(self.project_dir)
            saudavel = resumo.tem_env and resumo.tem_main
            prontos = {
                "visao": saudavel,
                "conexoes": self.admin_estado.conexoes_ok,
                "ddl": self.admin_estado.ddl_ok,
                "schedules": self.admin_estado.schedules_ok,
                "inferir": self.admin_estado.inferir_ok,
                "servidores": False,
            }
            return [
                (titulo, PASSO_ATUAL if passo == atual
                 else PASSO_FEITO if prontos.get(passo) else PASSO_PENDENTE)
                for passo, titulo in PASSOS_ADMIN
            ]
        estado = self.estado
        prontos_criar = {
            "inicio": bool(estado.nome_projeto.strip()),
            "origem": estado.status_origem(),
            "destino": estado.status_destino(),
            "schemas": estado.status_schemas(),
            "opcoes": "opcoes" in self._visitadas,
            "revisao": estado.pronta_para_criar(),
        }
        return [
            (t(titulo), PASSO_ATUAL if passo == atual
             else PASSO_FEITO if prontos_criar.get(passo) else PASSO_PENDENTE)
            for passo, titulo in PASSOS_CRIAR
        ]

    def _atualizar_tela(self, tela_id: str) -> None:
        tela = self.query_one(f"#{tela_id}")
        atualizar = getattr(tela, "atualizar", None)
        if callable(atualizar):
            atualizar()

    def atualizar_cromado(self) -> None:
        """Redesenha timeline + atalhos do form (chamado ao navegar e ao agir)."""
        atual = self.query_one(ContentSwitcher).current
        self.query_one("#timeline", Timeline).definir(self._passos_atuais(atual))
        tela = self.query_one(f"#{atual}")
        atalhos = list(getattr(tela, "atalhos", lambda: [])() or [])
        atalhos.append(("F1", t("Comandos")))
        self.query_one("#atalhos-conteudo", BarraAtalhos).definir(atalhos)
        if self.modo == MODO_CRIAR:
            try:
                self.query_one("#marca", Marca).definir(self._contexto())
            except Exception:
                pass

    def _mostrar(self, tela_id: str) -> None:
        self._sincronizar_tudo()
        self._visitadas.add(self._passo_da_tela(tela_id))
        self.query_one(ContentSwitcher).current = tela_id
        self._atualizar_tela(tela_id)
        self.atualizar_cromado()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        destino = self._mapa_telas().get(event.item.id or "")
        if destino:
            self._mostrar(destino)

    # ------------------------------------------------------------------
    # Ações globais: F1 paleta, F2 menu, Ctrl+Q sair
    # ------------------------------------------------------------------

    def action_comandos(self) -> None:
        self.push_screen(TelaComandos(comandos_para(self.modo), self._ao_escolher_comando))

    def _ao_escolher_comando(self, comando: Comando) -> None:
        if comando.acao == "navegar":
            self._mostrar(comando.alvo)
        elif comando.acao == "executar":
            tela_id, _, metodo = comando.alvo.partition(":")
            self._mostrar(tela_id)
            acao = getattr(self.query_one(f"#{tela_id}"), metodo, None)
            if callable(acao):
                acao()
        elif comando.acao == "sair_executar":
            self.exit({"acao": comando.alvo, "project_dir": str(self._dir_de_saida())})

    def _dir_de_saida(self) -> Path:
        if self.modo == MODO_ADMINISTRAR:
            return self.project_dir
        return self.project_dir_previsto()

    def action_menu(self) -> None:
        self.query_one("#menu", ListView).focus()

    def action_sair(self) -> None:
        self.exit(None)
