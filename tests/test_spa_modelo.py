"""Modelo puro da SPA: decisão de modo, timeline, comandos e resumo.

Sem Textual e sem rede — a casca (`spa_shell`) só desenha o que daqui
sai. A regra de "onde estou / o que falta / o que posso rodar" mora
aqui e é testável sem abrir nenhum terminal.
"""

from pathlib import Path

import pytest

from conduto.i18n import definir_idioma
from conduto.tui.spa_modelo import (
    COMANDOS,
    MODO_ADMINISTRAR,
    MODO_CRIAR,
    PASSO_ATUAL,
    PASSO_FEITO,
    PASSO_PENDENTE,
    comandos_para,
    decidir_init,
    ler_conexoes_env,
    resumir_projeto,
    texto_timeline,
)


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


# ---------------------------------------------------------------------------
# decidir_init: `init nome` cria, `init .`/`init` no projeto administra
# ---------------------------------------------------------------------------


def test_init_com_nome_cria_projeto_novo():
    decisao = decidir_init("demo", em_projeto_uv=False, cwd_tem_main=False, alvo_tem_main=False)
    assert decisao.modo == MODO_CRIAR
    assert decisao.usar_cwd is False
    assert decisao.nome == "demo"
    assert decisao.erro == ""


def test_init_com_nome_em_pasta_que_ja_e_projeto_administra():
    decisao = decidir_init("demo", em_projeto_uv=False, cwd_tem_main=False, alvo_tem_main=True)
    assert decisao.modo == MODO_ADMINISTRAR
    assert decisao.usar_cwd is False


def test_init_ponto_no_projeto_administra_o_atual():
    decisao = decidir_init(".", em_projeto_uv=True, cwd_tem_main=True, alvo_tem_main=True)
    assert decisao.modo == MODO_ADMINISTRAR
    assert decisao.usar_cwd is True


def test_init_sem_nome_no_projeto_administra_o_atual():
    decisao = decidir_init(None, em_projeto_uv=True, cwd_tem_main=True, alvo_tem_main=True)
    assert decisao.modo == MODO_ADMINISTRAR
    assert decisao.usar_cwd is True


def test_init_sem_nome_em_uv_sem_main_adapta_como_criar():
    decisao = decidir_init(None, em_projeto_uv=True, cwd_tem_main=False, alvo_tem_main=False)
    assert decisao.modo == MODO_CRIAR
    assert decisao.usar_cwd is True
    assert decisao.nome is None  # o chamador deriva do nome da pasta


def test_init_ponto_fora_de_projeto_erra_com_dica():
    decisao = decidir_init(".", em_projeto_uv=False, cwd_tem_main=False, alvo_tem_main=False)
    assert decisao.modo == "erro"
    assert "init meu_projeto" in decisao.erro


def test_init_sem_nome_fora_de_projeto_erra_pedindo_nome():
    decisao = decidir_init(None, em_projeto_uv=False, cwd_tem_main=False, alvo_tem_main=False)
    assert decisao.modo == "erro"
    assert "meu_projeto" in decisao.erro


# ---------------------------------------------------------------------------
# texto_timeline: ✓ feito · ● atual · ○ pendente (cor = status, sem decorar)
# ---------------------------------------------------------------------------


def test_timeline_mostra_feito_atual_e_pendente():
    texto = texto_timeline([
        ("Início", PASSO_FEITO),
        ("Origem", PASSO_ATUAL),
        ("Destino", PASSO_PENDENTE),
    ])
    assert texto.plain == "✓ Início  ● Origem  ○ Destino"


def test_timeline_tudo_pendente_no_comeco():
    texto = texto_timeline([("A", PASSO_PENDENTE), ("B", PASSO_PENDENTE)])
    assert texto.plain == "○ A  ○ B"


def test_timeline_usa_as_cores_de_status():
    from conduto.tui.tema import cor, Status

    texto = texto_timeline([("A", PASSO_FEITO), ("B", PASSO_ATUAL), ("C", PASSO_PENDENTE)])
    estilos = [span.style for span in texto.spans]
    assert cor(Status.OK) in estilos
    assert cor(Status.INFO) in estilos
    assert cor(Status.NEUTRO) in estilos


