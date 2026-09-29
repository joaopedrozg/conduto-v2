"""Web UI do conduto: backend FastAPI que espelha a TUI sem substituí-la.

A TUI (Textual, v1.1.42 em diante) continua sendo a interface padrão do
``conduto init``. Este pacote expõe as mesmas operações via REST para o
frontend Angular em ``web/``:

- catálogo: SGBDs, teste de conexão, bancos/schemas/tabelas;
- projeto: criar (motor ``init_exec.executar_init``), resumo, DDL,
  schedules, inferir e docs (``docs_server.coletar_dados``).

Tudo aqui reutiliza as funções puras já testadas — nenhum prompt de
terminal é chamado.
"""

from conduto.web.app import app, criar_app

__all__ = ["app", "criar_app"]
