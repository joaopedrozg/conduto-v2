"""Localiza e encerra o servidor da Web UI pela porta (`conduto parar`).

Sem dependências novas: no Windows usa `netstat`/`taskkill`, no
Linux/macOS usa `lsof` (com fallback para `ss` e `fuser`) + `os.kill`.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import subprocess
import time
from typing import List, Tuple

__all__ = ["encerrar", "nome_processo", "parar_servidor", "pids_na_porta"]


def _pids_netstat(saida: str, porta: int) -> List[int]:
    """PIDs em LISTENING na porta (saída do `netstat -ano` do Windows)."""
    padrao = re.compile(rf"^\s*TCP\s+\S+:{porta}(?=\s).*LISTENING\s+(\d+)\s*$", re.MULTILINE)
    return sorted({int(pid) for pid in padrao.findall(saida)})


def _pids_ss(saida: str, porta: int) -> List[int]:
    """PIDs escutando na porta (saída do `ss -ltnp` do Linux)."""
    pids = []
    for linha in saida.splitlines():
        if re.search(rf":{porta}(?=\s)", linha):
            pids.extend(int(pid) for pid in re.findall(r"pid=(\d+)", linha))
    return sorted(set(pids))


def _pids_lsof(saida: str) -> List[int]:
    """PIDs da saída do `lsof -ti` (um PID por linha, sem cabeçalho)."""
    return sorted({int(linha) for linha in saida.split() if linha.strip().isdigit()})


def _pids_fuser(saida: str) -> List[int]:
    """PIDs da saída do `fuser 8080/tcp` (ignora o cabeçalho `PORTA/tcp:`)."""
    corpo = re.sub(r"^\s*\d+/tcp:\s*", "", saida)
    return sorted({int(pid) for pid in re.findall(r"\b\d+\b", corpo)})


def _rodar(comando: List[str]) -> str:
    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return resultado.stdout or ""


def pids_na_porta(porta: int) -> List[int]:
    """PIDs com socket em escuta na porta (vazio = livre)."""
    if platform.system() == "Windows":
        return _pids_netstat(_rodar(["netstat", "-ano"]), porta)
    if shutil.which("lsof"):
        return _pids_lsof(_rodar(["lsof", "-ti", f"tcp:{porta}"]))
    if shutil.which("ss"):
        return _pids_ss(_rodar(["ss", "-ltnp"]), porta)
    if shutil.which("fuser"):
        return _pids_fuser(_rodar(["fuser", f"{porta}/tcp"]))
    return []


def nome_processo(pid: int) -> str:
    """Nome do processo (vazio se já morreu ou sem permissão)."""
    if platform.system() == "Windows":
        saida = _rodar(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        for linha in saida.splitlines():
            partes = [p.strip().strip('"') for p in linha.split('","')]
            if len(partes) >= 2 and partes[1] == str(pid):
                return partes[0]
        return ""
    saida = _rodar(["ps", "-p", str(pid), "-o", "comm="]).strip()
    return saida.splitlines()[0].strip() if saida else ""


def _vivo(pid: int) -> bool:
    # No Windows, os.kill(pid, 0) segue passando para processo já morto
    # enquanto o pai não o recolheu (handle aberto): o tasklist reflete
    # a realidade (morto some da lista).
    if platform.system() == "Windows":
        saida = _rodar(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
        for linha in saida.splitlines():
            partes = [p.strip().strip('"') for p in linha.split('","')]
            if len(partes) >= 2 and partes[1] == str(pid):
                return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def encerrar(pid: int, timeout: float = 10) -> bool:
    """Encerra o PID (gentil primeiro, forçado depois). True se morreu."""
    if not _vivo(pid):
        return True
    if platform.system() == "Windows":
        _rodar(["taskkill", "/PID", str(pid)])
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return not _vivo(pid)
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout:
        if not _vivo(pid):
            return True
        time.sleep(0.5)
    if platform.system() == "Windows":
        _rodar(["taskkill", "/F", "/PID", str(pid)])
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    time.sleep(1)
    return not _vivo(pid)


def parar_servidor(porta: int, timeout: float = 10) -> Tuple[bool, str]:
    """Encerra quem escuta na porta. Devolve (ok, mensagem em pt-BR)."""
    pids = [p for p in pids_na_porta(porta) if p != os.getpid()]
    if not pids:
        return True, f"Nenhum servidor na porta {porta}."
    rotulos = [f"{nome_processo(pid) or 'processo'} (PID {pid})" for pid in pids]
    falharam = [pid for pid in pids if not encerrar(pid, timeout)]
    if falharam:
        return False, (
            f"Não foi possível encerrar na porta {porta}: "
            + ", ".join(f"PID {pid}" for pid in falharam)
            + " (tente como administrador)."
        )
    return True, "Servidor encerrado na porta {porta}: {quem}.".format(
        porta=porta, quem=", ".join(rotulos)
    )
