# Modern Discord backup & restore toolkit.

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from colorama import init as colorama_init

from discord_backup.backup import BackupError, BackupService
from discord_backup.config import AppConfig
from discord_backup.console import Console
from discord_backup.http_client import DiscordHTTPClient
from discord_backup.restore import RestoreError, RestoreService
from discord_backup.results import BackupResult
from discord_backup.startup import remove_startup_script, write_startup_script
from discord_backup.token_discovery import DiscoveredToken, discover_tokens

colorama_init()

app = typer.Typer(help="DiscordAccountBackup CLI/TUI toolkit.")


def _load_config_and_console() -> tuple[AppConfig, Console]:
    config = AppConfig.load()
    console = Console(accent=config.colour)
    return config, console


async def _select_token(console: Console, scan: bool) -> tuple[str, DiscoveredToken] | None:
    http = await DiscordHTTPClient.create()
    try:
        tokens = await discover_tokens()
        if not tokens:
            console.warn("No tokens discovered on this system.")
            return None
        console.info("Discovered tokens:")
        for idx, t in enumerate(tokens):
            console.info(f"  {idx}: {t.user_tag} from {t.source}")
        try:
            choice = typer.prompt("Select token index", type=int)
            selected = tokens[choice]
            console.success(f"Selected {selected.user_tag}")
            return selected.token, selected
        except (ValueError, IndexError):
            console.error("Invalid selection")
            return None
    finally:
        await http.aclose()


@app.command()
def backup(
    token: Optional[str] = typer.Argument(None, help="Discord user token"),
    scan: bool = typer.Option(False, "--scan", help="Auto-discover tokens on this machine"),
) -> None:
    """Create a new backup interactively."""
    config, console = _load_config_and_console()
    try:
        asyncio.run(_run_backup(token, config, console, scan))
    except BackupError as exc:
        console.error(str(exc))
        raise typer.Exit(1)


async def _run_backup(
    token: Optional[str],
    config: AppConfig,
    console: Console,
    scan: bool,
) -> None:
    if not token and not scan:
        console.error("Token is required to run a backup.")
        return
    token_value = token
    if scan or not token_value:
        selection = await _select_token(console, scan)
        if not selection:
            return
        token_value = selection[0]
    http = await DiscordHTTPClient.create()
    try:
        service = BackupService()
        result = await service.run(token_value, config, console)
        path = service.save(result)
        console.success(f"Backup stored at {path}")
        if hasattr(result, "summary") and result.summary:
            summary = result.summary
            console.info(
                f"Guilds: {summary.get('guilds', (0, 0))[0]}/{summary.get('guilds', (0, 0))[1]}"
            )
            console.info(
                f"Group chats: {summary.get('group_chats', (0, 0))[0]}/{summary.get('group_chats', (0, 0))[1]}"
            )
        if hasattr(result, "duration"):
            console.info(f"Duration: {result.duration:.1f}s")
    finally:
        await http.aclose()


@app.command()
def restore(
    backup_file: Path = typer.Argument(..., help="Path to .bkup file"),
    token: Optional[str] = typer.Argument(None, help="Discord user token"),
    bot_token: Optional[str] = typer.Option(None, help="Bot token for user lookups"),
    restore_folders: bool = typer.Option(False, help="Restore guild folders"),
    allow_version_mismatch: bool = typer.Option(False, help="Ignore backup version mismatches"),
) -> None:
    """Restore from a backup file."""
    config, console = _load_config_and_console()
    try:
        asyncio.run(_run_restore(backup_file, token, bot_token, restore_folders, allow_version_mismatch, console))
    except RestoreError as exc:
        console.error(str(exc))
        raise typer.Exit(1)


async def _run_restore(
    backup_path: Path,
    token: Optional[str],
    bot_token: Optional[str],
    restore_folders: bool,
    allow_version_mismatch: bool,
    console: Console,
) -> None:
    if not backup_path.exists():
        console.error(f"Backup file not found: {backup_path}")
        return
    data = json.loads(backup_path.read_text(encoding="utf-8"))
    http = await DiscordHTTPClient.create()
    try:
        service = RestoreService()
        summary = await service.run(
            data, token or "", bot_token, restore_folders, allow_version_mismatch, console
        )
        console.success("Restore complete")
        if summary:
            console.info(f"Backup guild id: {summary.get('guild_id')}")
            console.info(f"Favourite GIFs: {summary.get('favourite_gifs_status')}")
            console.info(f"Folders restored: {summary.get('folder_restore_attempted')}")
            console.info(f"Duration: {summary.get('duration', 0):.1f}s")
    finally:
        await http.aclose()


@app.command()
def auto_backup(
    account_id: str = typer.Argument(..., help="Discord account ID to auto-backup"),
    working_dir: Optional[Path] = typer.Argument(None, help="Working directory containing config.yml"),
) -> None:
    """Internal helper used by the startup script."""
    config, console = _load_config_and_console()
    if working_dir and not working_dir.exists():
        console.warn(f"Working directory not found: {working_dir}")
        return

    async def runner() -> None:
        http = await DiscordHTTPClient.create()
        tokens = await discover_tokens()
        token_value = None
        for item in tokens:
            if item.user_id == account_id:
                token_value = item.token
                console.success(f"Found token for {item.user_tag}")
                break
        if not token_value:
            console.error("No matching token found for auto-backup")
            return
        await http.aclose()
        service = BackupService()
        result = await service.run(token_value, config, console)
        service.save(result)
        console.success("Auto-backup finished")

    asyncio.run(runner())


@app.command()
def startup_add(
    scan: bool = typer.Option(False, help="Scan for tokens to choose from"),
) -> None:
    """Add the current executable/script to Windows startup for auto-backup."""
    config, _ = _load_config_and_console()

    _console = Console(accent=config.colour)

    async def runner() -> None:
        http = await DiscordHTTPClient.create()
        selection = await _select_token(_console, scan) if scan else None
        if not selection:
            token_input = typer.prompt("Enter user token for auto-backup", default="")
            if not token_input:
                _console.error("Token required for auto-backup")
                return
            user_id = "manual"
        else:
            user_id = selection[1].user_id
        await http.aclose()
        executable = getattr(sys, "executable", None)
        if getattr(sys, "frozen", False):
            command = f'"{executable}"'
        else:
            from pathlib import Path as P
            _root = P(__file__).resolve().parent.parent
            command = f'cmd.exe /C python "{_root / "main.py"}"'
        command += f' auto-backup --account-id {user_id}'
        script_path = write_startup_script(command, ".")
        _console.success(f"Startup script written to {script_path}")

    asyncio.run(runner())


@app.command()
def startup_remove() -> None:
    """Remove the auto-backup startup script if present."""
    if remove_startup_script():
        typer.echo("Startup script removed")
    else:
        typer.echo("No startup script found")


@app.command()
def tokens() -> None:
    """List tokens discovered on this machine."""
    config, console = _load_config_and_console()

    async def runner() -> None:
        http = await DiscordHTTPClient.create()
        tokens = await discover_tokens()
        await http.aclose()
        if not tokens:
            console.warn("No tokens discovered")
            return
        for item in tokens:
            console.info(f"{item.user_tag} ({item.user_id}) - {item.source}")

    asyncio.run(runner())


def run() -> None:
    app()


__all__ = ["app", "run"]
