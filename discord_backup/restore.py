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
        raise RestoreError("Restore operation is currently unavailable in this source build.")


__all__ = ["RestoreError", "RestoreService"]
