"""Modelos Pydantic da Web UI (contrato com o frontend Angular)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Credenciais(BaseModel):
    tipo: str = Field(description="Tipo do SGBD: postgresql, mysql, sqlserver, clickhouse, duckdb, deltalake")
    host: str = ""
    port: str = ""
    user: str = ""
    password: str = ""
    database: str = ""
    schema_: str = Field(default="", alias="schema")

    model_config = {"populate_by_name": True}

    def para_dict(self) -> Dict[str, str]:
        return {
            "tipo": self.tipo,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "schema": self.schema_,
        }


class TabelaEscolhida(BaseModel):
    schema_: str = Field(default="", alias="schema")
    table: str = ""

    model_config = {"populate_by_name": True}


class PedidoInit(BaseModel):
    project_dir: str = Field(description="Pasta do projeto (criada se não existir)")
    nome_projeto: str = ""
    origem: Credenciais
    destino: Credenciais
    gerar_automatico: bool = True
    tabelas: List[TabelaEscolhida] = []
    gerar_schedules: bool = True
    aplicar_ddl: bool = False
    armazenamento: str = "env"
    cron_padrao: Optional[str] = Field(
        default=None,
        description="Cron aplicado ao schedule geral e das tabelas (ex.: '0 * * * *'). None = padrão.",
    )


class PedidoCatalogo(BaseModel):
    credenciais: Credenciais
    schemas: List[str] = Field(
        default_factory=list,
        description="Só tabelas destes schemas (vazio = todos).",
    )


class PedidoConexaoSalva(BaseModel):
    apelido: str = ""
    credenciais: Credenciais


class PedidoDdl(BaseModel):
    project_dir: str = "."
    aplicar: bool = False


class PedidoSchedules(BaseModel):
    project_dir: str = "."
    cron: Optional[str] = Field(
        default=None,
        description="Cron aplicado ao schedule geral e das tabelas após regenerar. None = mantém.",
    )


class PedidoDagster(BaseModel):
    project_dir: str = "."


class PedidoInferir(BaseModel):
    project_dir: str = "."
    tabela: Optional[str] = None


class PedidoDriver(BaseModel):
    tipo: str = ""
    quebrar_sistema: bool = False


def resolver_dir(project_dir: str) -> Path:
    return Path(project_dir or ".")
