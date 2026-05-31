from __future__ import annotations

import os
from pathlib import Path


STARTUP_FILENAME = "discord_backup_startup.vbs"


def startup_folder() -> Path:
    path = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_startup_script(command: str, working_dir: Path) -> Path:
    script_path = startup_folder() / STARTUP_FILENAME
    lines = [
        "Set oShell = CreateObject(\"WScript.Shell\")",
        f'oShell.CurrentDirectory = "{working_dir}"',
        f'oShell.run "{command}"',
    ]
    script_path.write_text("\n".join(lines), encoding="utf-8")
    return script_path


def remove_startup_script() -> bool:
    path = startup_folder() / STARTUP_FILENAME
    if path.exists():
        path.unlink()
        return True
    return False


__all__ = ["write_startup_script", "remove_startup_script", "STARTUP_FILENAME"]
