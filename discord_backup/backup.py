from __future__ import annotations


class BackupError(Exception):
    pass


class BackupService:
    async def run(self, token: str, config: object, console: object) -> object:
        """Run backup; returns result with duration, guilds, group_chats, path."""
        raise BackupError("Backup operation is currently unavailable in this source build.")

    def save(self, result: object, path: str | None = None) -> str:
        """Persist backup bundle to .bkup file. Returns path."""
        raise BackupError("Backup save operation is currently unavailable in this source build.")


__all__ = ["BackupError", "BackupService"]
