"""Pergunta de instalação do driver ao selecionar o SGBD no formulário.

Ao escolher o tipo de banco, o form checa ``drivers_faltantes``: se
faltar algo, pergunta na linha de status e liga o botão "Instalar
driver". A instalação roda em worker para não travar a tela. Sem
mutação de layout (só texto + ``disabled``): mostrar/esconder caixas
quebrava o posicionamento dos botões no Textual.
"""

import asyncio
import threading

import pytest
from textual.widgets import Button, ContentSwitcher, Select

from conduto.database import drivers as drivers_mod
from conduto.i18n import definir_idioma
from conduto.tui.dashboard import CondutoApp, FormularioConexao


@pytest.fixture(autouse=True)
def _idioma():
    definir_idioma("pt")


def _rodar(cenario):
    return asyncio.run(cenario())


async def _selecionar(app, pilot, papel="origem", tipo="postgresql"):
    # O form mora na tela de conexões: sem navegar, o clique não chega.
    app.query_one(ContentSwitcher).current = "tela-conexoes"
    await pilot.pause()
    form = app.query_one(f"#form-{papel}", FormularioConexao)
    select = form.query_one(Select)
    select.value = tipo
    select.post_message(Select.Changed(select, tipo))
    await pilot.pause()
    await pilot.pause()
    return form


def _botao_driver(form):
    return form.query_one(f"#{form.papel}-btn-driver", Button)


def test_sem_driver_faltando_nao_pergunta_nada(monkeypatch):
    async def cenario():
        monkeypatch.setattr(drivers_mod, "drivers_faltantes", lambda tipo: ())
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            assert _botao_driver(form).disabled is True
            await _selecionar(app, pilot)
            assert _botao_driver(form).disabled is True
            assert form.status_texto == ""
        return None

    _rodar(cenario)


def test_com_driver_faltando_pergunta_e_liga_o_botao(monkeypatch):
    async def cenario():
        monkeypatch.setattr(drivers_mod, "drivers_faltantes", lambda tipo: ("psycopg",))
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot)
            assert _botao_driver(form).disabled is False
            assert "psycopg" in form.status_texto
            assert "instalar" in form.status_texto.lower()
        return None

    _rodar(cenario)


def test_clicar_instalar_executa_e_mostra_resultado(monkeypatch):
    chamadas = []
    instalado = []

    async def cenario():
        # Após instalar, o driver passa a existir: o botão só desliga
        # quando a rechecagem confirma que não falta mais nada.
        monkeypatch.setattr(
            drivers_mod, "drivers_faltantes", lambda tipo: () if instalado else ("psycopg",)
        )

        def _instalar(tipo):
            chamadas.append(tipo)
            instalado.append(True)
            return True, "Dependências do postgresql instaladas com sucesso"

        monkeypatch.setattr(drivers_mod, "instalar_drivers", _instalar)
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot)
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-driver")
            await pilot.pause()
            await pilot.pause()
            assert chamadas == ["postgresql"]
            assert _botao_driver(form).disabled is True
            assert "instaladas com sucesso" in form.status_texto
        return None

    _rodar(cenario)


def test_falha_na_instalacao_mostra_comando_manual_e_mantem_botao(monkeypatch):
    async def cenario():
        monkeypatch.setattr(drivers_mod, "drivers_faltantes", lambda tipo: ("psycopg",))
        monkeypatch.setattr(
            drivers_mod,
            "instalar_drivers",
            lambda tipo: (False, 'Instale manualmente com: pip install psycopg[binary]'),
        )
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot)
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-driver")
            await pilot.pause()
            await pilot.pause()
            assert "pip install" in form.status_texto
            assert _botao_driver(form).disabled is False
        return None

    _rodar(cenario)


def test_trocar_para_sgbd_ok_desliga_e_limpa_a_pergunta(monkeypatch):
    async def cenario():
        monkeypatch.setattr(
            drivers_mod, "drivers_faltantes", lambda tipo: ("psycopg",) if tipo == "postgresql" else ()
        )
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot, tipo="postgresql")
            assert _botao_driver(form).disabled is False
            assert form.status_texto != ""
            await _selecionar(app, pilot, tipo="duckdb")
            assert _botao_driver(form).disabled is True
            assert form.status_texto == ""
        return None

    _rodar(cenario)


def test_status_mostra_instalando_enquanto_instala(monkeypatch):
    liberado = threading.Event()

    async def cenario():
        monkeypatch.setattr(drivers_mod, "drivers_faltantes", lambda tipo: ("psycopg",))

        def _instalar(tipo):
            liberado.wait(timeout=10)
            return True, "ok"

        monkeypatch.setattr(drivers_mod, "instalar_drivers", _instalar)
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot)
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-driver")
            await pilot.pause()
            await pilot.pause()
            assert "instalando" in form.status_texto.lower()
            liberado.set()
            await pilot.pause()
            await pilot.pause()
            assert form.status_texto == "ok"
        return None

    _rodar(cenario)


def test_pergunta_e_por_formulario_origem_e_destino_independentes(monkeypatch):
    async def cenario():
        monkeypatch.setattr(
            drivers_mod, "drivers_faltantes", lambda tipo: ("psycopg",) if tipo == "postgresql" else ()
        )
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            origem = await _selecionar(app, pilot, papel="origem", tipo="postgresql")
            destino = await _selecionar(app, pilot, papel="destino", tipo="duckdb")
            assert _botao_driver(origem).disabled is False
            assert _botao_driver(destino).disabled is True
        return None

    _rodar(cenario)


def test_aceite_instala_sozinho_de_ponta_a_ponta(monkeypatch):
    """Um clique instala sem digitar comando: só o subprocesso é segurado.

    `drivers_faltantes` e `instalar_drivers` são os reais; `_rodar` (o
    mesmo seam de `test_drivers.py`) finge o pip com sucesso e registra
    o comando que rodaria de verdade.
    """
    comandos = []

    async def cenario():
        def _rodar_fake(comando):
            comandos.append(comando)
            return "", False

        monkeypatch.setattr(drivers_mod, "_rodar", _rodar_fake)
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            form = await _selecionar(app, pilot, tipo="postgresql")
            if _botao_driver(form).disabled is True:
                pytest.skip("psycopg já instalado neste ambiente")
            await pilot.pause()  # estabiliza o layout pós-Select antes do clique
            await pilot.click("#origem-btn-driver")
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert any("psycopg[binary]" in parte for parte in comandos[0])
            assert "instaladas com sucesso" in form.status_texto
        return None

    _rodar(cenario)


def test_botao_instalar_divide_a_linha_com_o_seletor_de_tipo():
    async def cenario():
        app = CondutoApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(ContentSwitcher).current = "tela-conexoes"
            await pilot.pause()
            form = app.query_one("#form-origem", FormularioConexao)
            select = form.query_one("#origem-tipo", Select)
            botao = form.query_one("#origem-btn-driver", Button)
            # Lado a lado na mesma linha, dividindo o espaço com paridade:
            # seletor fica com a parte flexível, botão só o rótulo.
            assert select.region.y == botao.region.y
            assert botao.region.x > select.region.x
            assert select.region.x + select.region.width <= botao.region.x + 2
            assert abs(select.region.width - botao.region.width) <= 4
            assert select.region.width >= 8
            # Mesma altura: botão do tamanho do seletor.
            assert botao.region.height == select.region.height
            # Suspiro entre os dois, no padrão das fileiras de botões.
            assert botao.region.x - (select.region.x + select.region.width) == 2
        return None

    _rodar(cenario)
