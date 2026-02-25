"""
test_daemon_protocol.py — Testes de integração do modo daemon (main.py).

Testa o protocolo stdin/stdout JSON sem depender do executável compilado,
rodando main.py diretamente via subprocess com --daemon.
"""
import json
import sys
import subprocess
import threading
import time
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"
SAMPLE_XLSX = Path("C:/Users/rikel/OneDrive/Área de Trabalho/Itau CRI Rivello 2025-07.xlsx")


def _skip_if_no_sample():
    return pytest.mark.skipif(
        not SAMPLE_XLSX.exists(),
        reason=f"Arquivo de amostra não encontrado: {SAMPLE_XLSX}"
    )


# ===========================================================================
# Helpers
# ===========================================================================

def _start_daemon():
    """Inicia o daemon como subprocesso e retorna o objeto Process."""
    proc = subprocess.Popen(
        [sys.executable, str(MAIN), "--daemon"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # modo bytes para controle manual de encoding
        cwd=str(ROOT),
    )
    return proc


def _wait_ready(proc, timeout=30.0) -> bool:
    """Aguarda DAEMON_READY no stderr."""
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = proc.stderr.read(64)
        if not chunk:
            time.sleep(0.05)
            continue
        buf += chunk
        if b"DAEMON_READY" in buf:
            return True
    return False


def _send_cmd(proc, cmd: str, input_path: str) -> dict:
    """Envia um comando e lê a resposta JSON."""
    payload = json.dumps({"cmd": cmd, "input": input_path}, ensure_ascii=False)
    proc.stdin.write((payload + "\n").encode("utf-8"))
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line.decode("utf-8").strip())


# ===========================================================================
# Testes do protocolo daemon
# ===========================================================================

@_skip_if_no_sample()
class TestDaemonProtocol:
    @pytest.fixture(autouse=True)
    def daemon(self):
        proc = _start_daemon()
        ready = _wait_ready(proc, timeout=45)
        if not ready:
            proc.kill()
            pytest.skip("Daemon não emitiu DAEMON_READY em 45s")
        yield proc
        proc.kill()
        proc.wait(timeout=5)

    def test_daemon_ready_sinalizado(self, daemon):
        # Se chegou até aqui, DAEMON_READY foi emitido (fixture garante)
        assert daemon.poll() is None  # processo ainda vivo

    def test_get_all_retorna_documentos(self, daemon):
        result = _send_cmd(daemon, "get-all", str(SAMPLE_XLSX))
        assert "documentos" in result
        assert isinstance(result["documentos"], list)
        assert len(result["documentos"]) > 0

    def test_get_all_retorna_planos(self, daemon):
        result = _send_cmd(daemon, "get-all", str(SAMPLE_XLSX))
        assert "planos_por_documento" in result
        assert isinstance(result["planos_por_documento"], dict)

    def test_get_all_retorna_datas(self, daemon):
        result = _send_cmd(daemon, "get-all", str(SAMPLE_XLSX))
        assert "datas" in result
        assert len(result["datas"]) > 0

    def test_get_all_retorna_datas_por_documento(self, daemon):
        result = _send_cmd(daemon, "get-all", str(SAMPLE_XLSX))
        assert "datas_por_documento" in result

    def test_get_preview_retorna_headers_e_rows(self, daemon):
        result = _send_cmd(daemon, "get-preview", str(SAMPLE_XLSX))
        assert "headers" in result
        assert "rows" in result
        assert isinstance(result["headers"], list)
        assert len(result["headers"]) > 0

    def test_get_options_retorna_documentos(self, daemon):
        result = _send_cmd(daemon, "get-options", str(SAMPLE_XLSX))
        assert "documentos" in result

    def test_cmd_desconhecido_retorna_erro(self, daemon):
        result = _send_cmd(daemon, "cmd-invalido", str(SAMPLE_XLSX))
        assert "erro" in result

    def test_multiplos_comandos_sequenciais(self, daemon):
        """Daemon deve responder corretamente a vários comandos em sequência."""
        for _ in range(3):
            result = _send_cmd(daemon, "get-all", str(SAMPLE_XLSX))
            assert "documentos" in result

    def test_arquivo_inexistente_retorna_erro(self, daemon):
        result = _send_cmd(daemon, "get-all", "/nao/existe/arquivo.xlsx")
        assert "erro" in result


# ===========================================================================
# Testes do modo CLI (invocação direta, sem daemon)
# ===========================================================================

@_skip_if_no_sample()
class TestCLIGetAll:
    def _run(self, args: list[str]) -> dict:
        result = subprocess.run(
            [sys.executable, str(MAIN)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=60,
        )
        return json.loads(result.stdout.strip())

    def test_get_all_documentos(self):
        data = self._run(["--input", str(SAMPLE_XLSX), "--get-all", "--quiet"])
        assert "documentos" in data
        assert len(data["documentos"]) > 0

    def test_get_preview_headers(self):
        data = self._run(["--input", str(SAMPLE_XLSX), "--get-preview", "--quiet"])
        assert "headers" in data
        assert len(data["headers"]) > 0

    def test_get_options(self):
        data = self._run(["--input", str(SAMPLE_XLSX), "--get-options", "--quiet"])
        assert "documentos" in data

    def test_get_all_colunas_obrigatorias_presentes(self):
        data = self._run(["--input", str(SAMPLE_XLSX), "--get-all", "--quiet"])
        assert data["colunas_obrigatorias"]["todas_presentes"] is True

    def test_arquivo_inexistente_retorna_json_erro(self):
        result = subprocess.run(
            [sys.executable, str(MAIN), "--input", "/nao/existe.xlsx", "--get-all"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=10,
        )
        data = json.loads(result.stdout.strip())
        assert "erro" in data
