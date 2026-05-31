# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackupResult:
    duration: float
    guilds: tuple[int, int]  # success, total
    group_chats: tuple[int, int]
    path: str | None = None
    summary: dict | None = None


__all__ = ["BackupResult"]
