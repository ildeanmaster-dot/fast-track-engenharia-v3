"""Entregavel 3 - Correlacao frente x votacao.

Compara o alinhamento medio dentro de frentes vs dentro de partidos.
Hipotese: deputados de uma mesma frente votam de forma mais alinhada do que
seus colegas de partido?
"""
from __future__ import annotations

import pandas as pd

VOTOS_VALIDOS = {"Sim", "Nao"}


def _alinhamento_por_grupo(votos: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Para cada (votacao, grupo), calcula % do voto majoritario.

    Considera so Sim/Nao (abstencao/obstrucao ficam de fora).
    """
    df = votos[votos["tipo_voto"].isin(VOTOS_VALIDOS)].copy()
    if df.empty:
        return pd.DataFrame()

    pivot = (df.groupby(["id_votacao", group_col, "tipo_voto"])
               .size()
               .reset_index(name="n")
               .pivot_table(index=["id_votacao", group_col],
                            columns="tipo_voto", values="n",
                            fill_value=0)
               .reset_index())

    for col in ("Sim", "Nao"):
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["total"] = pivot["Sim"] + pivot["Nao"]
    pivot = pivot[pivot["total"] >= 2].copy()
    pivot["alinhamento"] = pivot[["Sim", "Nao"]].max(axis=1) / pivot["total"]
    return pivot


def alinhamento_frente_por_votacao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fm = silver["frente_membros"][["id_frente", "id_deputado"]]
    votos = silver["votacao_votos"].merge(fm, on="id_deputado")
    out = _alinhamento_por_grupo(votos, "id_frente")
    if out.empty:
        return out
    nomes = silver["frentes"][["id_frente", "nome_frente"]]
    return out.merge(nomes, on="id_frente", how="left")


def alinhamento_partido_por_votacao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return _alinhamento_por_grupo(silver["votacao_votos"], "sigla_partido")


def _resumo(detalhe: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if detalhe.empty:
        return pd.DataFrame()
    return (detalhe.groupby(group_col)
                   .agg(alinhamento_medio=("alinhamento", "mean"),
                        qtd_votacoes=("id_votacao", "nunique"))
                   .reset_index()
                   .sort_values("alinhamento_medio", ascending=False))


def comparativo_frente_vs_partido(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabela final: media de alinhamento por frente vs partido majoritario."""
    df_f = alinhamento_frente_por_votacao(silver)
    df_p = alinhamento_partido_por_votacao(silver)
    if df_f.empty or df_p.empty:
        return pd.DataFrame()

    # alinhamento medio por (id_frente)
    media_frente = (df_f.groupby("id_frente")["alinhamento"].mean()
                        .reset_index(name="alinhamento_frente"))

    # partido majoritario de cada frente (a partir do atlas)
    # frente_membros pode ter sigla_partido propria — usamos a do deputado para
    # garantir consistencia
    fm = silver["frente_membros"][["id_frente", "id_deputado"]]
    dep = silver["deputados"][["id_deputado", "sigla_partido"]]
    fm_part = fm.merge(dep, on="id_deputado", how="left")
    partido_majoritario = (fm_part.groupby("id_frente")["sigla_partido"]
                                  .agg(lambda s: s.value_counts().idxmax() if len(s) else None)
                                  .reset_index(name="partido_majoritario"))

    # alinhamento do partido majoritario
    ali_partido = df_p.set_index("sigla_partido")["alinhamento"]
    media_partido_pelo_majoritario = (df_p.groupby("sigla_partido")["alinhamento"].mean()
                                          .reset_index(name="alinhamento_partido_majoritario")
                                          .rename(columns={"sigla_partido": "partido_majoritario"}))

    out = (media_frente
           .merge(partido_majoritario, on="id_frente", how="left")
           .merge(media_partido_pelo_majoritario, on="partido_majoritario", how="left"))
    out["delta_frente_vs_partido"] = (
        out["alinhamento_frente"] - out["alinhamento_partido_majoritario"]
    )
    nomes = silver["frentes"][["id_frente", "nome_frente"]]
    return out.merge(nomes, on="id_frente", how="left").sort_values(
        "delta_frente_vs_partido", ascending=False
    ).reset_index(drop=True)


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    df_f = alinhamento_frente_por_votacao(silver)
    df_p = alinhamento_partido_por_votacao(silver)
    return {
        "gold_alinhamento_frente_por_votacao": df_f,
        "gold_alinhamento_partido_por_votacao": df_p,
        "gold_resumo_alinhamento_frente": _resumo(df_f, "id_frente"),
        "gold_resumo_alinhamento_partido": _resumo(df_p, "sigla_partido"),
        "gold_comparativo_frente_vs_partido": comparativo_frente_vs_partido(silver),
    }
