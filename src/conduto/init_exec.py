"""Execução não-interativa do `conduto init` (o motor do painel).

O wizard legado pergunta tudo em sequência (:func:`conduto.cli._init_corpo`,
mantido como fallback sem terminal); o painel coleta tudo em formulários e
executa uma vez só aqui, com parâmetros explícitos:

- progresso via ``relatar`` (o painel espelha no log, o chamador direto ignora);
- erros como exceção (o painel exibe na tela);
- ``silenciar_console=True`` prende a saída rica das etapas num buraco, para
  a thread de execução não sujar o terminal que a TUI está desenhando.
"""

from __future__ import annotations

import io
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List

from rich.console import Console

from conduto.ddl.ddl_render import (
    carregar_tabelas,
    dividir_statement,
    executar_ddl,
    gerar_ddl,
)
from conduto.env.env_render import env_render
from conduto.project_base.gerar_project import gerar_comando_dagster, setup_uv_environment
from conduto.schemas.schemas_auto import gerar_schemas_automaticos
from conduto.schemas.schemas_render import schemas_render
from conduto.schedules.schedules_auto import gerar_schedules_automaticos
from conduto.tui.conexoes import adapter_por_tipo

__all__ = ["ParametrosInit", "ResultadoInit", "executar_init"]


@dataclass
class ParametrosInit:
    """Tudo que o painel coleta antes de criar o projeto."""

    project_dir: Path
    nome_projeto: str
    origem: Dict[str, str]
    destino: Dict[str, str]
    gerar_automatico: bool = True
    tabelas: List[Dict[str, str]] = field(default_factory=list)
    gerar_schedules: bool = True
    aplicar_ddl: bool = False
    armazenamento: str = "env"


@dataclass
class ResultadoInit:
    """Resumo do que foi criado (o painel mostra na revisão final)."""

    project_dir: Path
    env_path: Path | None
    schemas_gerados: int
    schedules: bool
    ddl_comandos: int
    ddl_aplicado: bool


@contextmanager
def _console_descartavel():
    """Prende a saída rica das etapas (o rich prende o stdout na construção).

    Todas as etapas falam pelo mesmo objeto ``conduto.ui.console``: trocar o
    ``_real`` dele (e devolver no finally) silencia tudo sem tocar no código
    das etapas. O progresso do painel passa por ``relatar``, fora daqui.
    """
    from conduto import ui

    original = ui.console._real
    ui.console._real = Console(file=io.StringIO(), width=100)
    try:
        yield
    finally:
        ui.console._real = original


def executar_init(
    params: ParametrosInit,
    relatar: Callable[[str], None] = lambda mensagem: None,
    silenciar_console: bool = False,
) -> ResultadoInit:
    """Cria o projeto ELT a partir dos parâmetros (sem perguntar nada)."""
    adapter_origem = adapter_por_tipo(params.origem.get("tipo", ""))
    if adapter_origem is None:
        raise ValueError(f"Tipo de SGBD de origem desconhecido: {params.origem.get('tipo')!r}")
    adapter_destino = adapter_por_tipo(params.destino.get("tipo", ""))
    if adapter_destino is None:
        raise ValueError(f"Tipo de SGBD de destino desconhecido: {params.destino.get('tipo')!r}")

    project_dir = Path(params.project_dir)
    contexto = {
        "project_name": params.nome_projeto,
        "origem": dict(params.origem),
        "destino": dict(params.destino),
    }
    gerados = 0
    fez_schedules = False
    ddl_comandos = 0
    ddl_aplicado = False

    _silenciar = _console_descartavel() if silenciar_console else _passar()
    with _silenciar:
        project_dir.mkdir(parents=True, exist_ok=True)
        env_path = env_render(contexto, output_dir=project_dir)
        relatar(f"Projeto em: {project_dir}")

        if params.gerar_automatico:
            relatar("Gerando schemas a partir do banco de origem...")
            schemas = sorted({t.get("schema", "") for t in params.tabelas if t.get("schema")})
            gerou = gerar_schemas_automaticos(
                project_dir,
                params.nome_projeto,
                adapter_origem,
                dict(params.origem),
                params.destino.get("schema", ""),
                selecao={"schemas": schemas, "tabelas": list(params.tabelas)},
            )
            if gerou:
                gerados = len(params.tabelas)
                relatar(f"{gerados} schema(s) gerado(s) do banco de origem.")
            else:
                relatar("Automática sem tabelas: gerando schemas de exemplo.")
                schemas_render(project_dir, contexto)
        else:
            schemas_render(project_dir, contexto)
            relatar("Schemas de exemplo gerados.")

        if params.gerar_schedules:
            relatar("Gerando schedules e código Dagster...")
            gerar_schedules_automaticos(project_dir, params.nome_projeto)
            fez_schedules = True

        if params.aplicar_ddl:
            relatar("Aplicando DDL no banco de destino...")
            tabelas_ddl = carregar_tabelas(project_dir)
            texto_ddl = gerar_ddl(tabelas_ddl, adapter_destino.tipo)
            comandos = dividir_statement(texto_ddl)
            erros = executar_ddl(adapter_destino.tipo, dict(params.destino), comandos)
            if erros:
                raise RuntimeError("; ".join(str(e) for e in erros))
            ddl_comandos = len(comandos)
            ddl_aplicado = True
            relatar(f"{ddl_comandos} comando(s) aplicado(s) no destino.")

        if env_path is not None and env_path.exists():
            relatar("Preparando o ambiente uv...")
            drivers = {adapter_origem.driver, adapter_destino.driver}
            setup_uv_environment(project_dir, drivers=drivers)
            gerar_comando_dagster(project_dir)

        if params.armazenamento != "env":
            from conduto.conexoes_store import salvar_conexoes

            # O .env acima continua valendo (runtime); aqui vai a cópia do painel.
            copia = salvar_conexoes(
                project_dir, dict(params.origem), dict(params.destino),
                backend=params.armazenamento,
            )
            relatar(f"Conexões guardadas em: {copia.name}")

    return ResultadoInit(
        project_dir=project_dir,
        env_path=env_path,
        schemas_gerados=gerados,
        schedules=fez_schedules,
        ddl_comandos=ddl_comandos,
        ddl_aplicado=ddl_aplicado,
    )


@contextmanager
def _passar():
    """Sem silenciamento: o corpo roda com a saída normal (wizard legado)."""
    yield
