"""Tests dos 6 entregaveis + 2 opcionais com fixtures sinteticas."""
import pandas as pd
import pytest

from src.analytics import (
    atlas_frentes,
    calendario,
    cdc_tramitacao,
    ceap,
    correlacao,
    cpis,
    engajamento,
    streaming_votacoes,
)


@pytest.fixture
def silver():
    return {
        "deputados": pd.DataFrame([
            {"id_deputado": 1, "nome": "A", "sigla_partido": "PT", "sigla_uf": "SP", "id_legislatura": 57},
            {"id_deputado": 2, "nome": "B", "sigla_partido": "PT", "sigla_uf": "SP", "id_legislatura": 57},
            {"id_deputado": 3, "nome": "C", "sigla_partido": "PL", "sigla_uf": "RJ", "id_legislatura": 57},
            {"id_deputado": 4, "nome": "D", "sigla_partido": "NOVO", "sigla_uf": "MG", "id_legislatura": 57},
        ]),
        "partidos": pd.DataFrame([
            {"id_partido": 1, "sigla_partido": "PT", "nome_partido": "PT"},
        ]),
        "frentes": pd.DataFrame([
            {"id_frente": 100, "nome_frente": "F1", "id_legislatura": 57},
            {"id_frente": 200, "nome_frente": "F2", "id_legislatura": 57},
        ]),
        "frente_membros": pd.DataFrame([
            {"id_frente": 100, "id_deputado": 1},
            {"id_frente": 100, "id_deputado": 2},
            {"id_frente": 100, "id_deputado": 3},
            {"id_frente": 200, "id_deputado": 1},
            {"id_frente": 200, "id_deputado": 4},
        ]),
        "orgaos": pd.DataFrame([
            {"id_orgao": 1, "sigla_orgao": "X", "nome_orgao": "Comissao",
             "tipo_orgao": "Permanente", "cod_tipo_orgao": 3,
             "data_inicio": pd.NaT, "data_fim": pd.NaT},
            {"id_orgao": 2, "sigla_orgao": "CPI8J", "nome_orgao": "CPMI 8 Janeiro",
             "tipo_orgao": "CPMI", "cod_tipo_orgao": 5,
             "data_inicio": pd.Timestamp("2023-05-25"), "data_fim": pd.Timestamp("2023-12-22")},
        ]),
        "orgao_membros": pd.DataFrame([
            {"id_orgao": 2, "id_deputado": 1, "sigla_partido": "PT", "sigla_uf": "SP"},
        ]),
        "orgao_eventos": pd.DataFrame(),
        "eventos": pd.DataFrame([
            {"id_evento": 1, "data_hora_inicio": pd.Timestamp("2024-09-15", tz="UTC"),
             "data_hora_fim": pd.Timestamp("2024-09-15 12:00", tz="UTC"),
             "descricao_tipo": "Audiencia", "situacao": "ok",
             "descricao": "tema X"},
            {"id_evento": 2, "data_hora_inicio": pd.Timestamp("2024-11-10", tz="UTC"),
             "data_hora_fim": pd.Timestamp("2024-11-10 14:00", tz="UTC"),
             "descricao_tipo": "Sessao", "situacao": "ok",
             "descricao": "tema Y"},
        ]),
        "evento_deputados": pd.DataFrame([
            {"id_evento": 1, "id_deputado": 1, "sigla_partido": "PT", "sigla_uf": "SP"},
            {"id_evento": 1, "id_deputado": 2, "sigla_partido": "PT", "sigla_uf": "SP"},
            {"id_evento": 2, "id_deputado": 1, "sigla_partido": "PT", "sigla_uf": "SP"},
        ]),
        "votacoes": pd.DataFrame([
            {"id_votacao": 1000, "data_hora_registro": pd.Timestamp("2024-09-20", tz="UTC"),
             "descricao": "Pedido de urgencia para PL"},
            {"id_votacao": 2000, "data_hora_registro": pd.Timestamp("2024-09-21", tz="UTC"),
             "descricao": "Aprovacao de relatorio"},
        ]),
        "votacao_votos": pd.DataFrame([
            {"id_votacao": 1000, "id_deputado": 1, "tipo_voto": "Sim", "sigla_partido": "PT", "data_registro_voto": None},
            {"id_votacao": 1000, "id_deputado": 2, "tipo_voto": "Sim", "sigla_partido": "PT", "data_registro_voto": None},
            {"id_votacao": 1000, "id_deputado": 3, "tipo_voto": "Nao", "sigla_partido": "PL", "data_registro_voto": None},
        ]),
        "deputado_despesas": pd.DataFrame([
            {"id_deputado": 1, "ano": 2024, "mes": 1, "tipo_despesa": "COMB",
             "valor_liquido": 100.0, "nome_fornecedor": "F1", "cnpj_fornecedor": "00000000000191",
             "data_documento": None, "cod_documento": "D1"},
            {"id_deputado": 2, "ano": 2024, "mes": 1, "tipo_despesa": "COMB",
             "valor_liquido": 110.0, "nome_fornecedor": "F1", "cnpj_fornecedor": "00000000000191",
             "data_documento": None, "cod_documento": "D2"},
            {"id_deputado": 3, "ano": 2024, "mes": 1, "tipo_despesa": "COMB",
             "valor_liquido": 5000.0, "nome_fornecedor": "F2", "cnpj_fornecedor": "11111111111111",
             "data_documento": None, "cod_documento": "D3"},
        ]),
        "deputado_discursos": pd.DataFrame([
            {"id_deputado": 1, "data_hora_inicio": pd.Timestamp("2024-05-01", tz="UTC")},
            {"id_deputado": 2, "data_hora_inicio": pd.Timestamp("2024-05-02", tz="UTC")},
        ]),
        "proposicoes": pd.DataFrame([
            {"id_proposicao": 1, "sigla_tipo": "PL",
             "ementa": "Cria CPI8J de investigacao", "data_apresentacao": pd.Timestamp("2024-03-01")},
        ]),
        "proposicao_tramitacoes": pd.DataFrame([
            {"id_proposicao": 1, "sequencia": 1,
             "data_hora": pd.Timestamp("2024-03-02", tz="UTC"),
             "sigla_orgao": "MESA", "descricao_situacao": "Aguardando Parecer",
             "descricao_tramitacao": "x"},
            {"id_proposicao": 1, "sequencia": 2,
             "data_hora": pd.Timestamp("2024-04-01", tz="UTC"),
             "sigla_orgao": "PLEN", "descricao_situacao": "Pronta para Pauta no Plenario",
             "descricao_tramitacao": "y"},
        ]),
    }


