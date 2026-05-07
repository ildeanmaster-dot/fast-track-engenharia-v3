"""Carregamento e validacao do catalogo de endpoints YAML.

O catalogo e a "fonte da verdade" sobre quais endpoints existem, suas
estrategias incrementais e suas chaves primarias. O cliente HTTP e a camada
Bronze consomem dessas estruturas tipadas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_INCREMENTALS = {
    "snapshot",
    "append",
    "append_watermark",
    "merge_by_hash",
    "scd2_by_hash",
}


@dataclass(frozen=True)
class EndpointConfig:
    """Configuracao de um endpoint da API."""

    name: str
    path: str
    params: dict[str, Any] = field(default_factory=dict)
    paginated: bool = True
    pk: list[str] = field(default_factory=list)
    incremental: str = "snapshot"
    watermark: list[str] = field(default_factory=list)
    fanout_from: str | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.incremental not in VALID_INCREMENTALS:
            raise ValueError(
                f"endpoint {self.name}: incremental invalido '{self.incremental}'. "
                f"Validos: {sorted(VALID_INCREMENTALS)}"
            )
        if self.incremental == "append_watermark" and not self.watermark:
            raise ValueError(
                f"endpoint {self.name}: append_watermark requer 'watermark'"
            )


@dataclass(frozen=True)
class APIConfig:
    """Configuracao geral da API."""

    base_url: str
    user_agent: str
    timeout: int
    max_retries: int
    rate_limit_rpm: int
    endpoints: dict[str, EndpointConfig]
    fanout_limits: dict[str, int]


def load(path: str | Path = "conf/endpoints.yaml") -> APIConfig:
    """Le e valida o YAML de configuracao."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    api = raw.get("api") or {}
    eps_raw = raw.get("endpoints") or {}

    eps = {name: EndpointConfig(name=name, **cfg) for name, cfg in eps_raw.items()}

    # validacao adicional: fanouts apontam pra pais existentes
    for name, ep in eps.items():
        if ep.fanout_from and ep.fanout_from not in eps:
            raise ValueError(
                f"endpoint {name}: fanout_from='{ep.fanout_from}' nao existe"
            )

    return APIConfig(
        base_url=str(api.get("base_url", "")).rstrip("/"),
        user_agent=str(api.get("user_agent", "camara-lakehouse/0.1")),
        timeout=int(api.get("timeout", 30)),
        max_retries=int(api.get("max_retries", 5)),
        rate_limit_rpm=int(api.get("rate_limit_rpm", 180)),
        endpoints=eps,
        fanout_limits=raw.get("fanout_limits", {}) or {},
    )


def load_ideologia(path: str | Path = "conf/ideologia_partidos.yaml") -> dict[str, Any]:
    """Le mapa ideologico dos partidos."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
