# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations


class BackupError(Exception):
    pass


class BackupService:
    async def run(self, token: str, config: object, console: object) -> object:
        """Run backup; returns result with duration, guilds, group_chats, path."""
        raise NotImplementedError("Backup logic reconstructed from bytecode - implement from _dis.txt")

    def save(self, result: object, path: str | None = None) -> str:
        """Persist backup bundle to .bkup file. Returns path."""
        raise NotImplementedError("Backup save logic - implement from backup_dis.txt")


__all__ = ["BackupError", "BackupService"]
