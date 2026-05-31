from __future__ import annotations

import sys

from discord_backup.bootstrap import ensure_runtime_dependencies


def main() -> None:
    ensure_runtime_dependencies(verbose=True)
    if len(sys.argv) == 1:
        from discord_backup.tui import run_tui

        run_tui()
    else:
        from discord_backup.cli import run as run_cli

        run_cli()


if __name__ == "__main__":
    main()
