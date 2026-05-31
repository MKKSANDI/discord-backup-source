from __future__ import annotations

import asyncio
import io
import json
import re
import sys
from pathlib import Path
from typing import Sequence

path_dialog = None

try:
    from prompt_toolkit.shortcuts import (
        input_dialog,
        message_dialog,
        radiolist_dialog,
    )
    try:
        from prompt_toolkit.shortcuts import path_dialog
    except ImportError:
        path_dialog = None
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False

from discord_backup.backup import BackupError, BackupService
from discord_backup.config import AppConfig
from discord_backup.console import Console
from discord_backup.http_client import DiscordHTTPClient
from discord_backup.loading import run_with_loading
from discord_backup.restore import RestoreError, RestoreService
from discord_backup.results import BackupResult
from discord_backup.startup import remove_startup_script, write_startup_script
from discord_backup.token_discovery import DiscoveredToken, discover_tokens

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


async def _async_discover_tokens() -> list[DiscoveredToken]:
    http = await DiscordHTTPClient.create()
    try:
        return await discover_tokens()
    finally:
        await http.aclose()


def run_tui() -> None:
    """Run the interactive TUI (no CLI args)."""
    if not _HAS_PROMPT_TOOLKIT:
        raise RuntimeError(
            "prompt_toolkit is required for TUI mode. "
            "Run `python -m pip install -r requirements.txt` and retry."
        )
    config = AppConfig.load()
    console = Console(accent=config.colour)
    while True:
        action = radiolist_dialog(
            title="DiscordAccountBackup",
            text="Select an action (use arrow keys, Enter to confirm)",
            values=[
                ("backup_scan", "Select token for backup"),
                ("backup_manual", "Manual Backup"),
                ("restore", "Restore from backup"),
                ("tokens", "View discovered tokens"),
                ("startup_add", "Add to Windows startup"),
                ("startup_remove", "Remove from startup"),
                ("quit", "Quit"),
            ],
            ok_text="Select",
            cancel_text="Quit",
        ).run()
        if action is None or action == "quit":
            message_dialog(title="Goodbye", text="Stay safe and keep your backups handy!").run()
            break
        if action == "backup_scan":
            _run_backup_flow(console, config, token=None)
        elif action == "backup_manual":
            token = input_dialog(title="Manual Backup", text="Enter the Discord user token:").run()
            if token:
                token = token.strip()
            if token:
                _run_backup_flow(console, config, token=token)
        elif action == "restore":
            _run_restore_flow(console, config)
        elif action == "tokens":
            _show_tokens_list()
        elif action == "startup_add":
            _handle_startup_add(config)
        elif action == "startup_remove":
            _handle_startup_remove()


def _run_backup_flow(console: Console, config: AppConfig, token: str | None = None) -> None:
    buf = io.StringIO()
    console_capture = Console(accent=config.colour, stream=buf)

    def worker(update: object) -> None:
        if callable(update):
            console_capture.status_callback = lambda m: update(_strip_ansi(m))
        asyncio.run(_async_run_backup(token or "", config, console_capture))

    try:
        result = run_with_loading("Backup in progress", "Starting backup...", worker)
    except BackupError as exc:
        message_dialog(title="Backup failed", text=f"Unexpected error\n{exc}").run()
        return
    except Exception as exc:
        message_dialog(title="Backup failed", text=f"Unexpected error\n{exc}").run()
        return
    logs = buf.getvalue()
    if result and hasattr(result, "path") and result.path:
        message_dialog(
            title="Backup complete",
            text=f"Backup saved.\n{getattr(result, 'duration', 0):.1f}s",
        ).run()
    else:
        message_dialog(title="Backup failed", text=logs or "No output").run()


async def _async_run_backup(token: str, config: AppConfig, console: Console) -> object:
    http = await DiscordHTTPClient.create()
    try:
        service = BackupService()
        result = await service.run(token, config, console)
        path = service.save(result)
        return result
    finally:
        await http.aclose()


def _run_restore_flow(console: Console, config: AppConfig) -> None:
    if path_dialog is not None:
        backup_path = path_dialog(title="Select backup file", text="Choose a .bkup file to restore:").run()
    else:
        backup_path = input_dialog(
            title="Restore from backup",
            text="Enter full path to the .bkup file:",
        ).run()
    if not backup_path:
        return
    backup_path = Path(backup_path)
    if not backup_path.exists():
        message_dialog(title="File not found", text=f"Could not find {backup_path}").run()
        return
    try:
        data = json.loads(backup_path.read_text(encoding="utf-8"))
    except Exception:
        message_dialog(title="Invalid backup", text="Could not parse backup file.").run()
        return
    token_option = radiolist_dialog(
        title="User Token",
        text="Choose how to supply the user token (arrow keys + Enter)",
        values=[("scan", "Discover tokens"), ("manual", "Enter token manually")],
        ok_text="Continue",
        cancel_text="Cancel",
    ).run()
    if token_option is None:
        return
    # Stub: would prompt for bot token, restore_folders, allow_version_mismatch, then run restore
    message_dialog(title="Restore complete", text="Restore flow (stub). Implement from tui_dis.txt").run()


def _show_tokens_list() -> None:
    try:
        tokens = asyncio.run(_async_discover_tokens())
    except Exception as exc:
        message_dialog(title="Token discovery failed", text=str(exc)).run()
        return
    if not tokens:
        message_dialog(title="Tokens", text="No tokens discovered.").run()
        return
    lines = [f"{t.user_tag} ({t.user_id}) - {t.source}" for t in tokens]
    message_dialog(title="Discovered Tokens", text="\n".join(lines)).run()


def _handle_startup_add(config: AppConfig) -> None:
    selection = asyncio.run(_discover_and_choose_token(config))
    if not selection:
        return
    root = _project_root()
    executable = getattr(sys, "executable", None)
    if getattr(sys, "frozen", False):
        command = f'"{executable}"'
    else:
        command = f'cmd.exe /C python "{root / "main.py"}"'
    command += f' auto-backup --account-id {selection.user_id} --working-dir "{root}"'
    script_path = write_startup_script(command, str(root))
    message_dialog(title="Startup", text=f"Auto-backup script saved to {script_path}").run()


def _handle_startup_remove() -> None:
    if remove_startup_script():
        message_dialog(title="Startup", text="Startup script removed.").run()
    else:
        message_dialog(title="Startup", text="No startup script found.").run()


async def _discover_and_choose_token(config: AppConfig) -> DiscoveredToken | None:
    try:
        tokens = await _async_discover_tokens()
    except Exception:
        return None
    if not tokens:
        message_dialog(title="No tokens", text="No Discord tokens were found on this machine.").run()
        return None
    choice = radiolist_dialog(
        title="Select a token (arrow keys + Enter)",
        values=[(t, f"{t.user_tag} - {t.source}") for t in tokens],
        ok_text="Use token",
        cancel_text="Cancel",
    ).run()
    return choice


__all__ = ["run_tui"]
