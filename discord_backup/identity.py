# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)
"""Discord browser-like identity / headers for API requests."""

from __future__ import annotations

import json
import platform
import sys
from typing import Any

# Build number / client version - from bytecode
DISCORD_BUILD = "123456"


def ensure_build_number() -> str:
    return DISCORD_BUILD


def build_headers(
    method: str,
    *,
    authorization: str | None = None,
    debugoptions: bool = False,
    discordlocale: bool = False,
    superprop: bool = False,
    timezone: bool = False,
    **kwargs: Any,
) -> dict[str, str]:
    """Build request headers that look like Discord client."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    if authorization:
        headers["Authorization"] = authorization
    if superprop:
        headers["X-Super-Properties"] = json.dumps(
            {
                "os": platform.system(),
                "browser": "Chrome",
                "device": "",
                "system_locale": "en-GB",
                "browser_user_agent": headers["User-Agent"],
                "browser_version": "120.0",
                "os_version": platform.release(),
                "referrer": "",
                "referring_domain": "",
                "referrer_current": "",
                "referring_domain_current": "",
                "release_channel": "stable",
                "client_build_number": ensure_build_number(),
                "client_event_source": None,
            }
        )
    return headers


class DiscordBrowserIdentity:
    """Identity provider for Discord API (browser-like)."""

    def build_headers(
        self,
        method: str,
        token: str | None = None,
        **kwargs: Any,
    ) -> dict[str, str]:
        return build_headers(method, authorization=token, **kwargs)


__all__ = ["DiscordBrowserIdentity", "build_headers", "ensure_build_number"]
