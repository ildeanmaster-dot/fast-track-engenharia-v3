"""Entregavel 5 - Auditoria de CPIs.

Tabelas geradas:
    gold_cpi_catalogo       - identificacao + duracao
    gold_cpi_membros        - convocados (membros do orgao CPI)
    gold_cpi_eventos        - timeline de eventos do CPI
    gold_cpi_legislacao     - legislacao derivada (heuristica via ementa)
    gold_cpi_produtividade  - relatorio gerado vs encerrada sem conclusao
"""
from __future__ import annotations

import pandas as pd

CPI_REGEX = r"CPI|CPMI|Inqu[eé]rito"
PRAZO_REGIMENTAL_DIAS = 180


def identificar_cpis(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = silver["orgaos"].copy()
    mask = df["nome_orgao"].fillna("").str.contains(
        CPI_REGEX, case=False, regex=True, na=False
    )
    cpis = df[mask].copy()

    for col in ("data_inicio", "data_fim"):
        if col not in cpis.columns:
            cpis[col] = pd.NaT

    if cpis.empty:
        return pd.DataFrame(columns=[
            "id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao",
            "data_inicio", "data_fim", "duracao_dias", "excedeu_prazo", "encerrada",
        ])

    cpis["data_inicio"] = pd.to_datetime(cpis["data_inicio"], errors="coerce")
    cpis["data_fim"] = pd.to_datetime(cpis["data_fim"], errors="coerce")
    cpis["duracao_dias"] = (cpis["data_fim"] - cpis["data_inicio"]).dt.days
    cpis["excedeu_prazo"] = cpis["duracao_dias"].fillna(0) > PRAZO_REGIMENTAL_DIAS
    cpis["encerrada"] = cpis["data_fim"].notna()

    return cpis[[
        "id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao",
        "data_inicio", "data_fim", "duracao_dias", "excedeu_prazo", "encerrada",
    ]].reset_index(drop=True)


def cpi_membros(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Membros das CPIs identificadas."""
    cpis = identificar_cpis(silver)
    if cpis.empty or "orgao_membros" not in silver or silver["orgao_membros"].empty:
        return pd.DataFrame()

    membros = silver["orgao_membros"]
    return membros.merge(
        cpis[["id_orgao", "sigla_orgao", "nome_orgao"]],
        on="id_orgao", how="inner"
    ).reset_index(drop=True)


def cpi_eventos(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Eventos vinculados as CPIs identificadas."""
    cpis = identificar_cpis(silver)
    if cpis.empty or "orgao_eventos" not in silver or silver["orgao_eventos"].empty:
        return pd.DataFrame()

    eventos = silver["orgao_eventos"].rename(columns={"id_orgao_pai": "id_orgao"})
    return eventos.merge(
        cpis[["id_orgao", "sigla_orgao"]],
        on="id_orgao", how="inner"
    ).reset_index(drop=True)


def cpi_legislacao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Legislacao derivada de CPIs (heuristica via match de sigla na ementa)."""
    cpis = identificar_cpis(silver)
    if cpis.empty or "proposicoes" not in silver:
        return pd.DataFrame()

    prop = silver["proposicoes"]
    if "ementa" not in prop.columns or prop.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for _, cpi in cpis.iterrows():
        sigla = cpi.get("sigla_orgao") or ""
        if not sigla:
            continue
        match = prop[prop["ementa"].fillna("").str.contains(sigla, case=False, na=False)]
        for _, p in match.iterrows():
            rows.append({
                "id_cpi": cpi["id_orgao"],
                "sigla_cpi": sigla,
                "id_proposicao": p["id_proposicao"],
                "sigla_tipo": p.get("sigla_tipo"),
                "ementa_resumo": (p.get("ementa") or "")[:200],
            })
    return pd.DataFrame(rows)


def cpi_produtividade(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Comparativo: CPIs com legislacao derivada vs sem."""
    cpis = identificar_cpis(silver)
    if cpis.empty:
        return pd.DataFrame()
    legislacao = cpi_legislacao(silver)
    if legislacao.empty:
        cpis["qtd_legislacao"] = 0
    else:
        agg = legislacao.groupby("id_cpi").size().reset_index(name="qtd_legislacao")
        cpis = cpis.merge(agg, left_on="id_orgao", right_on="id_cpi", how="left") \
                   .drop(columns=["id_cpi"])
        cpis["qtd_legislacao"] = cpis["qtd_legislacao"].fillna(0).astype(int)
    cpis["produtiva"] = cpis["qtd_legislacao"] > 0
    return cpis


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "gold_cpi_catalogo": identificar_cpis(silver),
        "gold_cpi_membros": cpi_membros(silver),
        "gold_cpi_eventos": cpi_eventos(silver),
        "gold_cpi_legislacao": cpi_legislacao(silver),
        "gold_cpi_produtividade": cpi_produtividade(silver),
    }
