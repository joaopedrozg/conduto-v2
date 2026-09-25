"""Modelo puro das conexões do painel (sem Textual, sem terminal).

A fonte de verdade são os :data:`conduto.database.adapters.ADAPTERS`:
opções do ``Select``, porta padrão e placeholder de host derivam do
adapter — nada de lista copiada à mão na tela (que diverge do real).

O dashboard (:mod:`conduto.tui.dashboard`) só desenha este modelo; os
testes deste módulo rodam sem abrir nenhuma TUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from conduto.database.adapters import ADAPTERS

__all__ = [
    "OPCOES_BANCO",
    "ConfigConexao",
    "RegistroConexoes",
    "adapter_por_tipo",
    "placeholder_host_para",
    "porta_padrao_para",
    "precisa_porta",
    "texto_de_select",
    "tipos_conhecidos",
]

#: (rótulo, valor) para o ``Select`` — valor é o ``tipo`` do adapter,
#: que é o que ``testar_conexao``/``.env`` esperam.
OPCOES_BANCO: List[Tuple[str, str]] = [
    (adapter.nome, adapter.tipo) for adapter in ADAPTERS.values()
]

#: Hosts que indicam caminho/URI em vez de servidor (placeholder muda).
_PLACEHOLDER_CAMINHO = "Caminho ou URI (ex: s3://bucket/dados)"
_PLACEHOLDER_HOST = "Host (ex: localhost)"


def tipos_conhecidos() -> List[str]:
    """Tipos de banco válidos (os ``tipo`` dos adapters)."""
    return [adapter.tipo for adapter in ADAPTERS.values()]


def texto_de_select(valor) -> str:
    """Normaliza valor lido de um ``Select``: só ``str`` passa.

    Os sentinelas do Textual (``BLANK``/``NULL``), ``None`` e qualquer
    outro não-str viram ``""`` — sem isso o ``str()`` de um sentinel
    (ex.: ``"Select.NULL"``) vazava como nome de banco/credencial e
    quebrava a connection string (ODBC 4060/28000).
    """
    if isinstance(valor, str):
        return valor
    return ""


def _adapter_de(tipo: str):
    for adapter in ADAPTERS.values():
        if adapter.tipo == tipo:
            return adapter
    return None


def adapter_por_tipo(tipo: str):
    """O :class:`Adapter` do tipo (``None`` se desconhecido)."""
    return _adapter_de(tipo)


def porta_padrao_para(tipo: str) -> str:
    """Porta padrão do tipo (``""`` nos embedded)."""
    adapter = _adapter_de(tipo)
    return adapter.porta_padrao if adapter is not None else ""


def precisa_porta(tipo: str) -> bool:
    """Se o tipo usa porta (embedded como duckdb/deltalake: não)."""
    return bool(porta_padrao_para(tipo))


def placeholder_host_para(tipo: str) -> str:
    """Placeholder do campo host: servidor ou caminho/URI."""
    if precisa_porta(tipo):
        return _PLACEHOLDER_HOST
    return _PLACEHOLDER_CAMINHO


@dataclass
class ConfigConexao:
    """Uma conexão origem/destino preenchida no formulário."""

    tipo: str = ""
    host: str = ""
    porta: str = ""
    user: str = ""
    senha: str = ""
    database: str = ""
    schema: str = ""

    def validar(self) -> List[str]:
        """Lista de problemas (vazia = válida)."""
        erros: List[str] = []
        if self.tipo not in tipos_conhecidos():
            erros.append(f"Tipo de SGBD desconhecido: {self.tipo!r}")
            return erros
        if not self.host.strip():
            erros.append("Host/caminho não informado.")
        if precisa_porta(self.tipo):
            porta = self.porta.strip()
            if not porta.isdigit():
                erros.append(f"Porta inválida: {self.porta!r}")
        return erros

    def para_credenciais(self) -> Dict[str, str]:
        """Dict compatível com ``testar_conexao``/``env_render``."""
        return {
            "tipo": self.tipo,
            "host": self.host,
            "port": self.porta,
            "user": self.user,
            "password": self.senha,
        }


@dataclass
class RegistroConexoes:
    """Conexões salvas no painel (alimenta as DataTables, sem mock)."""

    _itens: List[ConfigConexao] = field(default_factory=list)

    def adicionar(self, config: ConfigConexao) -> None:
        self._itens.append(config)

    def listar(self) -> List[ConfigConexao]:
        return list(self._itens)