@pytest.fixture
def ideologia():
    return {
        "partidos": {"PT": 1, "PL": 5, "NOVO": 5},
        "distancia_minima_oposicao": 3,
    }


# ===== Atlas =====

def test_hhi_calculo(silver):
    atlas = atlas_frentes.atlas_frentes(silver)
    hhi = atlas_frentes.hhi_por_frente(atlas)
    f1 = hhi[hhi["id_frente"] == 100].iloc[0]
    # F1 tem 2 PT + 1 PL = (2/3)^2 + (1/3)^2 = 5/9
    assert abs(f1["hhi"] - 5/9) < 1e-6


def test_frentes_opostas_pipeline_executa(silver, ideologia):
    """Garante que o pipeline executa sem erro mesmo se nenhum par for oposto."""
    atlas = atlas_frentes.atlas_frentes(silver)
    sobreposicao = atlas_frentes.sobreposicao_frentes(atlas, min_overlap=1)
    out = atlas_frentes.frentes_ideologicamente_opostas(sobreposicao, atlas, ideologia)
    # pode estar vazio se todos os pares ficam abaixo da distancia minima
    assert isinstance(out, pd.DataFrame)
    if not out.empty:
        assert "distancia_ideologica" in out.columns


# ===== Calendario =====

def test_taxa_presenca(silver):
    out = calendario.taxa_presenca_deputado(silver)
    d1 = out[out["id_deputado"] == 1].iloc[0]
    assert d1["n_presencas"] == 2
    assert d1["taxa_presenca"] == 1.0


def test_pre_pos_eleitoral(silver):
    out = calendario.pre_pos_eleitoral(silver)
    assert set(out["periodo"]) == {"pre_eleicao", "pos_eleicao"}


# ===== Correlacao =====

def test_alinhamento_partido_unanime(silver):
    out = correlacao.alinhamento_partido_por_votacao(silver)
    pt = out[out["sigla_partido"] == "PT"]
    assert (pt["alinhamento"] == 1.0).all()


# ===== CEAP =====

def test_ceap_z_score_calculado(silver):
    out = ceap.ceap_anomalias(silver)
    assert "z_score" in out.columns
    assert "outlier" in out.columns


def test_ceap_top10(silver):
    out = ceap.ceap_top10_partido_mes(silver)
    assert not out.empty


# ===== CPIs =====

def test_identifica_cpmi(silver):
    out = cpis.identificar_cpis(silver)
    assert len(out) == 1
    assert out.iloc[0]["sigla_orgao"] == "CPI8J"


def test_cpi_membros(silver):
    out = cpis.cpi_membros(silver)
    assert len(out) == 1


def test_cpi_legislacao_via_ementa(silver):
    out = cpis.cpi_legislacao(silver)
    assert len(out) == 1
    assert out.iloc[0]["sigla_cpi"] == "CPI8J"


def test_cpi_produtividade(silver):
    out = cpis.cpi_produtividade(silver)
    assert "produtiva" in out.columns


# ===== Engajamento =====

def test_engajamento_normalizado(silver):
    out = engajamento.score_engajamento(silver)
    assert out["engajamento"].between(0, 1).all()
    assert out["percentil_nacional"].between(0, 1).all()


def test_relatorio_mensal(silver):
    out = engajamento.relatorio_mensal_deputado(silver)
    assert "engajamento" in out.columns
    assert "percentil_nacional" in out.columns


# ===== Opcional 1: CDC =====

def test_cdc_marca_is_current(silver):
    out = cdc_tramitacao.build_scd2(silver)
    assert out[out["is_current"]].iloc[0]["sequencia"] == 2


def test_cdc_alertas_plenario(silver):
    scd2 = cdc_tramitacao.build_scd2(silver)
    alertas = cdc_tramitacao.alertas_transicao(scd2)
    assert "avanco_plenario" in alertas["tipo_alerta"].values


def test_cdc_tempo_medio(silver):
    scd2 = cdc_tramitacao.build_scd2(silver)
    out = cdc_tramitacao.tempo_medio_tramitacao(scd2, silver)
    assert "media_dias" in out.columns


# ===== Opcional 2: Streaming =====

def test_streaming_classifica_urgencia():
    assert streaming_votacoes.classifica_urgencia("Pedido de urgencia") == "urgente"
    assert streaming_votacoes.classifica_urgencia("Sessao normal") == "normal"
    assert streaming_votacoes.classifica_urgencia(None) == "normal"
    assert streaming_votacoes.classifica_urgencia("Acordo de Lideres") == "urgente"


def test_streaming_alertas(silver):
    out = streaming_votacoes.alertas_votacao(silver)
    assert "urgencia" in out.columns
    # primeira votacao tem "urgencia" no texto
    urgentes = out[out["urgencia"] == "urgente"]
    assert len(urgentes) >= 1
