"""Tests do cliente HTTP."""
import pytest
import responses

from src.ingestion.api_client import (
    CamaraAPIClient,
    CamaraAPIError,
    _extract_page_number,
    _parse_next_link,
)
from src.utils.config_loader import APIConfig, EndpointConfig


@pytest.fixture
def cfg():
    eps = {
        "test": EndpointConfig(name="test", path="/test", params={"itens": 10},
                               paginated=True, pk=["id"], incremental="snapshot"),
        "child": EndpointConfig(name="child", path="/parents/{id}/children",
                                paginated=False, pk=["id"], incremental="snapshot",
                                fanout_from="test"),
    }
    return APIConfig(
        base_url="https://api.exemplo.com",
        user_agent="ut/0.1", timeout=10, max_retries=3, rate_limit_rpm=600,
        endpoints=eps, fanout_limits={},
    )


def test_parse_next_link_header():
    h = '<https://api/?pagina=1>; rel="self", <https://api/?pagina=2>; rel="next"'
    assert _parse_next_link(h) == "https://api/?pagina=2"
    assert _parse_next_link(None) is None
    assert _parse_next_link('<https://api/>; rel="last"') is None


def test_extract_page_number():
    assert _extract_page_number("https://api/?pagina=5", current=4) == 5
    assert _extract_page_number("https://api/?other=1", current=4) == 5  # fallback


@responses.activate
def test_iter_pages_segue_next_link(cfg):
    # primeira pagina com header next
    responses.add(
        responses.GET, "https://api.exemplo.com/test",
        json={"dados": [{"id": 1}]},
        status=200,
        headers={"Link": '<https://api.exemplo.com/test?pagina=2>; rel="next"'},
    )
    # segunda pagina sem next
    responses.add(
        responses.GET, "https://api.exemplo.com/test",
        json={"dados": [{"id": 2}]},
        status=200,
    )
    client = CamaraAPIClient(cfg)
    pages = list(client.iter_pages(cfg.endpoints["test"], max_pages=5))
    assert len(pages) == 2
    assert pages[0].records[0]["id"] == 1
    assert pages[1].records[0]["id"] == 2


@responses.activate
def test_endpoint_nao_paginado_nao_injeta_pagina(cfg):
    """Fanouts nao devem ter parametro `pagina` na request."""
    responses.add(
        responses.GET, "https://api.exemplo.com/parents/42/children",
        json={"dados": [{"id": 100}, {"id": 101}]},
        status=200,
    )
    client = CamaraAPIClient(cfg)
    pages = list(client.iter_pages(cfg.endpoints["child"], path_params={"id": 42}))
    assert len(pages) == 1  # so 1 chamada, nao paginou
    # confirma que nao tem `pagina` na URL
    assert "pagina" not in responses.calls[0].request.url


@responses.activate
def test_erro_4xx_levanta_imediatamente(cfg):
    responses.add(
        responses.GET, "https://api.exemplo.com/test",
        json={"erro": "Bad Request"},
        status=400,
    )
    client = CamaraAPIClient(cfg)
    with pytest.raises(CamaraAPIError):
        list(client.iter_pages(cfg.endpoints["test"]))


@responses.activate
def test_503_dispara_retry_e_eventualmente_funciona(cfg):
    """Tenacity deve fazer retry em 5xx."""
    for _ in range(2):
        responses.add(responses.GET, "https://api.exemplo.com/test", status=503)
    responses.add(
        responses.GET, "https://api.exemplo.com/test",
        json={"dados": [{"id": 1}]}, status=200,
    )
    client = CamaraAPIClient(cfg)
    pages = list(client.iter_pages(cfg.endpoints["test"]))
    assert len(pages) == 1
    # 3 tentativas registradas
    assert len(responses.calls) >= 3