# ---------------------------------------------------------------------------
# COMANDOS: catálogo interno da paleta F1 (navegar / executar / sair)
# ---------------------------------------------------------------------------


def test_comandos_tem_ids_unicos_e_titulo():
    ids = [c.id for c in COMANDOS]
    assert len(ids) == len(set(ids))
    for comando in COMANDOS:
        assert comando.titulo.strip()
        assert comando.acao in ("navegar", "executar", "sair_executar")
        assert comando.alvo.strip()


def test_comandos_filtram_por_modo():
    criar = {c.id for c in comandos_para(MODO_CRIAR)}
    admin = {c.id for c in comandos_para(MODO_ADMINISTRAR)}
    assert "criar-projeto" in criar
    assert "criar-projeto" not in admin
    assert "ddl-gerar" in admin
    assert "ddl-gerar" not in criar
    assert "dagster-subir" in admin  # sair_executar também entra na paleta


def test_comandos_de_saida_marcam_que_fecham_a_interface():
    sair = [c for c in COMANDOS if c.acao == "sair_executar"]
    assert {c.id for c in sair} == {"dagster-subir", "docs-abrir"}


# ---------------------------------------------------------------------------
# resumir_projeto + ler_conexoes_env: visão geral sem banco
# ---------------------------------------------------------------------------

ENV_EXEMPLO = """\
DB_ORIGEM_TYPE=postgresql
DB_ORIGEM_HOST=localhost
DB_ORIGEM_PORT=5432
DB_ORIGEM_NAME=postgres
DB_ORIGEM_USER=postgres
DB_ORIGEM_PASSWORD=postgres
DB_ORIGEM_SCHEMA=public
DB_DESTINO_TYPE=duckdb
DB_DESTINO_HOST=dest.duckdb
DB_DESTINO_PORT=
DB_DESTINO_NAME=dest.duckdb
DB_DESTINO_USER=
DB_DESTINO_PASSWORD=
DB_DESTINO_SCHEMA=main
"""

MAIN_EXEMPLO = """\
version: "1.0"
project: demo
tables:
  - path: "schemas/clientes.yml"
"""


def _projeto(tmp_path: Path) -> Path:
    (tmp_path / ".env").write_text(ENV_EXEMPLO, encoding="utf-8")
    (tmp_path / "main.yml").write_text(MAIN_EXEMPLO, encoding="utf-8")
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "clientes.yml").write_text("table: clientes\ncolumns: []\n", encoding="utf-8")
    dagster = tmp_path / "conduto_dagster"
    dagster.mkdir()
    (dagster / "definitions.py").write_text("# defs\n", encoding="utf-8")
    return tmp_path


def test_resumo_le_nome_tabelas_env_e_dagster(tmp_path):
    resumo = resumir_projeto(_projeto(tmp_path))
    assert resumo.nome == "demo"
    assert resumo.tem_env is True
    assert resumo.tem_main is True
    assert resumo.tabelas == ["schemas/clientes.yml"]
    assert resumo.n_schemas == 1
    assert resumo.tem_dagster is True
    assert resumo.origem_tipo == "postgresql"
    assert resumo.destino_tipo == "duckdb"


def test_resumo_de_pasta_vazia_nao_quebra(tmp_path):
    resumo = resumir_projeto(tmp_path)
    assert resumo.nome == tmp_path.name
    assert resumo.tem_env is False
    assert resumo.tabelas == []
    assert resumo.origem_tipo is None


def test_ler_conexoes_devolve_origem_e_destino(tmp_path):
    origem, destino = ler_conexoes_env(_projeto(tmp_path))
    assert origem["tipo"] == "postgresql"
    assert origem["database"] == "postgres"
    assert origem["schema"] == "public"
    assert destino["tipo"] == "duckdb"
    assert destino["database"] == "dest.duckdb"


def test_ler_conexoes_sem_env_falha_como_o_destino():
    with pytest.raises(FileNotFoundError):
        ler_conexoes_env(Path("/caminho/que/nao/existe"))
