"""Cliente HTTP resiliente para a API da Camara dos Deputados.

Caracteristicas:
- Retry exponencial com tenacity para transientes (429/5xx + erros de rede).
- Rate limit cliente-side configuravel (RPM).
- Paginacao via header `Link` rel="next".
- Endpoints fanout (filhos) recebem path_params em vez de pagina/itens.
- Auditoria: cada Page traz source_url, page_number, fetched_at_iso.
"""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.utils.config_loader import APIConfig, EndpointConfig

logger = logging.getLogger(__name__)


class CamaraAPIError(Exception):
    """Erro generico da API."""


class TransientError(CamaraAPIError):
    """Erros que merecem retry (429, 5xx, falha de rede)."""


_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    match = _LINK_NEXT_RE.search(link_header)
    return match.group(1) if match else None


def _extract_page_number(url: str, current: int) -> int:
    qs = parse_qs(urlparse(url).query)
    return int(qs.get("pagina", [str(current + 1)])[0])


@dataclass
class Page:
    """Resultado de uma chamada de pagina."""

    records: list[dict[str, Any]]
    source_url: str
    page_number: int
    fetched_at_iso: str
    extras: dict[str, Any] = field(default_factory=dict)


class _RateLimiter:
    """Rate limiter simples baseado em RPM. Bloqueia se necessario."""

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self.min_interval = 60.0 / max(rpm, 1)
        self._last_call: float = 0.0

    def throttle(self) -> None:
        if self.rpm <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()


class CamaraAPIClient:
    """Cliente HTTP da API com retry, rate limit e paginacao."""

    def __init__(self, config: APIConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": config.user_agent,
        })
        self._rate_limiter = _RateLimiter(config.rate_limit_rpm)

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    def _get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        self._rate_limiter.throttle()
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
        except requests.RequestException as exc:
            raise TransientError(f"erro de rede em {url}: {exc}") from exc

        if response.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"HTTP {response.status_code} em {response.url}")
        if response.status_code >= 400:
            raise CamaraAPIError(
                f"HTTP {response.status_code} em {response.url}: {response.text[:300]}"
            )
        return response

    def iter_pages(
        self,
        endpoint: EndpointConfig,
        path_params: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
        max_pages: int | None = None,
    ) -> Iterator[Page]:
        """Itera sobre as paginas de um endpoint.

        Para endpoints `paginated=False` (fanouts), yielda apenas 1 Page com
        todos os registros e ignora pagina/itens nos params.
        """
        path = endpoint.path.format(**(path_params or {}))
        url = f"{self.config.base_url}{path}"
        base_params: dict[str, Any] = {**endpoint.params, **(extra_params or {})}

        page_num = 1
        while True:
            if max_pages is not None and page_num > max_pages:
                break

            params = dict(base_params)
            if endpoint.paginated:
                params["pagina"] = page_num

            response = self._get(url, params=params)
            body = response.json()
            records = body.get("dados", []) if isinstance(body, dict) else body
            if isinstance(records, dict):
                records = [records]

            yield Page(
                records=records or [],
                source_url=response.url,
                page_number=page_num,
                fetched_at_iso=datetime.now(timezone.utc).isoformat(),
                extras={"links": body.get("links", []) if isinstance(body, dict) else []},
            )

            if not endpoint.paginated:
                break

            next_url = _parse_next_link(response.headers.get("Link"))
            if not next_url:
                break

            new_page = _extract_page_number(next_url, page_num)
            if new_page <= page_num:
                break
            page_num = new_page
