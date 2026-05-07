"""Validacao de CNPJ + heuristicas de "fornecedor suspeito".

Validacao real na Receita Federal exige CAPTCHA ou WS autenticado, fora do
escopo de uma integracao de API publica. Aqui temos:

1. **Validacao sintatica** com calculo de digitos verificadores (DV).
2. **Heuristicas** detectaveis com dados publicos:
   - mesmo CNPJ servindo deputados de muitas UFs distintas
   - valor medio bem acima do desvio do setor
   - CNPJ malformado/sequencial

Integracao com fonte autorizada da Receita pode ser plugada em
`enrich_with_cnpj_public_api()` (hoje no-op).
"""
from __future__ import annotations

import re

import pandas as pd

CNPJ_FAKE = re.compile(r"^(\d)\1{13}$")


def limpa_cnpj(raw: str | None) -> str | None:
    """Remove tudo que nao for digito. Retorna None se vazio."""
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    return digits or None


def _calc_dv(digits: str, peso_inicial: int) -> int:
    """Calculo de DV por modulo 11. peso_inicial=5 para DV1, =6 para DV2."""
    pesos = list(range(peso_inicial, 1, -1)) + [9, 8, 7, 6, 5, 4, 3, 2]
    pesos = pesos[: len(digits)]
    total = sum(int(d) * p for d, p in zip(digits, pesos, strict=False))
    resto = total % 11
    return 0 if resto < 2 else 11 - resto


def valida_cnpj(raw: str | None) -> bool:
    """True se CNPJ e sintaticamente valido (14 digitos, DVs corretos)."""
    digits = limpa_cnpj(raw)
    if digits is None or len(digits) != 14:
        return False
    if CNPJ_FAKE.match(digits):
        return False
    base = digits[:12]
    dv1_calc = _calc_dv(base, peso_inicial=5)
    dv2_calc = _calc_dv(base + str(dv1_calc), peso_inicial=6)
    return digits[12] == str(dv1_calc) and digits[13] == str(dv2_calc)


def flag_suspeitos(despesas: pd.DataFrame, deputados: pd.DataFrame) -> pd.DataFrame:
    """Por CNPJ, agrega metricas e flags heuristicos de suspeita."""
    if despesas.empty:
        return pd.DataFrame()

    enriched = despesas.merge(
        deputados[["id_deputado", "sigla_uf"]], on="id_deputado", how="left"
    )

    agg = (enriched.groupby(["cnpj_fornecedor", "nome_fornecedor"], dropna=False)
                   .agg(valor_total=("valor_liquido", "sum"),
                        qtd_documentos=("cod_documento", "count"),
                        qtd_deputados=("id_deputado", "nunique"),
                        ufs_atendidas=("sigla_uf", "nunique"),
                        valor_medio=("valor_liquido", "mean"))
                   .reset_index())

    # validacao sintatica
    agg["cnpj_valido"] = agg["cnpj_fornecedor"].apply(valida_cnpj)

    # heuristica multi-UF
    agg["flag_multi_uf"] = agg["ufs_atendidas"] >= 5

    # heuristica valor extremo (top 1%)
    if not agg["valor_total"].empty:
        cutoff = agg["valor_total"].quantile(0.99)
        agg["flag_valor_extremo"] = agg["valor_total"] >= cutoff
    else:
        agg["flag_valor_extremo"] = False

    agg["suspeito"] = (
        ~agg["cnpj_valido"] | agg["flag_multi_uf"] | agg["flag_valor_extremo"]
    )
    return agg.sort_values("valor_total", ascending=False).reset_index(drop=True)


def enrich_with_cnpj_public_api(cnpjs: list[str]) -> pd.DataFrame:
    """Hook para enriquecer com dados da Receita ou ReceitaWS publico.

    Hoje no-op (placeholder). Implementacao real consideraria:
    - rate limit agressivo (ReceitaWS gratuito tem 3 req/min)
    - cache em disco
    - tratamento de baixa/inexistencia
    """
    return pd.DataFrame(columns=["cnpj_fornecedor", "situacao", "data_situacao"])
