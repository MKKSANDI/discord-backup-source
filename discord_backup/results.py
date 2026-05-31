from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import BackupBundle


@dataclass(slots=True)
class BackupResult:
    bundle: BackupBundle
    duration: float
    guild_success: int
    guild_total: int
    group_chat_success: int
    group_chat_total: int

    def summary(self) -> dict[str, Any]:
        return {
            "duration": self.duration,
            "guilds": {
                "success": self.guild_success,
                "total": self.guild_total,
            },
            "group_chats": {
                "success": self.group_chat_success,
                "total": self.group_chat_total,
            },
        }


__all__ = ["BackupResult"]
