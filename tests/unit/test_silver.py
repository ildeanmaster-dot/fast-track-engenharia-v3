"""Tests da camada Silver."""
import json

import pytest

from src.transforms import silver as silver_mod


@pytest.fixture
def fake_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(silver_mod, "SAMPLES_DIR", tmp_path)
    return tmp_path


def _w(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_silver_deputados_rename_e_audit(fake_samples):
    _w(fake_samples / "deputados.jsonl", [
        {"id": 1, "nome": "X", "siglaPartido": "PT", "siglaUf": "SP",
         "idLegislatura": 57, "_payload_hash": "abc"},
    ])
    df = silver_mod.to_silver("deputados", run_id="test-run")
    assert "id_deputado" in df.columns
    assert "sigla_partido" in df.columns
    assert "silver_ingest_ts" in df.columns
    assert df["run_id"].iloc[0] == "test-run"


def test_dedup_remove_duplicatas(fake_samples):
    _w(fake_samples / "deputados.jsonl", [
        {"id": 1, "nome": "X", "siglaPartido": "PT", "siglaUf": "SP", "idLegislatura": 57},
        {"id": 1, "nome": "X", "siglaPartido": "PT", "siglaUf": "SP", "idLegislatura": 57},
        {"id": 2, "nome": "Y", "siglaPartido": "PL", "siglaUf": "RJ", "idLegislatura": 57},
    ])
    df = silver_mod.to_silver("deputados")
    assert len(df) == 2


def test_eventos_parse_timestamp_utc(fake_samples):
    _w(fake_samples / "eventos.jsonl", [
        {"id": 1, "dataHoraInicio": "2025-03-15T10:00",
         "dataHoraFim": "2025-03-15T12:00",
         "descricaoTipo": "Sessao", "situacao": "ok"},
    ])
    df = silver_mod.to_silver("eventos")
    assert "datetime" in df["data_hora_inicio"].dtype.name


def test_voto_aplaina_deputado_aninhado(fake_samples):
    _w(fake_samples / "votacao_votos.jsonl", [
        {"_parent_id": 100,
         "deputado_": {"id": 1, "nome": "X", "siglaPartido": "PT", "siglaUf": "SP"},
         "tipoVoto": "Sim", "dataRegistroVoto": "2025-01-01T10:00"},
    ])
    df = silver_mod.to_silver("votacao_votos")
    assert df.iloc[0]["id_deputado"] == 1
    assert df.iloc[0]["sigla_partido"] == "PT"
    assert df.iloc[0]["nome_deputado"] == "X"


def test_arquivo_inexistente_levanta(fake_samples):
    with pytest.raises(FileNotFoundError):
        silver_mod.to_silver("naoexiste")
