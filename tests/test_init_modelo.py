"""Estado do `conduto init` em modo painel: puro, sem Textual e sem banco.

O dashboard coleta tudo em formulários e executa uma vez só no final;
este modelo diz o que falta (`pendencias`) e se já dá para criar o
projeto (`pronta_para_criar`). A execução mora em `conduto.init_exec`.
"""

from conduto.tui.conexoes import ConfigConexao
from conduto.tui.init_modelo import (
    ARMAZENAMENTOS,
    MODO_AUTO,
    MODO_MANUAL,
    EstadoInit,
    dir_do_projeto,
)


def _origem_ok(**kw):
    base = dict(tipo="postgresql", host="localhost", porta="5432", user="postgres")
    resto = dict(
        nome_projeto="demo",
        origem_database="postgres",
        origem_schema="public",
        destino_database="dest.duckdb",
        destino_schema="main",
    )
    for chave in ("modo_schemas", "tabelas_escolhidas", "schema_origem_manual"):
        if chave in kw:
            resto[chave] = kw.pop(chave)
    base.update(kw)
    return EstadoInit(
        origem=ConfigConexao(**base),
        destino=ConfigConexao(tipo="duckdb", host="dest.duckdb", porta="", user=""),
        **resto,
    )


def test_novo_estado_nao_esta_pronto_e_lista_pendencias():
    estado = EstadoInit()
    assert estado.pronta_para_criar() is False
    pendencias = estado.pendencias()
    assert any("projeto" in p.lower() for p in pendencias)
    assert any("origem" in p.lower() for p in pendencias)
    assert any("destino" in p.lower() for p in pendencias)


def test_estado_completo_manual_esta_pronto():
    estado = _origem_ok(modo_schemas=MODO_MANUAL, schema_origem_manual="public")
    assert estado.pronta_para_criar() is True
    assert estado.pendencias() == []


def test_modo_auto_exige_tabelas_escolhidas():
    estado = _origem_ok(modo_schemas=MODO_AUTO, tabelas_escolhidas=[])
    assert estado.pronta_para_criar() is False
    assert any("tabela" in p.lower() for p in estado.pendencias())
    estado.tabelas_escolhidas = [{"schema": "public", "table": "clientes"}]
    assert estado.pronta_para_criar() is True


def test_modo_manual_exige_schema_origem_quando_pede_porta():
    estado = _origem_ok(modo_schemas=MODO_MANUAL, schema_origem_manual="")
    assert estado.pronta_para_criar() is False
    # Nos tipos em que schema == banco (mysql/clickhouse/deltalake) não há o que escolher.
    estado.origem = ConfigConexao(tipo="mysql", host="h", porta="3306", user="root")
    assert estado.pronta_para_criar() is True


def test_status_por_etapa_para_o_checklist_do_inicio():
    estado = EstadoInit()
    assert estado.status_origem() is False
    assert estado.status_destino() is False
    assert estado.status_schemas() is False
    cheio = _origem_ok(modo_schemas=MODO_MANUAL, schema_origem_manual="public")
    assert cheio.status_origem() is True
    assert cheio.status_destino() is True
    assert cheio.status_schemas() is True


def test_origem_invalida_nao_marca_etapa_como_ok():
    estado = _origem_ok()
    estado.origem = ConfigConexao(tipo="postgresql", host="", porta="abc", user="u")
    assert estado.status_origem() is False
    assert any("origem" in p.lower() for p in estado.pendencias())


def test_modo_desconhecido_e_pendencia():
    estado = _origem_ok(modo_schemas="qualquer")
    assert estado.pronta_para_criar() is False
    assert any("modo" in p.lower() for p in estado.pendencias())


def test_dir_absoluto_vence_mesmo_em_projeto_uv(tmp_path):
    # Regressão: `init C:/teste` dentro do repo criava tudo no cwd.
    alvo = tmp_path / "teste"
    assert dir_do_projeto(str(alvo), em_projeto_uv=True, cwd=tmp_path) == alvo
    assert dir_do_projeto(str(alvo), em_projeto_uv=False, cwd=tmp_path) == alvo


def test_dir_relativo_mantem_o_legado(tmp_path):
    assert dir_do_projeto("demo", em_projeto_uv=False, cwd=tmp_path) == tmp_path / "demo"
    assert dir_do_projeto("demo", em_projeto_uv=True, cwd=tmp_path) == tmp_path
    assert dir_do_projeto("", em_projeto_uv=False, cwd=tmp_path) == tmp_path
    assert dir_do_projeto("  ", em_projeto_uv=True, cwd=tmp_path) == tmp_path


def test_armazenamento_padrao_e_env_e_listas_comecam_vazias():
    estado = _origem_ok()
    assert estado.armazenamento == "env"
    assert ARMAZENAMENTOS == ("env", "sqlite", "yml")
    assert estado.origem_bancos == []
    assert estado.destino_bancos == []
    assert estado.origem_schemas == []
    assert estado.destino_schemas == []


def test_armazenamento_desconhecido_e_pendencia():
    estado = _origem_ok(modo_schemas=MODO_MANUAL, schema_origem_manual="public")
    estado.armazenamento = "oracle"
    assert estado.pronta_para_criar() is False
    assert any("guardar" in p.lower() or "armazen" in p.lower() for p in estado.pendencias())
