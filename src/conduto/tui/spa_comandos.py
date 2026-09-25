"""Runners internos da administração: executam e devolvem dados.

As funções de domínio imprimem no ``conduto.ui.console`` (rich prende o
stdout na construção, então ``redirect_stdout`` não pega — ver
:mod:`conduto.init_exec`). Cada runner captura essa saída e a repassa
via ``relatar``; o resumo vem no retorno e o erro vira exceção curta.
Quem chama (telas ou :class:`ServicosAdmin`) escreve log + status.
"""

from __future__ import annotations

import io
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, List, Optional

__all__ = [
    "console_capturado",
    "rodar_ddl_aplicar",
    "rodar_ddl_gerar",
    "rodar_driver",
    "rodar_inferir",
    "rodar_schedules",
]


@contextmanager
def console_capturado() -> Iterator[io.StringIO]:
    """Prende a saída rica do domínio e a devolve num buffer de texto."""
    from rich.console import Console

    from conduto import ui

    buffer = io.StringIO()
    original = ui.console._real
    ui.console._real = Console(file=buffer, width=100)
    try:
        yield buffer
    finally:
        ui.console._real = original


def _com_log(relatar: Callable[[str], None], acao: Callable[[], object]) -> object:
    """Roda ``acao`` capturando o console; despeja no log e devolve o dado."""
    with console_capturado() as buffer:
        dado = acao()
    texto = buffer.getvalue()
    if texto.strip():
        relatar(texto)
    return dado


def rodar_ddl_gerar(project_dir: Path, relatar: Callable[[str], None]) -> str:
    """Devolve o DDL (vai para o log); levanta RuntimeError sem tabelas."""
    from conduto.ddl import ddl_render

    def _gerar() -> str:
        credenciais, tipo = ddl_render.credenciais_destino(Path(project_dir))
        tabelas = ddl_render.carregar_tabelas(Path(project_dir))
        if not tabelas:
            raise RuntimeError("Nenhum schema YAML encontrado para gerar DDL.")
        return ddl_render.gerar_ddl(tabelas, tipo)

    return _com_log(relatar, _gerar)


def rodar_ddl_aplicar(project_dir: Path, relatar: Callable[[str], None]) -> int:
    """Aplica o DDL e devolve a quantidade de comandos; levanta se falhar."""
    from conduto.ddl import ddl_render

    def _aplicar() -> int:
        credenciais, tipo = ddl_render.credenciais_destino(Path(project_dir))
        tabelas = ddl_render.carregar_tabelas(Path(project_dir))
        if not tabelas:
            raise RuntimeError("Nenhum schema YAML encontrado para gerar DDL.")
        comandos = ddl_render.dividir_statement(ddl_render.gerar_ddl(tabelas, tipo))
        relatar("Aplicando DDL no banco de destino...")
        erros = ddl_render.executar_ddl(tipo, credenciais, comandos)
        if erros:
            raise RuntimeError("; ".join(str(e) for e in erros))
        return len(comandos)

    return _com_log(relatar, _aplicar)


def rodar_schedules(project_dir: Path, relatar: Callable[[str], None]) -> List[str]:
    """Regenera schedules + Dagster; devolve os nomes das tabelas."""
    from conduto.schedules import schedules_auto
    from conduto.schedules.dagster_render import garantir_config_dagster

    def _gerar() -> List[str]:
        try:
            nome = schedules_auto.nome_projeto(Path(project_dir))
        except Exception as exc:
            raise RuntimeError(f"Falha ao ler o projeto: {exc}") from exc
        tabelas = schedules_auto.gerar_schedules_automaticos(Path(project_dir), nome)
        if not garantir_config_dagster(Path(project_dir)):
            raise RuntimeError("Falha ao configurar o pyproject.toml para o dagster dev.")
        return [item["table"] for item in tabelas]

    return _com_log(relatar, _gerar)


def rodar_inferir(
    project_dir: Path, tabela: Optional[str], relatar: Callable[[str], None]
) -> List[str]:
    """Infere colunas da origem; devolve as tabelas inferidas."""
    from conduto.schemas import schemas_inferir

    def _inferir() -> List[str]:
        try:
            inferidas = schemas_inferir.inferir_colunas(Path(project_dir), tabela)
        except Exception as exc:
            raise RuntimeError(f"Falha ao inferir colunas: {exc}") from exc
        if not inferidas:
            raise RuntimeError("Nada a inferir (sem tabelas sem colunas?).")
        return list(inferidas)

    return _com_log(relatar, _inferir)


def rodar_driver(relatar: Callable[[str], None]) -> str:
    """Instala o ODBC Driver do SQL Server; devolve a mensagem oficial."""
    from conduto.database.adapters import instalar_driver_sqlserver

    def _instalar() -> str:
        ok, mensagem = instalar_driver_sqlserver()
        if not ok:
            raise RuntimeError(mensagem)
        return mensagem

    return _com_log(relatar, _instalar)
