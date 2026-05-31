from __future__ import annotations

import os
from pathlib import Path


def _startup_path() -> Path:
    roaming = os.environ.get("APPDATA", "")
    return Path(roaming) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "backupStartup.vbs"


def remove_startup_script() -> bool:
    """Remove the auto-backup startup script if present. Returns True if removed."""
    path = _startup_path()
    if path.exists():
        path.unlink()
        return True
    return False


def write_startup_script(command: str, cwd: str) -> str:
    """Write VBS script to run command at Windows startup. Returns script path."""
    path = _startup_path()
    content = f'Set oShell = CreateObject("WScript.Shell")\noShell.run "{command}"'
    path.write_text(content, encoding="utf-8")
    return str(path)


__all__ = ["remove_startup_script", "write_startup_script"]
