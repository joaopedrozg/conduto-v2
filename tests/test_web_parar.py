"""`conduto parar`: localiza e encerra o servidor da Web UI pela porta."""

import os
import platform
import shutil
import socket
import subprocess
import sys
import time

from conduto.web import servidor


def test_pids_netstat_basico():
    saida = (
        "\r\n"
        "  TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING       1234\r\n"
        "  TCP    127.0.0.1:80801        0.0.0.0:0              LISTENING       999\r\n"
        "  TCP    127.0.0.1:8080         127.0.0.1:50000        ESTABLISHED     1234\r\n"
        "  UDP    0.0.0.0:8080           *:*                                    555\r\n"
    )
    # Só o LISTENING na porta exata (80801, ESTABLISHED e UDP ficam de fora).
    assert servidor._pids_netstat(saida, 8080) == [1234]


def test_pids_ss_e_lsof_e_fuser():
    ss = (
        "State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
        'LISTEN 0 128 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=1234,fd=5))\n'
        'LISTEN 0 128 127.0.0.1:80801 0.0.0.0:* users:(("x",pid=999,fd=5))\n'
    )
    assert servidor._pids_ss(ss, 8080) == [1234]
    assert servidor._pids_lsof("1234\n 5678\n") == [1234, 5678]
    assert servidor._pids_fuser("8080/tcp:  1234  1234") == [1234]


def test_pids_na_porta_encontra_socket_proprio():
    if platform.system() != "Windows" and not (
        shutil.which("lsof") or shutil.which("ss") or shutil.which("fuser")
    ):
        import pytest

        pytest.skip("sem ferramenta de inspeção de porta")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    try:
        porta = sock.getsockname()[1]
        assert os.getpid() in servidor.pids_na_porta(porta)
    finally:
        sock.close()


def test_encerrar_processo_filho():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert servidor.encerrar(proc.pid, timeout=10) is True
        assert proc.wait(timeout=15) is not None
    finally:
        if proc.poll() is None:
            proc.kill()


def test_parar_servidor_porta_livre():
    ok, mensagem = servidor.parar_servidor(9)
    assert ok is True
    assert "9" in mensagem
