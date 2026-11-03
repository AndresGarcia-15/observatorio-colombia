"""Cliente HTTP con reintentos y un User-Agent que identifica al proyecto."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .config import USER_AGENT

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


class HttpClient:
    def __init__(self, timeout: float = 120.0, retries: int = 3, backoff: float = 3.0) -> None:
        self.retries = retries
        self.backoff = backoff
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=15.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            # Solo IPv4: los runners de GitHub Actions no tienen salida por IPv6 y algunos
            # servidores (NASA FIRMS) anuncian direcciones IPv6 que nunca responden.
            transport=httpx.HTTPTransport(retries=1, local_address="0.0.0.0"),
        )

    def get(self, url: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                resp = self._client.get(url, params=params, timeout=timeout or self._client.timeout)
                if resp.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code in RETRY_STATUS
                last = exc
                if not retryable or attempt == self.retries:
                    break
                wait = self.backoff * 2 ** (attempt - 1)
                log.warning("Fallo %s (%s). Reintento %d en %.0f s", url, exc, attempt, wait)
                time.sleep(wait)
        assert last is not None
        raise last

    def get_json(self, url: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        return self.get(url, params, timeout).json()

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        return self.get(url, params).text

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
