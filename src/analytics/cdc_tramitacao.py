"""Opcional 1 - CDC de tramitacao de PLs com SCD2.

Reconstroi o estado de cada proposicao em qualquer ponto do tempo via
intervalo [valid_from, valid_to). Em Databricks, somado ao Delta Time Travel
permite recuperar inclusive alteracoes acidentais da tabela.
"""
from __future__ import annotations

import pandas as pd

ALERTAS_REGEX = {
    "avanco_plenario": r"plen[aá]rio|pronta para pauta|leitura no plen",
    "arquivamento": r"arquiv|encerr",
    "votacao": r"vota[çc][aã]o",
    "promulgacao": r"promulga|sancion",
}


def build_scd2(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Cada tramitacao vira uma versao com valid_from/valid_to/is_current."""
    if "proposicao_tramitacoes" not in silver:
        return pd.DataFrame()

    df = silver["proposicao_tramitacoes"].copy()
    if df.empty or "data_hora" not in df.columns:
        return pd.DataFrame()

    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce", utc=True)
    df = df.dropna(subset=["data_hora"])
    df = df.sort_values(["id_proposicao", "data_hora"]).reset_index(drop=True)

    df["valid_from"] = df["data_hora"]
    df["valid_to"] = df.groupby("id_proposicao")["data_hora"].shift(-1)
    df["is_current"] = df["valid_to"].isna()
    return df


def estado_atual(scd2: pd.DataFrame) -> pd.DataFrame:
    """Vista das proposicoes com a tramitacao mais recente (is_current=True)."""
    if scd2.empty:
        return pd.DataFrame()
    return scd2[scd2["is_current"]].copy().reset_index(drop=True)


def alertas_transicao(scd2: pd.DataFrame) -> pd.DataFrame:
    """Identifica transicoes relevantes (chegada ao Plenario, arquivamento, etc.)."""
    if scd2.empty or "descricao_situacao" not in scd2.columns:
        return pd.DataFrame()

    df = scd2.copy()
    df["tipo_alerta"] = pd.NA
    for tipo, regex in ALERTAS_REGEX.items():
        mask = df["descricao_situacao"].fillna("").str.contains(
            regex, case=False, regex=True
        )
        df.loc[mask & df["tipo_alerta"].isna(), "tipo_alerta"] = tipo

    return df[df["tipo_alerta"].notna()].copy().reset_index(drop=True)


def tempo_medio_tramitacao(scd2: pd.DataFrame, silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tempo medio entre apresentacao e ultima tramitacao por tipo/sigla."""
    if scd2.empty:
        return pd.DataFrame()
    prop = silver["proposicoes"][["id_proposicao", "sigla_tipo", "data_apresentacao"]].copy()
    prop["data_apresentacao"] = pd.to_datetime(prop["data_apresentacao"], errors="coerce", utc=True)

    ultima = (scd2.groupby("id_proposicao")["data_hora"].max()
                  .reset_index(name="ultima_tramitacao"))
    j = prop.merge(ultima, on="id_proposicao", how="inner")
    j["dias_em_tramitacao"] = (j["ultima_tramitacao"] - j["data_apresentacao"]).dt.days
    return (j.groupby("sigla_tipo")["dias_em_tramitacao"]
              .agg(["mean", "median", "count"])
              .reset_index()
              .rename(columns={"mean": "media_dias", "median": "mediana_dias", "count": "n"})
              .sort_values("n", ascending=False))


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    scd2 = build_scd2(silver)
    return {
        "gold_pl_tramitacao_scd2": scd2,
        "gold_pl_estado_atual": estado_atual(scd2),
        "gold_pl_alertas_transicao": alertas_transicao(scd2),
        "gold_pl_tempo_medio_tramitacao": tempo_medio_tramitacao(scd2, silver),
    }
