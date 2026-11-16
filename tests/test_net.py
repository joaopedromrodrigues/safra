"""Cache e retry do download, contra um servidor local que falha de proposito."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from safra import net


class Handler(BaseHTTPRequestHandler):
    falhas_pendentes = 0
    pedidos = 0

    def do_GET(self):  # noqa: N802
        type(self).pedidos += 1
        if type(self).falhas_pendentes > 0:
            type(self).falhas_pendentes -= 1
            self.send_error(429, "slow down")
            return
        corpo = b"conteudo"
        self.send_response(200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *_):  # silencia o log do http.server
        return


@pytest.fixture
def servidor():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/dado"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(net.time, "sleep", lambda *_: None)


def test_retry_depois_de_429_e_cache_depois(servidor, tmp_path, monkeypatch):
    monkeypatch.setattr(net, "MANIFEST", tmp_path / "manifest.jsonl")
    Handler.falhas_pendentes, Handler.pedidos = 1, 0

    coleta = net.fetch(servidor, tmp_path / "dado.txt", tentativas=3, min_intervalo=0)
    assert coleta["status"] == "baixado"
    assert (tmp_path / "dado.txt").read_text() == "conteudo"
    assert Handler.pedidos == 2

    cache = net.fetch(servidor, tmp_path / "dado.txt", min_intervalo=0)
    assert cache["status"] == "cache"
    assert Handler.pedidos == 2, "cache nao pode bater no servidor"

    registros = (tmp_path / "manifest.jsonl").read_text().strip().splitlines()
    assert len(registros) == 1
    assert '"status": "baixado"' in registros[0]


def test_falha_persistente_nao_deixa_arquivo(servidor, tmp_path, monkeypatch):
    monkeypatch.setattr(net, "MANIFEST", tmp_path / "manifest.jsonl")
    Handler.falhas_pendentes, Handler.pedidos = 99, 0

    with pytest.raises(net.DownloadError):
        net.fetch(servidor, tmp_path / "dado.txt", tentativas=2, min_intervalo=0)

    assert Handler.pedidos == 2
    assert list(tmp_path.glob("*")) == [], "nao pode sobrar .part nem arquivo parcial"


def test_force_ignora_cache(servidor, tmp_path, monkeypatch):
    monkeypatch.setattr(net, "MANIFEST", tmp_path / "manifest.jsonl")
    Handler.falhas_pendentes, Handler.pedidos = 0, 0

    net.fetch(servidor, tmp_path / "dado.txt", min_intervalo=0)
    net.fetch(servidor, tmp_path / "dado.txt", min_intervalo=0, force=True)
    assert Handler.pedidos == 2
