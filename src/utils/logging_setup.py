"""Configuracao de logging estruturado em JSON Lines.

Cada linha de log e um JSON valido com timestamp UTC, nivel, run_id e
contexto adicional. Facilita ingestao em ferramentas como Splunk/Datadog.
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonLineFormatter(logging.Formatter):
    """Formatter que serializa cada record como JSON em uma linha."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # campos extras passados via logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ) and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def new_run_id() -> str:
    """Gera um id curto para correlacionar logs de uma execucao."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def setup_logging(
    level: int = logging.INFO,
    log_dir: str | Path = "logs",
) -> tuple[logging.Logger, str, Path]:
    """Configura logging dual: stderr (legivel) + JSON em arquivo.

    Returns:
        (logger, run_id, log_path)
    """
    run_id = new_run_id()

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"run-{run_id}.jsonl"

    root = logging.getLogger()
    root.setLevel(level)

    # remove handlers anteriores (caso re-chamado em notebook)
    for h in list(root.handlers):
        root.removeHandler(h)

    # stderr para humanos
    h_console = logging.StreamHandler(sys.stderr)
    h_console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(h_console)

    # arquivo JSONL para maquinas
    h_file = logging.FileHandler(log_path, encoding="utf-8")
    h_file.setFormatter(JsonLineFormatter())
    root.addHandler(h_file)

    logger = logging.getLogger("camara")
    logger.info("logging configurado", extra={"run_id": run_id, "log_path": str(log_path)})
    return logger, run_id, log_path
