"""Modelo puro das conexões do painel: sem Textual, sem terminal.

É a regra de negócio que o dashboard desenha — opções de banco, porta
padrão por tipo, placeholder de host e validação — testável sem abrir
nenhuma tela. A fonte de verdade são os ADAPTERS (não uma lista copiada
na mão, que diverge: ex. "postgres" vs "postgresql", 9000 vs 8123).
"""

from conduto.database.adapters import ADAPTERS
from conduto.tui.conexoes import (
    OPCOES_BANCO,
    ConfigConexao,
    RegistroConexoes,
    placeholder_host_para,
    porta_padrao_para,
    precisa_porta,
)


def test_opcoes_banco_espelham_os_adapters():
    tipos = {tipo for _, tipo in OPCOES_BANCO}
    assert tipos == {a.tipo for a in ADAPTERS.values()}
    # Regressão do exemplo inicial: o valor é o `tipo` ("postgresql"),
    # não o apelido ("postgres").
    assert "postgres" not in tipos
    assert "postgresql" in tipos


def test_porta_padrao_vem_do_adapter():
    for rotulo, tipo in OPCOES_BANCO:
        adapter = next(a for a in ADAPTERS.values() if a.tipo == tipo)
        assert porta_padrao_para(tipo) == adapter.porta_padrao, rotulo


def test_tipos_embedded_nao_precisam_de_porta():
    assert precisa_porta("postgresql") is True
    assert precisa_porta("mysql") is True
    assert precisa_porta("sqlserver") is True
    assert precisa_porta("clickhouse") is True
    assert precisa_porta("duckdb") is False
    assert precisa_porta("deltalake") is False
    assert porta_padrao_para("duckdb") == ""
    assert porta_padrao_para("deltalake") == ""


def test_placeholder_host_muda_para_caminho_nos_embedded():
    assert "localhost" in placeholder_host_para("postgresql").lower()
    caminho = placeholder_host_para("duckdb").lower()
    assert "s3://" in caminho or "caminho" in caminho
    assert "s3://" in placeholder_host_para("deltalake").lower()


def test_config_valida_ok():
    cfg = ConfigConexao(tipo="postgresql", host="localhost", porta="5432", user="postgres")
    assert cfg.validar() == []


def test_config_rejeita_tipo_desconhecido():
    cfg = ConfigConexao(tipo="oracle", host="h", porta="1521", user="u")
    erros = cfg.validar()
    assert any("tipo" in e.lower() or "sgbd" in e.lower() for e in erros)


def test_config_rejeita_host_vazio():
    cfg = ConfigConexao(tipo="postgresql", host="  ", porta="5432", user="u")
    assert cfg.validar() != []


def test_config_rejeita_porta_invalida_mas_aceita_vazia_nos_embedded():
    cfg = ConfigConexao(tipo="postgresql", host="h", porta="abc", user="u")
    assert cfg.validar() != []
    cfg_ok = ConfigConexao(tipo="duckdb", host="origem.duckdb", porta="", user="")
    assert cfg_ok.validar() == []


def test_para_credenciais_e_compativel_com_testar_conexao():
    cfg = ConfigConexao(
        tipo="postgresql", host="db01", porta="5432", user="app", senha="s3cr3t"
    )
    cred = cfg.para_credenciais()
    assert cred == {
        "tipo": "postgresql",
        "host": "db01",
        "port": "5432",
        "user": "app",
        "password": "s3cr3t",
    }


def test_registro_guarda_e_lista_conexoes_salvas():
    reg = RegistroConexoes()
    assert reg.listar() == []
    reg.adicionar(ConfigConexao(tipo="postgresql", host="localhost", porta="5432", user="postgres"))
    reg.adicionar(ConfigConexao(tipo="clickhouse", host="ch.local", porta="8123", user="default"))
    linhas = reg.listar()
    assert [(c.tipo, c.host, c.user) for c in linhas] == [
        ("postgresql", "localhost", "postgres"),
        ("clickhouse", "ch.local", "default"),
    ]
