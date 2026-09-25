"""Estado do `conduto init` em modo painel (puro: sem Textual, sem banco).

O dashboard coleta tudo em formulários e executa uma vez só no final
(:mod:`conduto.init_exec`); este modelo diz o que falta (`pendencias`)
e se já dá para criar o projeto (`pronta_para_criar`), além do status
por etapa para o checklist da tela inicial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from conduto.conexoes_store import BACKENDS as ARMAZENAMENTOS
from conduto.database.adapters import ADAPTERS
from conduto.tui.conexoes import ConfigConexao, precisa_porta

__all__ = [
    "ARMAZENAMENTOS",
    "MODO_AUTO",
    "MODO_MANUAL",
    "MODOS_SCHEMAS",
    "EstadoInit",
    "TIPOS_SCHEMA_IGUAL_A_BANCO",
    "dir_do_projeto",
]

#: Tipos em que o schema é o próprio banco (sem escolha de schema à parte).
TIPOS_SCHEMA_IGUAL_A_BANCO = ("mysql", "clickhouse", "deltalake")

#: Gera os schemas lendo o banco de origem (com escolha de tabelas).
MODO_AUTO = "auto"
#: Gera os schemas de exemplo (com escolha do schema de origem).
MODO_MANUAL = "manual"

MODOS_SCHEMAS = (MODO_AUTO, MODO_MANUAL)


def dir_do_projeto(nome_projeto: str, em_projeto_uv: bool, cwd: Path) -> Path:
    """Onde criar o projeto (puro: sem tocar em disco).

    Nome absoluto (``C:/teste``, ``/tmp/x``) sempre vence — foi o que o
    usuário digitou; o resto mantém o legado: em projeto uv adapta o
    atual, sem nome usa o atual, senão subpasta com o nome.
    """
    nome = (nome_projeto or "").strip()
    if nome and Path(nome).is_absolute():
        return Path(nome)
    if em_projeto_uv or not nome:
        return Path(cwd)
    return Path(cwd) / nome


@dataclass
class EstadoInit:
    """Tudo que o painel do init coleta antes de criar o projeto."""

    nome_projeto: str = ""
    origem: ConfigConexao = field(default_factory=ConfigConexao)
    origem_database: str = ""
    origem_schema: str = ""
    destino: ConfigConexao = field(default_factory=ConfigConexao)
    destino_database: str = ""
    destino_schema: str = ""
    modo_schemas: str = MODO_AUTO
    tabelas_escolhidas: List[Dict[str, str]] = field(default_factory=list)
    schema_origem_manual: str = ""
    gerar_schedules: bool = True
    aplicar_ddl: bool = False
    subir_dagster: bool = False
    armazenamento: str = "env"
    #: Bancos/schemas adicionados no painel (listas de trabalho por papel).
    origem_bancos: List[str] = field(default_factory=list)
    destino_bancos: List[str] = field(default_factory=list)
    origem_schemas: List[str] = field(default_factory=list)
    destino_schemas: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Status por etapa (checklist da tela inicial)
    # ------------------------------------------------------------------

    def status_origem(self) -> bool:
        """Conexão de origem válida + banco escolhido."""
        return not self.origem.validar() and bool(self.origem_database.strip())

    def status_destino(self) -> bool:
        """Conexão de destino válida + banco e schema escolhidos."""
        return (
            not self.destino.validar()
            and bool(self.destino_database.strip())
            and bool(self.destino_schema.strip())
        )

    def status_schemas(self) -> bool:
        """Modo válido + seleção correspondente preenchida."""
        if self.modo_schemas == MODO_AUTO:
            return bool(self.tabelas_escolhidas)
        if self.modo_schemas == MODO_MANUAL:
            return self._manual_ok()
        return False

    def _manual_ok(self) -> bool:
        if not self.origem.tipo or self.origem.tipo not in {
            a.tipo for a in ADAPTERS.values()
        }:
            return False
        if self.origem.tipo in TIPOS_SCHEMA_IGUAL_A_BANCO:
            return True
        return bool(self.schema_origem_manual.strip())

    # ------------------------------------------------------------------
    # Prontidão geral
    # ------------------------------------------------------------------

    def pendencias(self) -> List[str]:
        """O que falta para criar o projeto (vazia = pronta)."""
        pendencias: List[str] = []
        if not self.nome_projeto.strip():
            pendencias.append("Informe o nome do projeto.")
        if not self.status_origem():
            pendencias.append("Origem: teste a conexão e escolha o banco.")
        if not self.status_destino():
            pendencias.append("Destino: teste a conexão e escolha banco e schema.")
        if self.modo_schemas not in MODOS_SCHEMAS:
            pendencias.append("Schemas: escolha o modo (automático ou manual).")
        elif self.modo_schemas == MODO_AUTO and not self.tabelas_escolhidas:
            pendencias.append("Schemas: escolha ao menos uma tabela da origem.")
        elif self.modo_schemas == MODO_MANUAL and not self._manual_ok():
            pendencias.append("Schemas: escolha o schema de origem.")
        if self.armazenamento not in ARMAZENAMENTOS:
            pendencias.append("Opções: escolha onde guardar as conexões (.env, SQLite ou YAML).")
        return pendencias

    def pronta_para_criar(self) -> bool:
        """Se o botão Criar projeto pode executar."""
        return not self.pendencias()
