"""Serviços externos do painel do init, com costura para testes.

Cada campo de :class:`ServicosInit` é um chamável; o padrão fala com o
banco/execução de verdade e os testes passam lambdas. As funções reais
 Convertem qualquer falha em :class:`RuntimeError` com a mensagem — a
tela exibe sem precisar conhecer drivers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

__all__ = ["ServicosInit"]


def _bancos(adapter, credenciais: dict) -> List[str]:
    from conduto.database.admin import listar_bancos

    try:
        return list(listar_bancos(adapter, credenciais))
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _schemas(adapter, credenciais: dict) -> List[str]:
    from conduto.database.admin import listar_schemas

    try:
        return list(listar_schemas(adapter, credenciais))
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _criar_banco(adapter, credenciais: dict, nome: str) -> None:
    from conduto.database.admin import criar_banco

    try:
        criar_banco(adapter, credenciais, nome)
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _criar_schema(adapter, credenciais: dict, nome: str) -> None:
    from conduto.database.admin import criar_schema

    try:
        criar_schema(adapter, credenciais, nome)
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _tabelas(adapter, credenciais: dict) -> List[Dict[str, str]]:
    from conduto.schemas.schemas_auto import listar_tabelas_origem

    try:
        return listar_tabelas_origem(adapter, credenciais)
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def _executar(params, relatar, silenciar: bool):
    from conduto.init_exec import executar_init

    return executar_init(params, relatar=relatar, silenciar_console=silenciar)


@dataclass
class ServicosInit:
    """Costura do painel: banco e execução (mockável nos testes)."""

    listar_bancos: Callable[[Any, dict], List[str]] = field(default=_bancos)
    listar_schemas: Callable[[Any, dict], List[str]] = field(default=_schemas)
    criar_banco: Callable[[Any, dict, str], None] = field(default=_criar_banco)
    criar_schema: Callable[[Any, dict, str], None] = field(default=_criar_schema)
    carregar_tabelas: Callable[[Any, dict], List[Dict[str, str]]] = field(default=_tabelas)
    executar: Callable[..., Any] = field(default=_executar)
