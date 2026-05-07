"""Tests do modulo quality (CNPJ + expectations)."""
import pandas as pd
import pytest

from src.quality import expectations as exp_mod
from src.quality.cnpj import flag_suspeitos, limpa_cnpj, valida_cnpj


# ---- CNPJ ----

def test_limpa_cnpj():
    assert limpa_cnpj("00.000.000/0001-91") == "00000000000191"
    assert limpa_cnpj(None) is None
    assert limpa_cnpj("") is None
    assert limpa_cnpj("abc") is None


def test_valida_cnpj_real():
    # CNPJ valido conhecido (Banco Central)
    assert valida_cnpj("00.038.166/0001-05") is True


def test_valida_cnpj_invalido():
    assert valida_cnpj(None) is False
    assert valida_cnpj("123") is False
    assert valida_cnpj("11111111111111") is False  # sequencia
    assert valida_cnpj("00000000000000") is False  # zeros
    assert valida_cnpj("12345678000199") is False  # DV errado


def test_flag_suspeitos_marca_multi_uf():
    despesas = pd.DataFrame([
        {"id_deputado": 1, "cnpj_fornecedor": "X", "nome_fornecedor": "F",
         "valor_liquido": 100, "cod_documento": "D1"},
        {"id_deputado": 2, "cnpj_fornecedor": "X", "nome_fornecedor": "F",
         "valor_liquido": 200, "cod_documento": "D2"},
        {"id_deputado": 3, "cnpj_fornecedor": "X", "nome_fornecedor": "F",
         "valor_liquido": 100, "cod_documento": "D3"},
        {"id_deputado": 4, "cnpj_fornecedor": "X", "nome_fornecedor": "F",
         "valor_liquido": 100, "cod_documento": "D4"},
        {"id_deputado": 5, "cnpj_fornecedor": "X", "nome_fornecedor": "F",
         "valor_liquido": 100, "cod_documento": "D5"},
    ])
    deps = pd.DataFrame([
        {"id_deputado": i, "sigla_uf": uf}
        for i, uf in enumerate(["SP", "RJ", "MG", "BA", "RS"], start=1)
    ])
    out = flag_suspeitos(despesas, deps)
    assert out.iloc[0]["flag_multi_uf"] is True or out.iloc[0]["flag_multi_uf"] == True  # noqa: E712


# ---- Expectations ----

def test_not_null_predicate():
    df = pd.DataFrame({"x": [1, None, 3]})
    summary = exp_mod.check(df, [exp_mod.not_null("x")])
    assert summary["not_null(x)"] == 1


def test_unique_predicate():
    df = pd.DataFrame({"k": [1, 1, 2, 3]})
    summary = exp_mod.check(df, [exp_mod.unique(["k"])])
    assert summary["unique(['k'])"] == 2  # 2 linhas duplicadas


def test_in_set_predicate():
    df = pd.DataFrame({"v": ["A", "B", "C", "D"]})
    summary = exp_mod.check(df, [exp_mod.in_set("v", {"A", "B"})])
    assert summary["in_set(v, ['A', 'B'])"] == 2


def test_action_fail_levanta():
    df = pd.DataFrame({"x": [1, None]})
    e = exp_mod.Expectation(name="x_nn", predicate=lambda d: d["x"].notna(), action="fail")
    with pytest.raises(exp_mod.ExpectationFailed):
        exp_mod.check(df, [e])
