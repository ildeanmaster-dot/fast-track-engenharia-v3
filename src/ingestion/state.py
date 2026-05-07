"""Controle de estado da ingestao (watermarks por endpoint).

Persiste em JSON simples para iteracao local. Em producao Databricks isso
viraria uma tabela Delta de controle.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_PATH = Path("data/ctl/ingestion_state.json")


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_watermark(endpoint: str) -> str | None:
    state = load_state()
    return state.get(endpoint, {}).get("watermark")


def set_watermark(endpoint: str, watermark: str) -> None:
    state = load_state()
    state.setdefault(endpoint, {})["watermark"] = watermark
    save_state(state)
