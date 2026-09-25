"""Telas do modo administrar: saúde, conexões, DDL, schedules, inferir.

Cada tela de ação expõe um método público (`gerar`, `aplicar`,
`regenerar`, `inferir`, `instalar_driver`, `salvar`) usado pelo botão,
pelo F8 e pela paleta F1: um caminho só de execução. Serviços externos
entram por :class:`ServicosAdmin` — mockável nos testes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, RichLog, Select, Static

from conduto.i18n import t
from conduto.tui.dashboard import FormularioConexao
from conduto.tui.init_modelo import TIPOS_SCHEMA_IGUAL_A_BANCO
from conduto.tui.spa_modelo import resumir_projeto

__all__ = [
    "ADMIN_TELAS",
    "ServicosAdmin",
    "TelaConexoesAdmin",
    "TelaDdlAdmin",
    "TelaInferirAdmin",
    "TelaSchedulesAdmin",
    "TelaServidoresAdmin",
    "TelaVisaoGeral",
]

#: Menu (item) -> tela do ContentSwitcher no modo administrar.
ADMIN_TELAS = {
    "menu-visao": "tela-visao",
    "menu-conexoes": "tela-conexoes",
    "menu-ddl": "tela-ddl",
    "menu-schedules": "tela-schedules",
    "menu-inferir": "tela-inferir",
    "menu-servidores": "tela-servidores",
}


def _ler_conexoes(project_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    from conduto.conexoes_store import carregar_conexoes

    return carregar_conexoes(Path(project_dir))


def _salvar_conexoes(project_dir: Path, origem: dict, destino: dict) -> None:
    from conduto.env.env_render import env_render

    nome = resumir_projeto(Path(project_dir)).nome
    env_render({"project_name": nome, "origem": dict(origem), "destino": dict(destino)},
               output_dir=Path(project_dir))


def _ddl_texto(project_dir: Path) -> str:
    from conduto.tui.spa_comandos import rodar_ddl_gerar

    return rodar_ddl_gerar(Path(project_dir), lambda mensagem: None)


def _ddl_aplicar(project_dir: Path, relatar: Callable[[str], None]) -> int:
    from conduto.tui.spa_comandos import rodar_ddl_aplicar

    return rodar_ddl_aplicar(Path(project_dir), relatar)


def _schedules(project_dir: Path, relatar: Callable[[str], None]) -> List[str]:
    from conduto.tui.spa_comandos import rodar_schedules

    return rodar_schedules(Path(project_dir), relatar)


def _inferir(project_dir: Path, tabela: Optional[str], relatar: Callable[[str], None]) -> List[str]:
    from conduto.tui.spa_comandos import rodar_inferir

    return rodar_inferir(Path(project_dir), tabela, relatar)


def _driver(relatar: Callable[[str], None]) -> str:
    from conduto.tui.spa_comandos import rodar_driver

    return rodar_driver(relatar)


class ServicosAdmin:
    """Costura do administrar: projeto e execução (mockável nos testes)."""

    def __init__(
        self,
        ler_conexoes: Callable[[Path], Tuple[dict, dict]] = _ler_conexoes,
        salvar_conexoes: Callable[[Path, dict, dict], None] = _salvar_conexoes,
        ddl_texto: Callable[[Path], str] = _ddl_texto,
        ddl_aplicar: Callable[[Path, Callable[[str], None]], int] = _ddl_aplicar,
        schedules: Callable[[Path, Callable[[str], None]], List[str]] = _schedules,
        inferir: Callable[[Path, Optional[str], Callable[[str], None]], List[str]] = _inferir,
        driver: Callable[[Callable[[str], None]], str] = _driver,
    ) -> None:
        self.ler_conexoes = ler_conexoes
        self.salvar_conexoes = salvar_conexoes
        self.ddl_texto = ddl_texto
        self.ddl_aplicar = ddl_aplicar
        self.schedules = schedules
        self.inferir = inferir
        self.driver = driver


class _TelaAdmin(VerticalScroll):
    """Base das telas de administração (rolável, com atalhos do form)."""

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._app_ref = app_ref

    def sincronizar_estado(self) -> None:
        """Compatível com a casca (aqui nada há para sincronizar)."""

    def atualizar(self) -> None:
        """Estado -> widgets (a casca chama ao exibir a tela)."""

    def atalhos(self) -> List[Tuple[str, str]]:
        """Atalhos deste form para o footer do conteúdo."""
        return []

    def _logar(self, seletor: str, mensagem: str) -> None:
        try:
            self.query_one(seletor, RichLog).write(mensagem)
        except Exception:
            pass


class TelaVisaoGeral(_TelaAdmin):
    """Saúde do projeto lida do disco: env, tabelas, Dagster."""

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-visao"
        self._resumo = ""

    @property
    def resumo_texto(self) -> str:
        return self._resumo

    def compose(self) -> ComposeResult:
        yield Label(t("Visão geral"))
        yield Static("", id="visao-resumo")

    def on_mount(self) -> None:
        self.atualizar()

    def atualizar(self) -> None:
        resumo = resumir_projeto(self._app_ref.project_dir)
        linhas = [
            f"{t('Projeto')}: {resumo.nome}",
            f".env: {'✓' if resumo.tem_env else '○'}  main.yml: {'✓' if resumo.tem_main else '○'}",
            f"{t('Tabelas')}: {len(resumo.tabelas)}  ({', '.join(resumo.tabelas) or '—'})",
            f"schemas/: {resumo.n_schemas}  Dagster: {'✓' if resumo.tem_dagster else '○'}",
            f"{t('Origem')}: {resumo.origem_tipo or '—'}  →  {t('Destino')}: {resumo.destino_tipo or '—'}",
        ]
        self._resumo = "\n".join(linhas)
        try:
            self.query_one("#visao-resumo", Static).update(self._resumo)
        except Exception:
            pass


class TelaConexoesAdmin(_TelaAdmin):
    """Origem/destino do .env: testa nos forms e salva de volta no .env."""

    BINDINGS = [Binding("f8", "salvar", "Salvar no .env")]

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-conexoes"
        self._status = ""

    @property
    def status_texto(self) -> str:
        return self._status

    def compose(self) -> ComposeResult:
        yield FormularioConexao("origem")
        yield Label(t("Banco/schema de origem"))
        yield Input(placeholder=t("Banco de origem"), id="admin-origem-banco")
        yield Input(placeholder=t("Schema de origem"), id="admin-origem-schema")
        yield FormularioConexao("destino")
        yield Label(t("Banco/schema de destino"))
        yield Input(placeholder=t("Banco de destino"), id="admin-destino-banco")
        yield Input(placeholder=t("Schema de destino"), id="admin-destino-schema")
        yield Button(t("Salvar no .env"), id="admin-btn-salvar")
        yield Static("", id="admin-conexoes-status", classes="status-listas")

    def on_mount(self) -> None:
        try:
            origem, destino = self._app_ref.servicos_admin.ler_conexoes(self._app_ref.project_dir)
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._preencher("origem", origem)
        self._preencher("destino", destino)

    def _preencher(self, papel: str, cred: dict) -> None:
        try:
            self.query_one(f"#{papel}-tipo", Select).value = cred.get("tipo", "")
        except Exception:
            pass
        for campo, chave in (("host", "host"), ("porta", "port"), ("user", "user"), ("senha", "password")):
            try:
                self.query_one(f"#{papel}-{campo}", Input).value = cred.get(chave, "")
            except Exception:
                pass
        self.query_one(f"#admin-{papel}-banco", Input).value = cred.get("database", "")
        self.query_one(f"#admin-{papel}-schema", Input).value = cred.get("schema", "")

    def atalhos(self) -> List[Tuple[str, str]]:
        return [("F8", t("Salvar no .env"))]

    def _avisar(self, texto: str) -> None:
        self._status = texto
        try:
            self.query_one("#admin-conexoes-status", Static).update(texto)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if (event.button.id or "") == "admin-btn-salvar":
            self.salvar()

    def action_salvar(self) -> None:
        self.salvar()

    def salvar(self) -> None:
        """Valida os dois lados e reescreve o .env do projeto."""
        origem_cfg = self.query_one("#form-origem", FormularioConexao).ler_config()
        destino_cfg = self.query_one("#form-destino", FormularioConexao).ler_config()
        erros = origem_cfg.validar() + destino_cfg.validar()
        if erros:
            self._avisar(erros[0])
            return
        origem = {**origem_cfg.para_credenciais(),
                  "database": self.query_one("#admin-origem-banco", Input).value.strip(),
                  "schema": self._schema_de("origem", origem_cfg.tipo)}
        destino = {**destino_cfg.para_credenciais(),
                   "database": self.query_one("#admin-destino-banco", Input).value.strip(),
                   "schema": self.query_one("#admin-destino-schema", Input).value.strip()}
        faltando = [rot for rot, v in (("origem/database", origem["database"]),
                                       ("origem/schema", origem["schema"]),
                                       ("destino/database", destino["database"]),
                                       ("destino/schema", destino["schema"])) if not v]
        if faltando:
            self._avisar(t("Preencha: {campos}.", campos=", ".join(faltando)))
            return
        try:
            self._app_ref.servicos_admin.salvar_conexoes(self._app_ref.project_dir, origem, destino)
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._app_ref.admin_estado.conexoes_ok = True
        self._app_ref.atualizar_cromado()
        self._avisar(t("Conexões salvas no .env."))

    def _schema_de(self, papel: str, tipo: str) -> str:
        digitado = self.query_one(f"#admin-{papel}-schema", Input).value.strip()
        if digitado:
            return digitado
        if tipo in TIPOS_SCHEMA_IGUAL_A_BANCO:
            return self.query_one(f"#admin-{papel}-banco", Input).value.strip()
        return ""


class _TelaComLog(_TelaAdmin):
    """Ação + RichLog + status (DDL, schedules, inferir, driver)."""

    _seletor_log = ""
    _seletor_status = ""

    def _relatar(self, mensagem: str) -> None:
        self._app_ref.call_from_thread(self._logar, self._seletor_log, mensagem)

    def _avisar(self, texto: str) -> None:
        try:
            self.query_one(self._seletor_status, Static).update(texto)
        except Exception:
            pass

    @property
    def status_texto(self) -> str:
        try:
            conteudo = self.query_one(self._seletor_status, Static).content
            return str(conteudo)
        except Exception:
            return ""


class TelaDdlAdmin(_TelaComLog):
    """Gera o DDL no log ou aplica no destino."""

    BINDINGS = [Binding("f8", "gerar", "Gerar DDL")]

    _seletor_log = "#ddl-log"
    _seletor_status = "#ddl-status"

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-ddl"

    def compose(self) -> ComposeResult:
        yield Label(t("DDL do projeto"))
        with Horizontal():
            yield Button(t("Gerar DDL"), id="ddl-btn-gerar")
            yield Button(t("Aplicar no destino"), id="ddl-btn-aplicar")
        yield RichLog(id="ddl-log", highlight=False)
        yield Static("", id="ddl-status", classes="status-listas")

    def atalhos(self) -> List[Tuple[str, str]]:
        return [("F8", t("Gerar DDL"))]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        clicado = event.button.id or ""
        if clicado == "ddl-btn-gerar":
            self.gerar()
        elif clicado == "ddl-btn-aplicar":
            self.aplicar()

    def action_gerar(self) -> None:
        self.gerar()

    def gerar(self) -> None:
        self._app_ref.run_worker(self._gerar())

    async def _gerar(self) -> None:
        try:
            texto = await asyncio.to_thread(
                self._app_ref.servicos_admin.ddl_texto, self._app_ref.project_dir
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._logar(self._seletor_log, texto)
        from conduto.ddl.ddl_render import dividir_statement

        self._avisar(t("{qtd} comando(s) no log.", qtd=len(dividir_statement(texto))))

    def aplicar(self) -> None:
        self._app_ref.run_worker(self._aplicar())

    async def _aplicar(self) -> None:
        try:
            total = await asyncio.to_thread(
                self._app_ref.servicos_admin.ddl_aplicar, self._app_ref.project_dir, self._relatar
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._logar(self._seletor_log, t("{qtd} comando(s) aplicado(s).", qtd=total))
        self._app_ref.admin_estado.ddl_ok = True
        self._app_ref.atualizar_cromado()
        self._avisar(t("{qtd} comando(s) aplicado(s).", qtd=total))


class TelaSchedulesAdmin(_TelaComLog):
    """Regenera schedules + código Dagster."""

    BINDINGS = [Binding("f8", "regenerar", "Regenerar")]

    _seletor_log = "#sched-log"
    _seletor_status = "#sched-status"

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-schedules"

    def compose(self) -> ComposeResult:
        yield Label(t("Schedules e código Dagster"))
        yield Button(t("Regenerar schedules"), id="sched-btn-regenerar")
        yield RichLog(id="sched-log", highlight=False)
        yield Static("", id="sched-status", classes="status-listas")

    def atalhos(self) -> List[Tuple[str, str]]:
        return [("F8", t("Regenerar"))]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if (event.button.id or "") == "sched-btn-regenerar":
            self.regenerar()

    def action_regenerar(self) -> None:
        self.regenerar()

    def regenerar(self) -> None:
        self._app_ref.run_worker(self._regenerar())

    async def _regenerar(self) -> None:
        try:
            tabelas = await asyncio.to_thread(
                self._app_ref.servicos_admin.schedules, self._app_ref.project_dir, self._relatar
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._logar(self._seletor_log, t("Schedules: {nomes}.", nomes=", ".join(tabelas) or "—"))
        self._app_ref.admin_estado.schedules_ok = True
        self._app_ref.atualizar_cromado()
        self._avisar(t("Schedules regenerados."))


class TelaInferirAdmin(_TelaComLog):
    """Infere colunas da origem (todas ou uma tabela)."""

    BINDINGS = [Binding("f8", "inferir", "Inferir")]

    _seletor_log = "#inferir-log"
    _seletor_status = "#inferir-status"

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-inferir"

    def compose(self) -> ComposeResult:
        yield Label(t("Inferir colunas do banco de origem"))
        yield Input(placeholder=t("Tabela (vazio = todas sem colunas)"), id="inferir-tabela")
        yield Button(t("Inferir colunas"), id="inferir-btn")
        yield RichLog(id="inferir-log", highlight=False)
        yield Static("", id="inferir-status", classes="status-listas")

    def atalhos(self) -> List[Tuple[str, str]]:
        return [("F8", t("Inferir"))]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if (event.button.id or "") == "inferir-btn":
            self.inferir()

    def action_inferir(self) -> None:
        self.inferir()

    def inferir(self) -> None:
        self._app_ref.run_worker(self._inferir())

    async def _inferir(self) -> None:
        tabela = self.query_one("#inferir-tabela", Input).value.strip() or None
        try:
            inferidas = await asyncio.to_thread(
                self._app_ref.servicos_admin.inferir, self._app_ref.project_dir, tabela, self._relatar
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._logar(self._seletor_log, t("Inferidas: {nomes}.", nomes=", ".join(inferidas)))
        self._app_ref.admin_estado.inferir_ok = True
        self._app_ref.atualizar_cromado()
        self._avisar(t("{qtd} tabela(s) inferida(s).", qtd=len(inferidas)))


class TelaServidoresAdmin(_TelaComLog):
    """Dagster e Docs saem da interface; driver instala com log."""

    _seletor_log = "#srv-log"
    _seletor_status = "#srv-status"

    def __init__(self, app_ref: Any, **kwargs: Any) -> None:
        super().__init__(app_ref, **kwargs)
        self.id = "tela-servidores"

    def compose(self) -> ComposeResult:
        yield Label(t("Servidores e drivers"))
        yield Button(t("Subir Dagster (fecha a interface)"), id="srv-btn-dagster")
        yield Button(t("Abrir Docs (fecha a interface)"), id="srv-btn-docs")
        yield Button(t("Instalar driver SQL Server"), id="srv-btn-driver")
        yield RichLog(id="srv-log", highlight=False)
        yield Static("", id="srv-status", classes="status-listas")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        clicado = event.button.id or ""
        if clicado == "srv-btn-dagster":
            self._app_ref.exit({"acao": "dagster", "project_dir": str(self._app_ref.project_dir)})
        elif clicado == "srv-btn-docs":
            self._app_ref.exit({"acao": "docs", "project_dir": str(self._app_ref.project_dir)})
        elif clicado == "srv-btn-driver":
            self.instalar_driver()

    def instalar_driver(self) -> None:
        self._app_ref.run_worker(self._instalar_driver())

    async def _instalar_driver(self) -> None:
        try:
            mensagem = await asyncio.to_thread(
                self._app_ref.servicos_admin.driver, self._relatar
            )
        except Exception as exc:
            self._avisar(str(exc))
            return
        self._logar(self._seletor_log, mensagem)
        self._avisar(mensagem)
