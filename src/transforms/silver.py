"""Camada Silver: bronze JSONL -> DataFrame com schema canonico.

Aplica em ordem:
    1. Achatamento de objetos aninhados (json_normalize)
    2. Tratamento especial (votacao_votos.deputado_)
    3. Remocao de metadados internos (_audit, _payload_hash)
    4. Rename para snake_case (RENAMES)
    5. Parse temporal (TEMPORAL_COLS)
    6. Dedup pela PK (drop_duplicates keep="last")
    7. Adicao de colunas de auditoria silver
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.transforms.schemas import PKS, RENAMES, TEMPORAL_COLS

SAMPLES_DIR = Path("data/samples")


def _read_jsonl(name: str) -> list[dict]:
    path = SAMPLES_DIR / f"{name}.jsonl"
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _flatten_voto_deputado(record: dict) -> dict:
    """Em /votacoes/{id}/votos cada voto tem objeto deputado_ aninhado."""
    if "deputado_" in record and isinstance(record["deputado_"], dict):
        deputado = record.pop("deputado_")
        record["id_deputado"] = deputado.get("id")
        record["nome_deputado"] = deputado.get("nome")
        record["sigla_partido"] = deputado.get("siglaPartido")
        record["sigla_uf"] = deputado.get("siglaUf")
    return record


def to_silver(name: str, run_id: str = "local") -> pd.DataFrame:
    """Converte uma entidade do bronze para silver."""
    raw = _read_jsonl(name)
    if not raw:
        return pd.DataFrame()

    if name == "votacao_votos":
        raw = [_flatten_voto_deputado(r) for r in raw]

    df = pd.json_normalize(raw, sep="_")

    # captura payload_hash bronze antes de droppar metadados
    payload_hash = df["_payload_hash"] if "_payload_hash" in df.columns else None

    # tira metadados internos
    drop_cols = [c for c in df.columns if c.startswith("_audit") or c == "_payload_hash"]
    df = df.drop(columns=drop_cols, errors="ignore")

    # rename para silver
    df = df.rename(columns=RENAMES.get(name, {}))

    # parse temporal
    for col, kind in TEMPORAL_COLS.get(name, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=(kind == "ts"))

    # dedup pela PK
    pk = PKS.get(name)
    if pk and all(c in df.columns for c in pk):
        df = df.drop_duplicates(subset=pk, keep="last").reset_index(drop=True)

    # auditoria silver
    df["silver_ingest_ts"] = datetime.now(timezone.utc)
    df["run_id"] = run_id
    if payload_hash is not None:
        df["payload_hash"] = payload_hash[: len(df)].reset_index(drop=True)

    return df


def to_silver_all(run_id: str = "local") -> dict[str, pd.DataFrame]:
    """Roda silver para todas as entidades cujo bronze existe."""
    out: dict[str, pd.DataFrame] = {}
    for name in RENAMES:
        try:
            out[name] = to_silver(name, run_id=run_id)
        except FileNotFoundError:
            pass
    return out
