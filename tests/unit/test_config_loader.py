"""Tests do carregamento e validacao do catalogo."""
import pytest

from src.utils.config_loader import EndpointConfig, VALID_INCREMENTALS, load


def test_load_basico():
    cfg = load("conf/endpoints.yaml")
    assert cfg.base_url.startswith("https://")
    assert len(cfg.endpoints) == 17


def test_endpoints_simples_e_fanouts():
    cfg = load("conf/endpoints.yaml")
    simples = [n for n, ep in cfg.endpoints.items() if ep.fanout_from is None]
    fanouts = [n for n, ep in cfg.endpoints.items() if ep.fanout_from]
    assert len(simples) == 8
    assert len(fanouts) == 9


def test_estrategias_validas():
    cfg = load("conf/endpoints.yaml")
    for name, ep in cfg.endpoints.items():
        assert ep.incremental in VALID_INCREMENTALS, f"{name}: {ep.incremental}"


def test_pks_definidas():
    cfg = load("conf/endpoints.yaml")
    for name, ep in cfg.endpoints.items():
        assert ep.pk, f"endpoint {name} sem PK"


def test_fanouts_apontam_para_pais_existentes():
    cfg = load("conf/endpoints.yaml")
    for name, ep in cfg.endpoints.items():
        if ep.fanout_from:
            assert ep.fanout_from in cfg.endpoints


def test_incremental_invalida_levanta_erro():
    with pytest.raises(ValueError, match="incremental invalido"):
        EndpointConfig(name="x", path="/x", incremental="zzz")


def test_watermark_obrigatorio_em_append_watermark():
    with pytest.raises(ValueError, match="append_watermark requer"):
        EndpointConfig(name="x", path="/x", incremental="append_watermark")
