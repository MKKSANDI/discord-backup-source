from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

_LOGIN_BUILD_RE = re.compile(r"assets/(?:[\w-]+)\.(?P<hash>[\w]+)\.js")
_BUILD_NUMBER_RE = re.compile(r"buildNumber\D+(\d+)")
_DEFAULT_BUILD = 452533


@dataclass(slots=True)
class DiscordBrowserIdentity:
    """Represents a browser fingerprint Discord expects."""

    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
    browser_version: str = "123.0.0.0"
    locale: str = "en-US"
    os_version: str = "10"
    build_number: int | None = None
    _super_properties: str | None = field(default=None, init=False, repr=False)

    async def ensure_build_number(self, client: httpx.AsyncClient) -> int:
        if self.build_number is not None:
            return self.build_number

        try:
            login_page = await client.get(
                "https://discord.com/login",
                headers={"Accept-Encoding": "identity"},
            )
            login_page.raise_for_status()
        except httpx.HTTPError:
            self.build_number = _DEFAULT_BUILD
            return self.build_number

        hashes = _LOGIN_BUILD_RE.findall(login_page.text)
        for asset_hash in hashes:
            asset_url = f"https://discord.com/assets/{asset_hash}.js"
            try:
                asset = await client.get(asset_url, headers={"Accept-Encoding": "identity"})
                asset.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {403, 404}:
                    continue
                raise
            except httpx.HTTPError:
                continue

            match = _BUILD_NUMBER_RE.search(asset.text)
            if match:
                self.build_number = int(match.group(1))
                break

        if self.build_number is None:
            self.build_number = _DEFAULT_BUILD

        return self.build_number

    async def super_properties(self, client: httpx.AsyncClient) -> str:
        if self._super_properties is None:
            build_number = await self.ensure_build_number(client)
            payload: dict[str, Any] = {
                "os": "Windows",
                "browser": "Chrome",
                "device": "",
                "system_locale": self.locale,
                "browser_user_agent": self.user_agent,
                "browser_version": self.browser_version,
                "os_version": self.os_version,
                "referrer": "",
                "referring_domain": "",
                "referrer_current": "",
                "referring_domain_current": "",
                "release_channel": "stable",
                "client_build_number": build_number,
                "client_event_source": None,
            }
            self._super_properties = base64.b64encode(
                json.dumps(payload, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
        return self._super_properties

    async def build_headers(
        self,
        client: httpx.AsyncClient,
        *,
        method: str,
        authorization: str | None = None,
        referer: str | None = "https://discord.com/channels/@me",
        origin: str | None = "https://discord.com",
        super_properties: bool = True,
        include_locale: bool = True,
        include_debug: bool = False,
        timezone: str | None = "Europe/London",
        context: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "locale=en-GB",
            "Referer": referer or "https://discord.com",
            "Sec-Ch-Ua": '\"Google Chrome\";v="123", "Chromium";v="123", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '\"Windows\"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": self.user_agent,
        }

        if method.lower() != "get" and origin:
            headers["Content-Type"] = "application/json"
            headers["Origin"] = origin

        if authorization:
            headers["Authorization"] = authorization

        if super_properties:
            headers["X-Super-Properties"] = await self.super_properties(client)
        if include_locale:
            headers["X-Discord-Locale"] = self.locale
        if include_debug:
            headers["X-Debug-Options"] = "bugReporterEnabled"
        if timezone:
            headers["X-Discord-Timezone"] = timezone
        if context:
            headers["X-Context-Properties"] = context
        if extra:
            headers.update(extra)

        return headers


__all__ = ["DiscordBrowserIdentity"]
