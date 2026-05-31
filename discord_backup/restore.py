# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations


class RestoreError(Exception):
    pass


class RestoreService:
    async def run(
        self,
        backup_data: dict,
        token: str,
        bot_token: str | None = None,
        restore_folders: bool = False,
        allow_version_mismatch: bool = False,
        console: object | None = None,
    ) -> dict:
        """Run restore. Returns summary with guild_id, favourite_gifs_status, folder_restore_attempted, duration."""
        raise NotImplementedError("Restore logic - implement from restore_dis.txt")


__all__ = ["RestoreError", "RestoreService"]
