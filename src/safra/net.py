"""Download com cache em disco, throttle e retry.

As tres APIs do projeto (SIDRA, malhas, POWER) falham de formas diferentes: o
POWER responde 429 quando o pedido e rapido demais, o SIDRA tem picos de 503, e
ambos derrubam conexao no meio. Em vez de tratar caso a caso, tudo passa por
`fetch`, que grava em arquivo temporario, so promove quando o download termina e
registra a coleta num manifesto -- entao uma execucao interrompida no meio
retoma de onde parou em vez de baixar tudo de novo.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from .config import MANIFEST, USER_AGENT

_ultimo_pedido = 0.0


class DownloadError(RuntimeError):
    pass


def _espera_intervalo(min_intervalo: float) -> None:
    global _ultimo_pedido
    decorrido = time.monotonic() - _ultimo_pedido
    if decorrido < min_intervalo:
        time.sleep(min_intervalo - decorrido)
    _ultimo_pedido = time.monotonic()


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _registra(registro: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")


def fetch(
    url: str,
    destino: Path,
    *,
    timeout: int = 180,
    tentativas: int = 4,
    min_intervalo: float = 1.2,
    force: bool = False,
) -> dict:
    """Baixa `url` para `destino`. Devolve {'status': 'cache'|'baixado', ...}.

    `status='cache'` quando o arquivo ja existe e `force` e False: e o caso comum,
    porque a PAM e anual e a serie do POWER quase nao muda entre execucoes.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0 and not force:
        return {"url": url, "destino": str(destino), "status": "cache",
                "bytes": destino.stat().st_size}

    parcial = destino.with_suffix(destino.suffix + ".part")
    erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        _espera_intervalo(min_intervalo)
        inicio = time.monotonic()
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
                parcial.write_bytes(resposta.read())
            if parcial.stat().st_size == 0:
                raise DownloadError("resposta vazia")
            parcial.replace(destino)
            registro = {
                "url": url,
                "destino": str(destino),
                "status": "baixado",
                "bytes": destino.stat().st_size,
                "sha256": _sha256(destino),
                "duracao_s": round(time.monotonic() - inicio, 2),
                "coletado_em": datetime.now(UTC).isoformat(timespec="seconds"),
            }
            _registra(registro)
            return registro
        except urllib.error.HTTPError as exc:
            erro = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise DownloadError(f"{url} -> HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, DownloadError) as exc:
            erro = exc
        espera = min(60, 2 ** tentativa) + random.uniform(0, 0.5)
        if tentativa < tentativas:
            time.sleep(espera)

    parcial.unlink(missing_ok=True)
    raise DownloadError(f"{url} falhou em {tentativas} tentativas: {erro}")
