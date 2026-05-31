# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)
# Entry point: TUI when no args, CLI when args provided.

from __future__ import annotations

import sys

from discord_backup.bootstrap import ensure_runtime_dependencies
from discord_backup.cli import run as run_cli
from discord_backup.tui import run_tui as run_tui


def main() -> None:
    ensure_runtime_dependencies()
    if len(sys.argv) == 1:
        run_tui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
