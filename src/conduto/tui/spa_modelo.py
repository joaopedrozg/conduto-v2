"""Modelo puro da SPA: decisão de modo, timeline, comandos e resumo.

Sem Textual e sem rede — a casca (:mod:`conduto.tui.spa_shell`) só
desenha o que daqui sai. A regra de "onde estou / o que falta / o que
posso rodar" mora aqui e roda sem abrir nenhum terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.text import Text

from conduto.tui.tema import Status, cor

__all__ = [
    "COMANDOS",
    "MODO_ADMINISTRAR",
    "MODO_CRIAR",
    "PASSO_ATUAL",
    "PASSO_FEITO",
    "PASSO_PENDENTE",
    "PASSOS_ADMIN",
    "PASSOS_CRIAR",
    "AdminEstado",
    "Comando",
    "DecisaoInit",
    "ResumoProjeto",
    "comandos_para",
    "decidir_init",
    "ler_conexoes_env",
    "resumir_projeto",
    "texto_timeline",
]

#: `init nome` fora de projeto: cria tudo do zero.
MODO_CRIAR = "criar"
#: `init .` ou `init` dentro de projeto: administra o que já existe.
MODO_ADMINISTRAR = "administrar"

#: Passo concluído (verde ✓) — no criar: etapa preenchida; no admin: ação rodada.
PASSO_FEITO = "feito"
#: Passo onde o fluxo está (azul ●).
PASSO_ATUAL = "atual"
#: Passo que ainda vai vir (cinza ○).
PASSO_PENDENTE = "pendente"

#: Etapas do modo criar, na ordem da timeline.
PASSOS_CRIAR: Tuple[Tuple[str, str], ...] = (
    ("inicio", "Início"),
    ("origem", "Origem"),
    ("destino", "Destino"),
    ("schemas", "Schemas"),
    ("opcoes", "Opções"),
    ("revisao", "Revisão"),
)

#: Telas do modo administrar, na ordem da timeline.
PASSOS_ADMIN: Tuple[Tuple[str, str], ...] = (
    ("visao", "Visão geral"),
    ("conexoes", "Conexões"),
    ("ddl", "DDL"),
    ("schedules", "Schedules"),
    ("inferir", "Inferir"),
    ("servidores", "Servidores"),
)


@dataclass
class DecisaoInit:
    """Para onde o `conduto init` vai: criar, administrar ou erro com dica."""

    modo: str  # MODO_CRIAR | MODO_ADMINISTRAR | "erro"
    usar_cwd: bool  # o diretório-alvo é o atual
    nome: Optional[str]  # nome do projeto (None = deriva da pasta)
    erro: str = ""  # preenchido quando modo == "erro"


def decidir_init(
    project_name: Optional[str],
    em_projeto_uv: bool,
    cwd_tem_main: bool,
    alvo_tem_main: bool,
) -> DecisaoInit:
    """Decide criar/administrar sem tocar em disco (só fatos já apurados).

    - ``init nome`` cria — a menos que a pasta já seja projeto (administra);
    - ``init .`` / ``init`` no projeto administra o diretório atual;
    - ``init`` em uv sem main adapta (criar sobre o atual);
    - fora de projeto sem nome, erro que ensina o comando certo.
    """
    if project_name not in (None, "", "."):
        if alvo_tem_main:
            return DecisaoInit(MODO_ADMINISTRAR, usar_cwd=False, nome=project_name)
        return DecisaoInit(MODO_CRIAR, usar_cwd=False, nome=project_name)
    if cwd_tem_main:
        return DecisaoInit(MODO_ADMINISTRAR, usar_cwd=True, nome=None)
    if em_projeto_uv:
        return DecisaoInit(MODO_CRIAR, usar_cwd=True, nome=None)
    if project_name == ".":
        return DecisaoInit(
            "erro",
            usar_cwd=True,
            nome=None,
            erro="O diretório atual não é um projeto conduto. Crie um com: conduto init meu_projeto",
        )
    return DecisaoInit(
        "erro",
        usar_cwd=True,
        nome=None,
        erro="Informe um nome de projeto: conduto init meu_projeto",
    )


#: Glifo + status de cada estado (cor é status, nunca decoração).
MARCAS_PASSO = {
    PASSO_FEITO: ("✓", Status.OK),
    PASSO_ATUAL: ("●", Status.INFO),
    PASSO_PENDENTE: ("○", Status.NEUTRO),
}


def texto_timeline(passos: List[Tuple[str, str]]) -> Text:
    """Uma linha ``✓ feito  ● atual  ○ pendente`` com as cores de status."""
    texto = Text()
    for indice, (titulo, estado) in enumerate(passos):
        marca, status = MARCAS_PASSO.get(estado, MARCAS_PASSO[PASSO_PENDENTE])
        if indice:
            texto.append("  ")
        texto.append(f"{marca} {titulo}", style=cor(status))
    return texto


@dataclass(frozen=True)
class Comando:
    """Uma entrada da paleta F1: navegar, executar com log ou sair e rodar.

    ``alvo`` é o id da tela (navegar), o id do runner (executar) ou a ação
    de saída (sair_executar: ``dagster`` / ``docs`` — precisam do terminal
    de verdade, então a interface fecha e o CLI assume).
    """

    id: str
    titulo: str
    descricao: str
    modos: Tuple[str, ...]
    acao: str  # "navegar" | "executar" | "sair_executar"
    alvo: str


COMANDOS: Tuple[Comando, ...] = (
    # --- criar: a paleta é um atalho de navegação (nada roda sem revisão) ---
    Comando("ir-inicio", "Ir para: Início", "Nome do projeto e checklist", (MODO_CRIAR,), "navegar", "tela-inicio"),
    Comando("ir-origem", "Ir para: Origem", "Conexão e banco de origem", (MODO_CRIAR,), "navegar", "tela-origem"),
    Comando("ir-destino", "Ir para: Destino", "Conexão e banco de destino", (MODO_CRIAR,), "navegar", "tela-destino"),
    Comando("ir-schemas", "Ir para: Schemas", "Modo e tabelas", (MODO_CRIAR,), "navegar", "tela-schemas"),
    Comando("ir-opcoes", "Ir para: Opções", "Schedules, DDL e Dagster", (MODO_CRIAR,), "navegar", "tela-opcoes"),
    Comando("criar-projeto", "Criar projeto", "Abre a revisão para conferir e criar", (MODO_CRIAR,), "navegar", "tela-revisao"),
    # --- administrar: navegar ou executar com log na própria tela ---
    Comando("ir-visao", "Ir para: Visão geral", "Saúde do projeto", (MODO_ADMINISTRAR,), "navegar", "tela-visao"),
    Comando("ir-conexoes", "Ir para: Conexões", "Testar e salvar origem/destino", (MODO_ADMINISTRAR,), "navegar", "tela-conexoes"),
    Comando("ir-ddl", "Ir para: DDL", "Gerar e aplicar o DDL", (MODO_ADMINISTRAR,), "navegar", "tela-ddl"),
    Comando("ir-schedules", "Ir para: Schedules", "Regenerar schedules e Dagster", (MODO_ADMINISTRAR,), "navegar", "tela-schedules"),
    Comando("ir-inferir", "Ir para: Inferir", "Inferir colunas da origem", (MODO_ADMINISTRAR,), "navegar", "tela-inferir"),
    Comando("ir-servidores", "Ir para: Servidores", "Dagster, Docs e drivers", (MODO_ADMINISTRAR,), "navegar", "tela-servidores"),
    Comando("ddl-gerar", "DDL: gerar", "Mostra o DDL dos schemas no log", (MODO_ADMINISTRAR,), "executar", "tela-ddl:gerar"),
    Comando("ddl-aplicar", "DDL: aplicar no destino", "Cria as tabelas no banco de destino", (MODO_ADMINISTRAR,), "executar", "tela-ddl:aplicar"),
    Comando("schedules-gerar", "Schedules: regenerar", "Schedules + código Dagster", (MODO_ADMINISTRAR,), "executar", "tela-schedules:regenerar"),
    Comando("inferir-todas", "Inferir colunas", "Lê as colunas do banco de origem", (MODO_ADMINISTRAR,), "executar", "tela-inferir:inferir"),
    Comando("driver-sqlserver", "Driver SQL Server: instalar", "ODBC Driver 18 (pede UAC no Windows)", (MODO_ADMINISTRAR,), "executar", "tela-servidores:driver"),
    Comando("dagster-subir", "Dagster: subir servidor", "Fecha a interface e sobe em http://localhost:3000", (MODO_ADMINISTRAR,), "sair_executar", "dagster"),
    Comando("docs-abrir", "Docs: abrir documentação", "Fecha a interface e sobe em http://localhost:8000", (MODO_ADMINISTRAR,), "sair_executar", "docs"),
)


def comandos_para(modo: str) -> List[Comando]:
    """Os comandos da paleta naquele modo, na ordem do catálogo."""
    return [c for c in COMANDOS if modo in c.modos]


@dataclass
class AdminEstado:
    """O que já foi verificado/rodado nesta sessão (alimenta a timeline)."""

    conexoes_ok: bool = False
    ddl_ok: bool = False
    schedules_ok: bool = False
    inferir_ok: bool = False


@dataclass
class ResumoProjeto:
    """Visão geral lida do disco — sem banco, sem rede."""

    nome: str
    tem_env: bool
    tem_main: bool
    tabelas: List[str] = field(default_factory=list)
    n_schemas: int = 0
    tem_dagster: bool = False
    origem_tipo: Optional[str] = None
    destino_tipo: Optional[str] = None


def resumir_projeto(project_dir: Path) -> ResumoProjeto:
    """Lê main.yml/.env/schemas e resume a saúde do projeto."""
    project_dir = Path(project_dir)
    nome = project_dir.name
    tabelas: List[str] = []
    tem_main = (project_dir / "main.yml").exists()
    if tem_main:
        try:
            import yaml

            dados = yaml.safe_load((project_dir / "main.yml").read_text(encoding="utf-8")) or {}
            nome = str(dados.get("project") or nome)
            tabelas = [
                item["path"]
                for item in dados.get("tables", [])
                if isinstance(item, dict) and item.get("path")
            ]
        except Exception:
            tabelas = []
    schemas_dir = project_dir / "schemas"
    n_schemas = len(list(schemas_dir.glob("*.yml"))) if schemas_dir.exists() else 0
    tem_env = (project_dir / ".env").exists()
    origem_tipo = destino_tipo = None
    if tem_env:
        try:
            from conduto.ddl.ddl_render import ler_env

            env = ler_env(project_dir)
            origem_tipo = env.get("DB_ORIGEM_TYPE")
            destino_tipo = env.get("DB_DESTINO_TYPE")
        except Exception:
            pass
    return ResumoProjeto(
        nome=nome,
        tem_env=tem_env,
        tem_main=tem_main,
        tabelas=tabelas,
        n_schemas=n_schemas,
        tem_dagster=(project_dir / "conduto_dagster" / "definitions.py").exists(),
        origem_tipo=origem_tipo,
        destino_tipo=destino_tipo,
    )


def ler_conexoes_env(project_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Devolve (origem, destino) do .env — espelho de ``credenciais_destino``.

    Levanta FileNotFoundError sem .env e ValueError com tipo desconhecido,
    como a leitora de destino, para o chamador tratar igual.
    """
    from conduto.conexoes_store import carregar_conexoes

    return carregar_conexoes(Path(project_dir), backend="env")
