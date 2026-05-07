"""Camada Bronze: persiste payloads da API como JSONL com auditoria.

A versao Spark (notebook 01) le esses JSONL e converte para Delta no Volume.
Cada registro recebe um campo `_audit` com metadados de ingestao.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingestion.api_client import CamaraAPIClient, Page
from src.utils.config_loader import APIConfig, EndpointConfig
from src.utils.hashing import stable_hash

logger = logging.getLogger(__name__)
SAMPLES_DIR = Path("data/samples")


def _audit_block(endpoint_name: str, page: Page, run_id: str) -> dict[str, Any]:
    return {
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint_name,
        "source_url": page.source_url,
        "page_number": page.page_number,
        "run_id": run_id,
    }


def collect_simple(
    client: CamaraAPIClient,
    endpoint: EndpointConfig,
    run_id: str,
    max_pages: int | None = None,
) -> int:
    """Coleta endpoint paginado simples e grava em JSONL."""
    out_path = SAMPLES_DIR / f"{endpoint.name}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for page in client.iter_pages(endpoint, max_pages=max_pages):
            audit = _audit_block(endpoint.name, page, run_id)
            for record in page.records:
                record["_audit"] = audit
                record["_payload_hash"] = stable_hash(
                    {k: v for k, v in record.items() if not k.startswith("_")}
                )
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                n += 1

    logger.info(
        "bronze coletado",
        extra={"endpoint": endpoint.name, "registros": n, "path": str(out_path)},
    )
    return n


def _load_parent_ids(parent_endpoint: str) -> list[Any]:
    path = SAMPLES_DIR / f"{parent_endpoint}.jsonl"
    if not path.exists():
        raise RuntimeError(
            f"pai '{parent_endpoint}' nao foi coletado ainda — "
            f"ingerir antes do fanout"
        )
    ids: list[Any] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            if "id" in obj:
                ids.append(obj["id"])
    return ids


def collect_fanout(
    client: CamaraAPIClient,
    endpoint: EndpointConfig,
    run_id: str,
    max_parents: int = 30,
) -> int:
    """Coleta endpoint que depende de id do pai (1:N)."""
    if not endpoint.fanout_from:
        raise ValueError(f"{endpoint.name} nao tem fanout_from configurado")

    parent_ids = _load_parent_ids(endpoint.fanout_from)[:max_parents]

    out_path = SAMPLES_DIR / f"{endpoint.name}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for parent_id in parent_ids:
            try:
                for page in client.iter_pages(endpoint, path_params={"id": parent_id}):
                    audit = _audit_block(endpoint.name, page, run_id)
                    for record in page.records:
                        record["_parent_id"] = parent_id
                        record["_audit"] = audit
                        record["_payload_hash"] = stable_hash(
                            {k: v for k, v in record.items() if not k.startswith("_")}
                        )
                        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                        total += 1
            except Exception as exc:
                # registra mas nao quebra a coleta
                logger.warning(
                    "fanout falhou",
                    extra={"endpoint": endpoint.name, "parent_id": parent_id, "erro": str(exc)},
                )

    logger.info(
        "bronze fanout coletado",
        extra={"endpoint": endpoint.name, "registros": total, "parents": len(parent_ids)},
    )
    return total


def collect_all(
    config: APIConfig,
    run_id: str,
    max_pages_simple: int = 2,
) -> dict[str, int]:
    """Coleta todas as entidades respeitando ordem topologica."""
    client = CamaraAPIClient(config)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, int] = {}

    # primeiro os simples
    simples = [name for name, ep in config.endpoints.items() if ep.fanout_from is None]
    for name in simples:
        ep = config.endpoints[name]
        try:
            results[name] = collect_simple(client, ep, run_id, max_pages=max_pages_simple)
        except Exception as exc:
            logger.error("falha em %s: %s", name, exc, extra={"endpoint": name})
            results[name] = 0

    # depois os fanouts
    fanouts = [name for name, ep in config.endpoints.items() if ep.fanout_from]
    for name in fanouts:
        ep = config.endpoints[name]
        max_parents = config.fanout_limits.get(name, 30)
        try:
            results[name] = collect_fanout(client, ep, run_id, max_parents=max_parents)
        except Exception as exc:
            logger.error("falha em %s: %s", name, exc, extra={"endpoint": name})
            results[name] = 0

    return results
