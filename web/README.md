# conduto web — Web UI em Angular (TUI mantida)

A TUI Textual (`conduto init`) continua sendo a interface padrão — nada nela
foi alterado. Esta pasta é a **Web UI alternativa**, em Angular 17 standalone,
falando com o backend FastAPI em `src/conduto/web/`.

## Arquitetura

```text
web/src/app/              Angular 17 standalone (criar + administrar)
  app.component.ts        casca: marca + menu + router-outlet
  app.routes.ts           /criar (wizard) e /admin (visão geral, DDL...)
  services/api.service.ts contrato TS dos endpoints /api/*
  pages/criar.component   espelha PASSOS_CRIAR da TUI
  pages/admin.component   espelha PASSOS_ADMIN da TUI
  components/conexao      form origem/destino (deriva de ADAPTERS via /api/sgbds)

src/conduto/web/          backend FastAPI (reusa init_exec, ddl, schemas...)
  app.py                  GET /api/sgbds, POST /api/conexoes/testar, /catalogo/*,
                          POST /api/projeto/init, GET resumo/docs, POST ddl/...
  esquemas.py             modelos Pydantic (contrato com o Angular)
```

## Rodando

```bash
# 1. backend (serve a API + o build Angular em web/dist, se existir)
uv sync
uv run conduto web --no-open        # http://127.0.0.1:8080 (API em /docs)

# 2. frontend em dev (proxy /api → backend)
cd web
npm install
npm start                           # http://localhost:4200

> `conduto init nome --web` abre `/criar?nome=<nome>&dir=<pasta>` (pula a
> escolha de pasta) e o Administrar lê `?projeto=` ou o último contexto
> (`localStorage conduto.projeto`).

# 3. build de produção (o backend passa a servir na raiz)
npm run build
```

## Contrato API

| Método | Rota | Espelho TUI |
| --- | --- | --- |
| GET | /api/saude, /api/sgbds | ADAPTERS |
| POST | /api/conexoes/testar | testar_conexao |
| GET | /api/drivers/faltantes?tipo= | drivers_faltantes (verificar antes de instalar) |
| POST | /api/drivers/instalar | instalar_drivers (pip no servidor) |
| GET | /api/drivers/sqlserver-odbc | ODBC Driver 18/17 presente? |
| POST | /api/drivers/sqlserver-odbc/instalar | instalar_driver_sqlserver (nativo) |
| POST | /api/catalogo/bancos, /schemas, /tabelas | admin.listar_* |
| POST | /api/projeto/init | init_exec.executar_init (+ cron_padrao opcional) |
| GET | /api/projeto/resumo, /docs | spa_modelo.resumir, docs coletar_dados |
| POST | /api/projeto/ddl, /schedules (+cron), /inferir | ddl, schedules_auto, inferir |
| GET | /api/sistema/pastas?caminho= | navegador de pastas do servidor |
| GET/POST | /api/servidores/dagster, /iniciar, /parar | sobe/consulta/para o `dagster dev` |
