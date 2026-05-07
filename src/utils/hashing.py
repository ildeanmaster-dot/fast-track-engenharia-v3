"""Hashing deterministico de payloads para deteccao de mudanca."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(obj: Any) -> str:
    """Gera SHA-256 hex de um objeto JSON-serializavel.

    Estavel: re-rodar com mesmo input produz mesmo hash. Usado para detectar
    mudanca de payload no merge_by_hash e no SCD2.
    """
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
