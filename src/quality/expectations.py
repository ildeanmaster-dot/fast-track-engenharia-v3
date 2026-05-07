"""Expectations declarativas para qualidade de dados (estilo DLT).

Cada Expectation tem:
- nome
- predicado (callable que recebe DataFrame e retorna boolean Series)
- acao em caso de violacao: warn (loga) ou fail (raise)
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


class ExpectationFailed(AssertionError):
    """Levantada quando uma expectativa com acao 'fail' e violada."""


@dataclass
class Expectation:
    name: str
    predicate: Callable[[pd.DataFrame], pd.Series]
    action: str = "warn"  # "warn" ou "fail"


def check(df: pd.DataFrame, expectations: list[Expectation]) -> dict[str, int]:
    """Avalia expectativas. Retorna dict {nome -> qtd_violacoes}."""
    summary: dict[str, int] = {}
    for exp in expectations:
        mask = exp.predicate(df)
        violations = int((~mask).sum())
        summary[exp.name] = violations
        if violations:
            logger.warning(
                "expectativa violada",
                extra={"expectativa": exp.name, "violacoes": violations,
                       "n_total": len(df), "acao": exp.action},
            )
            if exp.action == "fail":
                raise ExpectationFailed(
                    f"expectativa '{exp.name}' falhou em {violations} linhas"
                )
    return summary


# Expectativas comuns prontas para reuso

def not_null(col: str) -> Expectation:
    return Expectation(
        name=f"not_null({col})",
        predicate=lambda df: df[col].notna(),
    )


def positive(col: str) -> Expectation:
    return Expectation(
        name=f"positive({col})",
        predicate=lambda df: df[col] > 0,
    )


def in_set(col: str, values: set) -> Expectation:
    return Expectation(
        name=f"in_set({col}, {sorted(values)})",
        predicate=lambda df: df[col].isin(values),
    )


def unique(cols: list[str]) -> Expectation:
    return Expectation(
        name=f"unique({cols})",
        predicate=lambda df: ~df.duplicated(subset=cols, keep=False),
    )
