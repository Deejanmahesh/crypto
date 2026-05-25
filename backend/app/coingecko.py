"""Thin async client for the CoinGecko public API.

Only the two endpoints we need are wrapped:
- /coins/markets            -> top assets with current price/volume
- /coins/{id}/market_chart  -> historical price & volume series

The public free tier is aggressively rate-limited (HTTP 429). Requests are
retried with exponential backoff, honouring the ``Retry-After`` header when
present.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CoinGeckoClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        max_retries: int = 4,
    ):
        self.base_url = base_url or settings.coingecko_base_url
        self.api_key = api_key if api_key is not None else settings.coingecko_api_key
        self.max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        # Demo API key header (optional, raises the public rate limit).
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    async def _get(self, url: str, params: dict) -> dict | list:
        """GET with retry/backoff on 429 (and transient 5xx)."""
        delay = 2.0
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(1, self.max_retries + 1):
                resp = await client.get(url, params=params, headers=self._headers())
                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt == self.max_retries:
                        resp.raise_for_status()
                    retry_after = resp.headers.get("retry-after")
                    wait = float(retry_after) if retry_after else delay
                    logger.warning(
                        "CoinGecko %s (attempt %d/%d) -> sleeping %.1fs",
                        resp.status_code,
                        attempt,
                        self.max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    delay *= 2  # exponential backoff
                    continue
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("unreachable")

    async def get_top_markets(self, vs_currency: str = "usd", per_page: int = 10) -> list[dict]:
        """Return the top `per_page` assets ordered by market cap."""
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
        }
        return await self._get(url, params)  # type: ignore[return-value]

    async def get_market_chart(
        self, coin_id: str, vs_currency: str = "usd", days: int = 30
    ) -> dict:
        """Return historical {prices, total_volumes} for a coin.

        Each series is a list of [unix_ms, value] pairs.
        """
        url = f"{self.base_url}/coins/{coin_id}/market_chart"
        params = {"vs_currency": vs_currency, "days": days}
        return await self._get(url, params)  # type: ignore[return-value]
