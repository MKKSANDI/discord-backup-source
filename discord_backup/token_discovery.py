# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DiscoveredToken:
    token: str
    user_tag: str
    user_id: str
    source: str


async def discover_tokens() -> List[DiscoveredToken]:
    """Scan local storage for Discord tokens. Returns list of DiscoveredToken."""
    # Implement by scanning browser/roaming storage (see token_discovery_dis.txt).
    return []


__all__ = ["DiscoveredToken", "discover_tokens"]
