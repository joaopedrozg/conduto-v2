"""Backend FastAPI da Web UI — mesma lógica da TUI, sem terminal.

Espelha os dois modos da SPA Textual (``spa_modelo.PASSOS_CRIAR`` e
``PASSOS_ADMIN``):

- criar: sgbds → testar → bancos/schemas/tabelas → init;
- administrar: resumo → conexões → ddl → schedules → inferir → servidores/docs.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from conduto import __version__
from conduto.web import esquemas as E


def _adapter(tipo: str):
    from conduto.tui.conexoes import adapter_por_tipo

    adapter = adapter_por_tipo(tipo)
    if adapter is None:
        raise HTTPException(status_code=400, detail=f"Tipo de SGBD desconhecido: {tipo!r}")
    return adapter


def diretorio_frontend() -> Path | None:
    """Pasta com o build Angular ou None se não compilado.

    Ordem: `src/conduto/web/dist` (viaja dentro do pacote — `pip install`
    já vem pronto) e depois `web/dist` (atalho de dev no repo).
    O CLI (`conduto init --web`) usa para exigir o build antes da API.
    """
    aqui = Path(__file__).resolve().parent / "dist"
    repo = Path(__file__).resolve().parent.parent.parent.parent / "web" / "dist"
    for dist in (aqui, repo):
        for candidato in (dist / "browser", dist):
            if (candidato / "index.html").exists():
                return candidato
    return None


_CRON_PRESETS = {
    "15min": "*/15 * * * *",
    "hora": "0 * * * *",
    "diario": "0 0 * * *",
    "semanal": "0 0 * * 0",
}

_CRON_RE = None


def _validar_cron(cron: str) -> str:
    """Normaliza preset ou cron; levanta 400 se inválido."""
    import re

    global _CRON_RE
    if _CRON_RE is None:
        _CRON_RE = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$")
    cron = (cron or "").strip()
    if cron in _CRON_PRESETS:
        return _CRON_PRESETS[cron]
    if not _CRON_RE.match(cron):
        raise HTTPException(
            status_code=400,
            detail=f"Cron inválido: {cron!r}. Use 5 campos (ex.: '0 * * * *') ou preset: {sorted(_CRON_PRESETS)}",
        )
    return cron


def _aplicar_cron_padrao(project_dir: Path, cron: str) -> int:
    """Força o cron no schedule geral (main.yml) e no de cada schema. Devolve nº de schemas."""
    import yaml

    cron = _validar_cron(cron)
    main_path = project_dir / "main.yml"
    if main_path.exists():
        main = yaml.safe_load(main_path.read_text(encoding="utf-8")) or {}
        main.setdefault("schedule", {})["cron"] = cron
        main_path.write_text(yaml.safe_dump(main, allow_unicode=True, sort_keys=False), encoding="utf-8")
    alterados = 0
    for schema_path in sorted((project_dir / "schemas").glob("*.yml")):
        try:
            dados = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        dados.setdefault("schedule", {})["cron"] = cron
        schema_path.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
        alterados += 1
    return alterados


# Servidor Dagster gerenciado pela Web UI (um por diretório de projeto).
_DAGSTER_PROC: dict = {}


def criar_app() -> FastAPI:
    app = FastAPI(title="conduto web", version=__version__)

    @app.get("/api/saude")
    def saude():
        return {"ok": True, "versao": __version__, "tui": "mantida (Textual)"}

    @app.get("/api/sgbds")
    def sgbds():
        from conduto.database.adapters import ADAPTERS

        return [
            {
                "tipo": a.tipo,
                "nome": a.nome,
                "driver": a.driver,
                "host_padrao": a.host_padrao,
                "porta_padrao": a.porta_padrao,
                "banco_padrao": a.banco_padrao,
                "usuario_padrao": a.usuario_padrao,
            }
            for a in ADAPTERS.values()
        ]

    @app.post("/api/conexoes/testar")
    def testar_conexao(pedido: E.PedidoCatalogo):
        from conduto.database.adapters import testar_conexao as _testar

        cred = pedido.credenciais.para_dict()
        ok, mensagem = _testar(_adapter(cred["tipo"]), cred)
        return {"ok": ok, "mensagem": mensagem}

    @app.get("/api/conexoes/salvas")
    def conexoes_salvas(project_dir: str = "."):
        from conduto.web import conexoes_salvas as _salvas

        return {"conexoes": _salvas.listar(project_dir)}

    @app.post("/api/conexoes/salvas")
    def conexao_salvar(pedido: E.PedidoConexaoSalva):
        from conduto.web import conexoes_salvas as _salvas

        _adapter(pedido.credenciais.tipo)  # 400 se tipo desconhecido
        return _salvas.salvar(pedido.apelido, pedido.credenciais.para_dict(), pedido.project_dir)

    @app.delete("/api/conexoes/salvas/{identificador}")
    def conexao_remover(identificador: str, project_dir: str = "."):
        from conduto.web import conexoes_salvas as _salvas

        if not _salvas.remover(identificador, project_dir):
            raise HTTPException(status_code=404, detail="Conexão salva não encontrada.")
        return {"ok": True}

    @app.post("/api/catalogo/bancos")
    def listar_bancos(pedido: E.PedidoCatalogo):
        from conduto.database.admin import listar_bancos as _listar

        cred = pedido.credenciais.para_dict()
        try:
            return {"bancos": _listar(_adapter(cred["tipo"]), cred)}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/catalogo/schemas")
    def listar_schemas(pedido: E.PedidoCatalogo):
        from conduto.database.admin import listar_schemas as _listar

        cred = pedido.credenciais.para_dict()
        try:
            return {"schemas": _listar(_adapter(cred["tipo"]), cred)}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/catalogo/tabelas")
    def listar_tabelas(pedido: E.PedidoCatalogo):
        from conduto.schemas.schemas_auto import listar_tabelas_origem

        cred = pedido.credenciais.para_dict()
        try:
            tabelas = listar_tabelas_origem(_adapter(cred["tipo"]), cred)
            if pedido.schemas:
                pedidos = set(pedido.schemas)
                tabelas = [t for t in tabelas if t.get("schema") in pedidos]
            return {"tabelas": tabelas}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/api/projeto/init")
    def criar_projeto(pedido: E.PedidoInit):
        from conduto.init_exec import ParametrosInit, executar_init

        params = ParametrosInit(
            project_dir=Path(pedido.project_dir),
            nome_projeto=pedido.nome_projeto or Path(pedido.project_dir).name,
            origem=pedido.origem.para_dict(),
            destino=pedido.destino.para_dict(),
            gerar_automatico=pedido.gerar_automatico,
            tabelas=[{"schema": t.schema_, "table": t.table} for t in pedido.tabelas],
            gerar_schedules=pedido.gerar_schedules,
            aplicar_ddl=pedido.aplicar_ddl,
            armazenamento=pedido.armazenamento,
        )
        try:
            resultado = executar_init(params, silenciar_console=True)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # erro de banco/rede no DDL, setup uv etc.
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        cron_aplicado = None
        if pedido.cron_padrao:
            try:
                _aplicar_cron_padrao(Path(pedido.project_dir), pedido.cron_padrao)
                cron_aplicado = _validar_cron(pedido.cron_padrao)
            except HTTPException as exc:
                raise exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "project_dir": str(resultado.project_dir),
            "env": str(resultado.env_path) if resultado.env_path else None,
            "schemas_gerados": resultado.schemas_gerados,
            "schedules": resultado.schedules,
            "ddl_comandos": resultado.ddl_comandos,
            "ddl_aplicado": resultado.ddl_aplicado,
            "cron_aplicado": cron_aplicado,
        }

    @app.get("/api/projeto/resumo")
    def resumo_projeto(project_dir: str = "."):
        from conduto.tui.spa_modelo import resumir_projeto

        resumo = resumir_projeto(Path(project_dir))
        return {
            "nome": resumo.nome,
            "tem_env": resumo.tem_env,
            "tem_main": resumo.tem_main,
            "tabelas": resumo.tabelas,
            "n_schemas": resumo.n_schemas,
            "tem_dagster": resumo.tem_dagster,
            "origem_tipo": resumo.origem_tipo,
            "destino_tipo": resumo.destino_tipo,
        }

    @app.get("/api/projeto/docs")
    def docs_projeto(project_dir: str = "."):
        from conduto.docs.docs_server import coletar_dados

        try:
            return coletar_dados(Path(project_dir))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projeto/ddl")
    def gerar_ddl(pedido: E.PedidoDdl):
        from conduto.ddl.ddl_render import (
            carregar_tabelas,
            credenciais_destino,
            dividir_statement,
            executar_ddl,
            gerar_ddl as _gerar,
        )

        project_dir = Path(pedido.project_dir)
        try:
            credenciais, tipo = credenciais_destino(project_dir)
            tabelas = carregar_tabelas(project_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not tabelas:
            raise HTTPException(status_code=400, detail="Nenhum schema YAML encontrado.")
        texto = _gerar(tabelas, tipo)
        comandos = dividir_statement(texto)
        aplicada = 0
        if pedido.aplicar:
            try:
                erros = executar_ddl(tipo, credenciais, comandos)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            if erros:
                raise HTTPException(status_code=502, detail="; ".join(str(e) for e in erros))
            aplicada = len(comandos)
        return {"tipo": tipo, "ddl": texto, "comandos": len(comandos), "aplicados": aplicada}

    @app.post("/api/projeto/schedules")
    def gerar_schedules(pedido: E.PedidoSchedules):
        from conduto.schedules.schedules_auto import (
            gerar_schedules_automaticos,
            nome_projeto,
        )

        project_dir = Path(pedido.project_dir)
        try:
            nome = nome_projeto(project_dir)
            atualizados = gerar_schedules_automaticos(project_dir, nome)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        cron_aplicado = None
        if pedido.cron:
            try:
                _aplicar_cron_padrao(project_dir, pedido.cron)
                cron_aplicado = _validar_cron(pedido.cron)
            except HTTPException as exc:
                raise exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"projeto": nome, "atualizados": atualizados, "cron_aplicado": cron_aplicado}

    @app.post("/api/projeto/inferir")
    def inferir(pedido: E.PedidoInferir):
        from conduto.schemas.schemas_inferir import inferir_colunas

        try:
            inferidas = inferir_colunas(Path(pedido.project_dir), pedido.tabela, pedido.forcar)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not inferidas:
            raise HTTPException(
                status_code=400,
                detail="Nada a inferir: todos os schemas já têm colunas "
                "(marque Re-inferir para forçar).",
            )
        return {"inferidas": inferidas}

    @app.get("/api/drivers/faltantes")
    def drivers_faltantes(tipo: str):
        from conduto.database.drivers import drivers_faltantes as _falt, requisicoes_pendentes

        _adapter(tipo)  # 400 se tipo desconhecido
        falt = list(_falt(tipo))
        return {"tipo": tipo, "faltantes": falt, "requisicoes": requisicoes_pendentes(tipo)}

    @app.post("/api/drivers/instalar")
    def drivers_instalar(pedido: E.PedidoDriver):
        from conduto.database.drivers import instalar_drivers

        _adapter(pedido.tipo)  # 400 se tipo desconhecido
        ok, mensagem = instalar_drivers(pedido.tipo, quebrar_sistema=pedido.quebrar_sistema)
        if not ok:
            raise HTTPException(status_code=502, detail=mensagem)
        return {"ok": True, "mensagem": mensagem}

    @app.get("/api/drivers/sqlserver-odbc")
    def odbc_status():
        try:
            import pyodbc

            instalados = pyodbc.drivers()
        except Exception:
            instalados = []
        alvos = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]
        return {
            "instalados": instalados,
            "ok": any(a in instalados for a in alvos),
            "requeridos": alvos,
        }

    @app.post("/api/drivers/sqlserver-odbc/instalar")
    def odbc_instalar():
        from conduto.database.adapters import instalar_driver_sqlserver

        ok, mensagem = instalar_driver_sqlserver()
        if not ok:
            raise HTTPException(status_code=502, detail=mensagem)
        return {"ok": True, "mensagem": mensagem}

    @app.get("/api/sistema/pastas")
    def listar_pastas(caminho: str = "."):
        """Navega o filesystem do servidor para o seletor de pasta do projeto."""
        base = Path(caminho or ".").expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        try:
            atual = base.resolve()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not atual.exists() or not atual.is_dir():
            raise HTTPException(status_code=400, detail=f"Pasta não encontrada: {caminho}")
        try:
            pastas = sorted(p.name for p in atual.iterdir() if p.is_dir() and not p.name.startswith("."))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        pai = str(atual.parent) if atual.parent != atual else None
        return {
            "atual": str(atual),
            "pai": pai,
            "pastas": pastas,
            "casa": str(Path.home()),
            "servidor_cwd": str(Path.cwd()),
        }

    def _dagster_vivo(project_dir: str) -> bool:
        proc = _DAGSTER_PROC.get(project_dir)
        return proc is not None and proc.poll() is None

    def _dagster_responde(url: str = "http://localhost:3000") -> bool:
        import urllib.request

        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    @app.get("/api/servidores/dagster")
    def dagster_status(project_dir: str = "."):
        chave = str(Path(project_dir or ".").resolve())
        vivo = _dagster_vivo(chave)
        responde = _dagster_responde()
        return {
            "rodando": vivo,
            "responde": responde,
            # responde sem processo gerenciado = subido por fora (terminal/TUI).
            "externo": responde and not vivo,
            "pid": _DAGSTER_PROC[chave].pid if vivo else None,
            "url": "http://localhost:3000",
        }

    @app.post("/api/servidores/dagster/iniciar")
    def dagster_iniciar(pedido: E.PedidoDagster):
        import subprocess

        from conduto.schedules.dagster_render import garantir_config_dagster
        from conduto.schedules.schedules_auto import garantir_codigo_dagster

        project_dir = Path(pedido.project_dir or ".")
        if not (project_dir / "pyproject.toml").exists():
            raise HTTPException(
                status_code=400,
                detail=f"Nenhum projeto uv em: {project_dir}",
            )
        chave = str(project_dir.resolve())
        if _dagster_vivo(chave):
            return {"rodando": True, "pid": _DAGSTER_PROC[chave].pid, "url": "http://localhost:3000"}
        if _dagster_responde():
            # Porta ocupada por um servidor que a Web UI não gerencia:
            # subir outro daria conflito — o status passa a mostrá-lo.
            raise HTTPException(
                status_code=409,
                detail="Já há um servidor respondendo em http://localhost:3000 "
                "(iniciado fora da Web UI). Use Atualizar status para vê-lo.",
            )
        if not garantir_codigo_dagster(project_dir):
            raise HTTPException(status_code=400, detail="Código Dagster ausente (main.yml?).")
        if not garantir_config_dagster(project_dir):
            raise HTTPException(status_code=400, detail="Falha ao configurar [tool.dagster].")
        try:
            proc = subprocess.Popen(
                ["uv", "run", "dagster", "dev"],
                cwd=str(project_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        _DAGSTER_PROC[chave] = proc
        return {"rodando": True, "pid": proc.pid, "url": "http://localhost:3000"}

    @app.post("/api/servidores/dagster/parar")
    def dagster_parar(pedido: E.PedidoDagster):
        chave = str(Path(pedido.project_dir or ".").resolve())
        proc = _DAGSTER_PROC.get(chave)
        if proc is None or proc.poll() is not None:
            _DAGSTER_PROC.pop(chave, None)
            return {"rodando": False}
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        _DAGSTER_PROC.pop(chave, None)
        return {"rodando": False}

    # --- frontend Angular (build em web/dist) ---------------------------------
    # Em dev o Angular roda com `ng serve` e proxy para este backend; em prod
    # o `ng build` (application builder) cai em web/dist/browser e é servido
    # aqui na raiz. Suporta os dois layouts (dist/ e dist/browser/).
    estatico = diretorio_frontend()
    index = (estatico / "index.html") if estatico is not None else None
    if estatico is not None and index is not None and index.exists():
        # Servidor leve do build Angular, com fallback SPA: rota que não é
        # arquivo nem API devolve o index.html (links diretos /criar, /admin).
        raiz = estatico.resolve()

        @app.get("/{caminho:path}", include_in_schema=False)
        def spa(caminho: str):
            if caminho.startswith(("api/", "docs", "openapi.json", "redoc")):
                raise HTTPException(status_code=404, detail="Rota não encontrada")
            alvo = (estatico / caminho).resolve()
            if not str(alvo).startswith(str(raiz)):
                raise HTTPException(status_code=404, detail="Rota não encontrada")
            if alvo.is_file():
                return FileResponse(path=str(alvo))
            return FileResponse(path=str(index))
    else:

        @app.get("/", include_in_schema=False)
        def raiz_sem_build():
            return JSONResponse(
                {
                    "mensagem": "conduto web API no ar. Frontend Angular ainda não compilado.",
                    "frontend_dev": "cd web && npm install && npm start",
                    "frontend_build": "cd web && npm run build",
                    "docs_api": "/docs",
                }
            )

        @app.get("/{caminho:path}", include_in_schema=False)
        def fallback_spa(caminho: str):
            if caminho.startswith("api/") or caminho.startswith("docs"):
                raise HTTPException(status_code=404, detail="Rota não encontrada")
            if index is not None and index.exists():
                return FileResponse(path=str(index))
            return JSONResponse({"detail": "Frontend não compilado. Veja GET /"}, status_code=404)

    return app


app = criar_app()
