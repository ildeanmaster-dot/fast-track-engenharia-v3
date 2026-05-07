"""Opcional 2 - Streaming de votacoes com classificacao de urgencia.

Em producao seria um job agendado a cada 10 min consumindo /votacoes via
ID watermark. Aqui o "tick" e implementado como funcao reusavel que pode
rodar tanto em Structured Streaming (Databricks) quanto em loop CLI local.

Saidas:
    gold_alertas_votacao    - alertas classificados (urgencia + tipo)
    gold_sla_streaming      - metricas de execucao por tick (latencia, erros)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

URGENCIA_REGEX = re.compile(
    r"urg[eê]ncia|emergen|plen[aá]rio|destaque|acordo de l[ií]deres|prioridade",
    re.IGNORECASE,
)


def classifica_urgencia(descricao: str | None) -> str:
    if not descricao:
        return "normal"
    return "urgente" if URGENCIA_REGEX.search(descricao) else "normal"


@dataclass
class TickMetrics:
    """SLA de uma execucao do tick."""

    run_id: str
    new_records: int
    urgentes: int
    duration_ms: int
    errors: int
    status: str  # "ok" ou "failed"


def alertas_votacao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabela de alertas (uma linha por votacao com classificacao de urgencia)."""
    df = silver["votacoes"].copy()
    if df.empty or "descricao" not in df.columns:
        return pd.DataFrame()

    df["urgencia"] = df["descricao"].apply(classifica_urgencia)
    cols = ["id_votacao", "data_hora_registro", "descricao", "urgencia"]
    return df[[c for c in cols if c in df.columns]].sort_values(
        "data_hora_registro", ascending=False
    ).reset_index(drop=True)


def sla_dashboard(metrics: list[TickMetrics]) -> pd.DataFrame:
    """Resumo das execucoes de tick."""
    if not metrics:
        return pd.DataFrame()
    return pd.DataFrame([m.__dict__ for m in metrics])


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "gold_alertas_votacao": alertas_votacao(silver),
    }
