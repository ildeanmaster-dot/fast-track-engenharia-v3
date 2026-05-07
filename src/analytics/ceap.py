"""Entregavel 4 - Raio-X CEAP com z-score e flag CNPJ.

Tabelas geradas:
    gold_ceap_anomalias            - z-score por (tipo_despesa, sigla_uf)
    gold_ceap_ranking_fornecedor   - top fornecedores com flag suspeito
    gold_ceap_mensal_partido       - relatorio mensal por partido
    gold_ceap_top10_partido_mes    - top 10 gastos por (partido, mes)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.quality.cnpj import flag_suspeitos


def _aplica_z_score(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> pd.DataFrame:
    """Adiciona colunas media_grupo, std_grupo, z_score, outlier."""
    grupo = df.groupby(group_cols)[value_col]
    df = df.copy()
    df["media_grupo"] = grupo.transform("mean")
    df["std_grupo"] = grupo.transform("std")
    # divisao segura: se std e 0 ou nan, z_score fica nan
    safe_std = df["std_grupo"].replace(0, np.nan)
    df["z_score"] = (df[value_col] - df["media_grupo"]) / safe_std
    df["outlier"] = df["z_score"].abs() > 3
    return df


def ceap_anomalias(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Z-score do valor_liquido particionado por (tipo_despesa, sigla_uf)."""
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()

    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    df = df.merge(dep, on="id_deputado", how="left")
    df = _aplica_z_score(df, "valor_liquido", ["tipo_despesa", "sigla_uf"])

    cols = [
        "id_deputado", "nome", "sigla_partido", "sigla_uf",
        "ano", "mes", "tipo_despesa", "valor_liquido",
        "nome_fornecedor", "cnpj_fornecedor",
        "media_grupo", "std_grupo", "z_score", "outlier",
    ]
    return df[[c for c in cols if c in df.columns]].copy()


def ceap_ranking_fornecedor(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Ranking de fornecedores com flags de suspeita (DV CNPJ + heuristicas)."""
    return flag_suspeitos(silver["deputado_despesas"], silver["deputados"]).head(200)


def ceap_mensal_partido(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Total CEAP por partido por mes."""
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()
    dep = silver["deputados"][["id_deputado", "sigla_partido"]]
    df = df.merge(dep, on="id_deputado", how="left")
    return (df.groupby(["ano", "mes", "sigla_partido"])
              .agg(total=("valor_liquido", "sum"),
                   qtd=("cod_documento", "count"),
                   deputados=("id_deputado", "nunique"))
              .reset_index()
              .sort_values(["ano", "mes", "total"], ascending=[True, True, False]))


def ceap_top10_partido_mes(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Top 10 gastos individuais por (partido, mes) - relatorio mensal."""
    df = silver["deputado_despesas"].copy()
    if df.empty:
        return pd.DataFrame()
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido"]]
    df = df.merge(dep, on="id_deputado", how="left")
    df["rank"] = (df.groupby(["ano", "mes", "sigla_partido"])["valor_liquido"]
                    .rank(method="first", ascending=False))
    return (df[df["rank"] <= 10]
              .sort_values(["ano", "mes", "sigla_partido", "rank"])
              .reset_index(drop=True))


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "gold_ceap_anomalias": ceap_anomalias(silver),
        "gold_ceap_ranking_fornecedor": ceap_ranking_fornecedor(silver),
        "gold_ceap_mensal_partido": ceap_mensal_partido(silver),
        "gold_ceap_top10_partido_mes": ceap_top10_partido_mes(silver),
    }
