"""Loop CLI para o opcional 2 (streaming de votacoes).

Equivalente a um job de micro-batch a cada 10 min. Em Databricks viraria
Structured Streaming com `.trigger(processingTime="10 minutes")`.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from src.analytics.streaming_votacoes import TickMetrics, classifica_urgencia
from src.ingestion.api_client import CamaraAPIClient
from src.utils.config_loader import load
from src.utils.logging_setup import new_run_id

logger = logging.getLogger(__name__)
ALERTS_DIR = Path("data/streaming/alerts")
STATE_FILE = Path("data/ctl/stream_votacoes_offset.json")


def _read_offset() -> str | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_id")
    except Exception:
        return None


def _write_offset(last_id: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last_id": last_id}), encoding="utf-8")


def tick(client: CamaraAPIClient, run_id: str, max_pages: int = 1) -> TickMetrics:
    """Uma execucao do micro-batch."""
    t0 = time.monotonic()
    last_id = _read_offset()
    cfg = load()
    endpoint = cfg.endpoints["votacoes"]

    new = 0
    urgentes = 0
    errors = 0
    alerts: list[dict] = []

    try:
        for page in client.iter_pages(endpoint,
                                      extra_params={"ordem": "DESC",
                                                    "ordenarPor": "dataHoraRegistro"},
                                      max_pages=max_pages):
            for rec in page.records:
                vid = rec.get("id")
                if last_id and vid == last_id:
                    break
                urgencia = classifica_urgencia(rec.get("descricao") or "")
                alerts.append({
                    "id_votacao": vid,
                    "data_hora_registro": rec.get("dataHoraRegistro"),
                    "descricao": rec.get("descricao"),
                    "urgencia": urgencia,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                })
                new += 1
                if urgencia == "urgente":
                    urgentes += 1

        if alerts:
            ALERTS_DIR.mkdir(parents=True, exist_ok=True)
            out_path = ALERTS_DIR / f"alerts_{run_id}.jsonl"
            with out_path.open("w", encoding="utf-8") as f:
                for a in alerts:
                    f.write(json.dumps(a, ensure_ascii=False) + "\n")
            _write_offset(alerts[0]["id_votacao"])
    except Exception:
        errors += 1
        raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)

    return TickMetrics(
        run_id=run_id,
        new_records=new,
        urgentes=urgentes,
        duration_ms=duration_ms,
        errors=errors,
        status="ok" if errors == 0 else "failed",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=600,
                        help="segundos entre ticks (default 600 = 10 min)")
    parser.add_argument("--max-iters", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load()
    client = CamaraAPIClient(cfg)

    sla: list[TickMetrics] = []
    for i in range(args.max_iters):
        run_id = new_run_id()
        m = tick(client, run_id)
        sla.append(m)
        print(f"  tick {run_id}  new={m.new_records:>3d}  "
              f"urgentes={m.urgentes:>2d}  dur={m.duration_ms:>5d}ms  "
              f"status={m.status}")
        if i < args.max_iters - 1:
            time.sleep(args.interval)

    if sla:
        latencias = sorted(m.duration_ms for m in sla)
        p50 = latencias[len(latencias) // 2]
        print(f"\nSLA p50 latencia: {p50}ms | erros: {sum(m.errors for m in sla)}")


if __name__ == "__main__":
    main()
