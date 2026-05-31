# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from typing import Any

import httpx

from discord_backup.identity import DiscordBrowserIdentity, build_headers, ensure_build_number

API_BASE = "https://discord.com/api/v9"


class DiscordHTTPClient:
    """Async HTTP helper with Discord flavoured defaults and rate-limit handling."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        identity: DiscordBrowserIdentity,
        concurrency: int = 6,
        max_retries: int = 4,
    ) -> None:
        self._client = client
        self.identity = identity
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._max_retries = max_retries

    @classmethod
    async def create(
        cls,
        identity: DiscordBrowserIdentity | None = None,
        timeout: float = 30.0,
        concurrency: int = 6,
        max_retries: int = 4,
    ) -> "DiscordHTTPClient":
        ensure_build_number()
        identity = identity or DiscordBrowserIdentity()
        client = httpx.AsyncClient(
            timeout=timeout,
            headers=identity.build_headers("get", superprop=True),
        )
        return cls(client, identity, concurrency, max_retries)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        token: str | None = None,
        json_payload: dict | None = None,
        params: dict | None = None,
        super_properties: bool = True,
        include_locale: bool = True,
        include_debug: bool = False,
        expected_status: int | None = 200,
    ) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{API_BASE.rstrip('/')}/{url.lstrip('/')}"
        referer = "https://discord.com/channels/@me"
        origin = "https://discord.com"
        headers = self.identity.build_headers(
            method,
            token=token,
            debugoptions=include_debug,
            discordlocale=include_locale,
            superprop=super_properties,
        )
        for attempt in range(self._max_retries):
            async with self._semaphore:
                try:
                    response = await self._client.request(
                        method,
                        url,
                        json=json_payload,
                        params=params,
                        headers=headers,
                    )
                except httpx.HTTPError as exc:
                    if attempt == self._max_retries - 1:
                        raise RuntimeError(
                            f"Failed to complete {method} {url} after {self._max_retries} attempts"
                        ) from exc
                    await asyncio.sleep(1.5)
                    continue
            if response.status_code == 429:
                data = response.json() if response.content else {}
                delay = float(data.get("retry_after", 0.25))
                await asyncio.sleep(delay)
                continue
            if expected_status and response.status_code != expected_status and response.status_code >= 500:
                await asyncio.sleep(0.25)
                continue
            return response
        return response  # type: ignore

    async def json(
        self,
        method: str,
        url: str,
        token: str | None = None,
        expected_status: int | None = 200,
        **kwargs: Any,
    ) -> Any:
        response = await self.request(method, url, token=token, expected_status=expected_status, **kwargs)
        response.raise_for_status()
        return response.json()


__all__ = ["API_BASE", "DiscordHTTPClient"]
