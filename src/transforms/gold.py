"""Camada Gold: dimensoes + fatos do star schema.

Os entregaveis analiticos sao construidos sobre essas tabelas em
src/analytics/. Aqui ficam apenas dimensoes/fatos compartilhados.
"""
from __future__ import annotations

import pandas as pd


def dim_deputado(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Dimensao deputado: chave + atributos descritivos."""
    cols = ["id_deputado", "nome", "sigla_partido", "sigla_uf",
            "id_legislatura", "email"]
    df = silver["deputados"]
    return df[[c for c in cols if c in df.columns]].copy()


def dim_partido(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = ["id_partido", "sigla_partido", "nome_partido"]
    df = silver["partidos"]
    return df[[c for c in cols if c in df.columns]].copy()


def dim_frente(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = ["id_frente", "nome_frente", "id_legislatura"]
    df = silver["frentes"]
    return df[[c for c in cols if c in df.columns]].copy()


def dim_orgao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = ["id_orgao", "sigla_orgao", "nome_orgao", "tipo_orgao",
            "cod_tipo_orgao", "data_inicio", "data_fim"]
    df = silver["orgaos"]
    return df[[c for c in cols if c in df.columns]].copy()


def dim_evento(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = ["id_evento", "data_hora_inicio", "data_hora_fim",
            "descricao_tipo", "situacao"]
    df = silver["eventos"]
    return df[[c for c in cols if c in df.columns]].copy()


def dim_fornecedor(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Dimensao fornecedor derivada das despesas (snapshot)."""
    desp = silver.get("deputado_despesas")
    if desp is None or desp.empty:
        return pd.DataFrame(columns=["cnpj_fornecedor", "nome_fornecedor"])
    return (desp[["cnpj_fornecedor", "nome_fornecedor"]]
            .dropna(subset=["cnpj_fornecedor"])
            .drop_duplicates(subset=["cnpj_fornecedor"], keep="last")
            .reset_index(drop=True))


def dim_data(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Dimensao calendario com derivadas uteis."""
    timestamps: list[pd.Series] = []
    for ent, col in [
        ("eventos", "data_hora_inicio"),
        ("votacoes", "data_hora_registro"),
        ("deputado_despesas", "data_documento"),
    ]:
        if ent in silver and col in silver[ent].columns:
            timestamps.append(silver[ent][col])

    if not timestamps:
        return pd.DataFrame(columns=["data", "ano", "mes", "dia", "semana", "dia_semana", "trimestre"])

    all_ts = pd.concat(timestamps).dropna()
    if all_ts.empty:
        return pd.DataFrame(columns=["data", "ano", "mes", "dia", "semana", "dia_semana", "trimestre"])

    dias = pd.to_datetime(all_ts, utc=True).dt.normalize().drop_duplicates().sort_values()
    return pd.DataFrame({
        "data": dias.dt.date,
        "ano": dias.dt.year.values,
        "mes": dias.dt.month.values,
        "dia": dias.dt.day.values,
        "semana": dias.dt.isocalendar().week.values,
        "dia_semana": dias.dt.day_name().values,
        "trimestre": dias.dt.quarter.values,
    }).reset_index(drop=True)


# ---------- Fatos ----------

def fato_voto(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Voto individual em cada votacao."""
    df = silver["votacao_votos"]
    cols = ["id_votacao", "id_deputado", "tipo_voto", "data_registro_voto",
            "sigla_partido", "sigla_uf"]
    return df[[c for c in cols if c in df.columns]].copy()


def fato_presenca(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Deputados que apareceram em cada evento."""
    df = silver["evento_deputados"]
    cols = ["id_evento", "id_deputado", "sigla_partido", "sigla_uf"]
    return df[[c for c in cols if c in df.columns]].copy()


def fato_despesa(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Despesas CEAP com chaves para junctions."""
    df = silver["deputado_despesas"]
    cols = ["id_deputado", "ano", "mes", "tipo_despesa", "valor_liquido",
            "valor_documento", "valor_glosa",
            "nome_fornecedor", "cnpj_fornecedor",
            "data_documento", "cod_documento"]
    return df[[c for c in cols if c in df.columns]].copy()


def fato_tramitacao(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Eventos de tramitacao das proposicoes."""
    df = silver.get("proposicao_tramitacoes")
    if df is None or df.empty:
        return pd.DataFrame()
    cols = ["id_proposicao", "sequencia", "data_hora",
            "sigla_orgao", "descricao_situacao", "descricao_tramitacao"]
    return df[[c for c in cols if c in df.columns]].copy()
