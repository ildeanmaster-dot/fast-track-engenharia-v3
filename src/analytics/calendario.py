"""Entregavel 2 - Calendario analitico de eventos.

Tabelas geradas:
    gold_taxa_presenca_deputado     - taxa de presenca por deputado
    gold_taxa_presenca_por_tipo     - presencas por tipo de evento
    gold_densidade_semanal          - eventos por semana
    gold_semanas_sem_atividade      - semanas vazias no range coberto
    gold_eventos_futuros            - eventos com data futura
    gold_pre_pos_eleitoral          - comparativo de frequencia pre/pos eleicoes
"""
from __future__ import annotations

import pandas as pd

# marcos eleitorais (1o turno e 2o turno) - usado pra comparativo pre/pos
MARCOS_ELEITORAIS_2024 = (pd.Timestamp("2024-10-06", tz="UTC"),
                          pd.Timestamp("2024-10-27", tz="UTC"))


def taxa_presenca_deputado(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    eventos = silver["eventos"]["id_evento"]
    total = eventos.nunique()
    if total == 0:
        return pd.DataFrame()

    presencas = (silver["evento_deputados"]
                 .groupby("id_deputado").size()
                 .reset_index(name="n_presencas"))
    presencas["total_eventos"] = total
    presencas["taxa_presenca"] = presencas["n_presencas"] / total

    dep = silver["deputados"][["id_deputado", "nome", "sigla_partido", "sigla_uf"]]
    return (presencas.merge(dep, on="id_deputado", how="left")
                     .sort_values("taxa_presenca", ascending=False)
                     .reset_index(drop=True))


def taxa_presenca_por_tipo(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    ev = silver["eventos"][["id_evento", "descricao_tipo"]]
    ed = silver["evento_deputados"][["id_evento", "id_deputado"]]
    j = ed.merge(ev, on="id_evento", how="left")
    return (j.groupby("descricao_tipo")
             .agg(n_eventos=("id_evento", "nunique"),
                  total_presencas=("id_deputado", "count"),
                  deputados_distintos=("id_deputado", "nunique"))
             .reset_index()
             .sort_values("total_presencas", ascending=False))


def densidade_semanal(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = silver["eventos"].copy()
    df["data_hora_inicio"] = pd.to_datetime(df["data_hora_inicio"], errors="coerce", utc=True)
    df = df.dropna(subset=["data_hora_inicio"])
    iso = df["data_hora_inicio"].dt.isocalendar()
    df["ano"] = iso.year
    df["semana"] = iso.week
    return (df.groupby(["ano", "semana"])
              .size()
              .reset_index(name="qtd_eventos")
              .sort_values(["ano", "semana"])
              .reset_index(drop=True))


def semanas_sem_atividade(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    densidade = densidade_semanal(silver)
    if densidade.empty:
        return pd.DataFrame(columns=["ano", "semana"])

    pares = set(zip(densidade["ano"], densidade["semana"]))
    ano_min = int(densidade["ano"].min())
    ano_max = int(densidade["ano"].max())
    sem: list[dict] = []
    for ano in range(ano_min, ano_max + 1):
        for s in range(1, 54):
            if (ano, s) not in pares:
                sem.append({"ano": ano, "semana": s})
    return pd.DataFrame(sem)


def eventos_futuros(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = silver["eventos"].copy()
    df["data_hora_inicio"] = pd.to_datetime(df["data_hora_inicio"], errors="coerce", utc=True)
    futuros = df[df["data_hora_inicio"] > pd.Timestamp.utcnow()].copy()
    cols = ["id_evento", "data_hora_inicio", "data_hora_fim",
            "descricao_tipo", "situacao", "descricao"]
    return futuros[[c for c in cols if c in futuros.columns]] \
        .sort_values("data_hora_inicio").reset_index(drop=True)


def pre_pos_eleitoral(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compara frequencia de eventos antes e depois das eleicoes 2024."""
    primeira_eleicao, _ = MARCOS_ELEITORAIS_2024
    df = silver["eventos"].copy()
    df["data_hora_inicio"] = pd.to_datetime(df["data_hora_inicio"], errors="coerce", utc=True)
    df = df.dropna(subset=["data_hora_inicio"])

    df["periodo"] = df["data_hora_inicio"].apply(
        lambda ts: "pos_eleicao" if ts > primeira_eleicao else "pre_eleicao"
    )

    return (df.groupby("periodo")
              .agg(n_eventos=("id_evento", "nunique"),
                   data_min=("data_hora_inicio", "min"),
                   data_max=("data_hora_inicio", "max"))
              .reset_index())


def build_all(silver: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "gold_taxa_presenca_deputado": taxa_presenca_deputado(silver),
        "gold_taxa_presenca_por_tipo": taxa_presenca_por_tipo(silver),
        "gold_densidade_semanal": densidade_semanal(silver),
        "gold_semanas_sem_atividade": semanas_sem_atividade(silver),
        "gold_eventos_futuros": eventos_futuros(silver),
        "gold_pre_pos_eleitoral": pre_pos_eleitoral(silver),
    }
