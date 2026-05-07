"""Entregavel 1 - Atlas das frentes parlamentares.

Tabelas geradas:
    gold_atlas_frentes              - membros das frentes enriquecidos
    gold_frente_diversidade         - HHI por frente (concentracao partidaria)
    gold_deputados_em_n_frentes     - top deputados por numero de frentes
    gold_sobreposicao_frentes       - pares de frentes com membros em comum
    gold_frentes_opostas            - sobreposicao entre frentes ideologicamente opostas
    gold_frentes_por_legislatura    - evolucao do numero de frentes por legislatura
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def atlas_frentes(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Membros das frentes com partido/UF do deputado."""
    fr = silver["frentes"][["id_frente", "nome_frente", "id_legislatura"]]
    fm = silver["frente_membros"][["id_frente", "id_deputado"]]
    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    return (fm.merge(dep, on="id_deputado", how="left")
              .merge(fr, on="id_frente", how="left"))


def hhi_por_frente(atlas: pd.DataFrame) -> pd.DataFrame:
    """Indice de Herfindahl-Hirschman por frente.

    HHI = soma((share_i)^2) onde share_i e a fracao de membros do partido i.
    Vai de 1/N (uniforme) a 1.0 (todos do mesmo partido).
    """
    rows: list[dict[str, Any]] = []
    for fid, grp in atlas.groupby("id_frente"):
        total = len(grp)
        if total == 0:
            continue
        partidos = grp["sigla_partido"].fillna("?").value_counts()
        shares = partidos / total
        rows.append({
            "id_frente": fid,
            "nome_frente": grp["nome_frente"].iloc[0],
            "n_membros": int(total),
            "n_partidos": int((partidos > 0).sum()),
            "n_ufs": grp["sigla_uf"].fillna("?").nunique(),
            "hhi": float((shares ** 2).sum()),
            "diversidade_score": float(1 - (shares ** 2).sum()),  # 1 - HHI
        })
    return pd.DataFrame(rows).sort_values("hhi").reset_index(drop=True)


def deputados_em_n_frentes(atlas: pd.DataFrame, top: int = 50) -> pd.DataFrame:
    return (atlas.groupby(["id_deputado", "nome", "sigla_partido", "sigla_uf"])
                 .size()
                 .reset_index(name="n_frentes")
                 .sort_values("n_frentes", ascending=False)
                 .head(top)
                 .reset_index(drop=True))


def sobreposicao_frentes(atlas: pd.DataFrame, min_overlap: int = 5) -> pd.DataFrame:
    """Pares de frentes (a, b) com >= min_overlap membros em comum."""
    membros: dict[Any, set] = (
        atlas.groupby("id_frente")["id_deputado"].apply(set).to_dict()
    )
    nomes: dict[Any, str] = atlas.set_index("id_frente")["nome_frente"].to_dict()

    rows: list[dict[str, Any]] = []
    fids = sorted(membros.keys())
    for i, a in enumerate(fids):
        for b in fids[i + 1:]:
            inter = len(membros[a] & membros[b])
            if inter >= min_overlap:
                rows.append({
                    "frente_a": a, "nome_a": nomes.get(a),
                    "frente_b": b, "nome_b": nomes.get(b),
                    "membros_comum": inter,
                })
    return (pd.DataFrame(rows)
            .sort_values("membros_comum", ascending=False)
            .reset_index(drop=True))


def frentes_ideologicamente_opostas(
    sobreposicao: pd.DataFrame,
    atlas: pd.DataFrame,
    ideologia: dict[str, Any],
) -> pd.DataFrame:
    """Para cada par de frentes com membros em comum, calcula a distancia
    ideologica medias dos membros e flagga as opostas."""
    if sobreposicao.empty:
        return pd.DataFrame()

    partidos_map: dict[str, int] = ideologia.get("partidos") or {}
    distancia_min: int = ideologia.get("distancia_minima_oposicao", 3)

    # eixo medio por frente
    atlas_eixo = atlas.copy()
    atlas_eixo["eixo"] = atlas_eixo["sigla_partido"].map(partidos_map)
    eixo_por_frente = (atlas_eixo.dropna(subset=["eixo"])
                                  .groupby("id_frente")["eixo"]
                                  .mean())

    rows: list[dict[str, Any]] = []
    for _, par in sobreposicao.iterrows():
        a, b = par["frente_a"], par["frente_b"]
        ea = eixo_por_frente.get(a)
        eb = eixo_por_frente.get(b)
        if pd.isna(ea) or pd.isna(eb):
            continue
        distancia = abs(ea - eb)
        if distancia >= distancia_min:
            rows.append({
                **par.to_dict(),
                "eixo_a": float(ea),
                "eixo_b": float(eb),
                "distancia_ideologica": float(distancia),
            })
    if not rows:
        return pd.DataFrame(columns=[
            "frente_a", "nome_a", "frente_b", "nome_b", "membros_comum",
            "eixo_a", "eixo_b", "distancia_ideologica",
        ])
    return (pd.DataFrame(rows)
            .sort_values("distancia_ideologica", ascending=False)
            .reset_index(drop=True))


def frentes_por_legislatura(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fr = silver["frentes"]
    return (fr.groupby("id_legislatura")["id_frente"]
              .nunique()
              .reset_index(name="qtd_frentes")
              .sort_values("id_legislatura"))


def build_all(
    silver: dict[str, pd.DataFrame], ideologia: dict[str, Any]
) -> dict[str, pd.DataFrame]:
    atlas = atlas_frentes(silver)
    sobreposicao = sobreposicao_frentes(atlas)
    return {
        "gold_atlas_frentes": atlas,
        "gold_frente_diversidade": hhi_por_frente(atlas),
        "gold_deputados_em_n_frentes": deputados_em_n_frentes(atlas),
        "gold_sobreposicao_frentes": sobreposicao,
        "gold_frentes_opostas":
            frentes_ideologicamente_opostas(sobreposicao, atlas, ideologia),
        "gold_frentes_por_legislatura": frentes_por_legislatura(silver),
    }
