"""Dependency bootstrap helpers."""

from __future__ import annotations

import importlib
import subprocess
import sys
from typing import List, Tuple

REQUIRED_PACKAGES: List[Tuple[str, str]] = [
    ("colorama", "colorama>=0.4.6"),
    ("httpx", "httpx>=0.24.0"),
    ("yaml", "PyYAML>=6.0"),
    ("typer", "typer[all]>=0.9.0"),
    ("prompt_toolkit", "prompt_toolkit>=3.0.0"),
    ("rich", "rich>=13.0.0"),
]


def ensure_runtime_dependencies(verbose: bool = False) -> None:
    """Ensure required modules are installed when running from source."""
    if getattr(sys, "frozen", False):
        return
    pending = [spec for spec in REQUIRED_PACKAGES if not _module_available(spec[0])]
    if not pending:
        return
    total = len(pending)
    if verbose:
        print(f"[bootstrap] Installing missing dependencies ({total} package(s))...")
    for idx, (_, spec) in enumerate(pending, 1):
        if verbose:
            print(f"Installing {spec}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", spec],
                stdout=subprocess.DEVNULL if not verbose else None,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to install {spec}. Run: {sys.executable} -m pip install {spec}"
            ) from exc


def _module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


__all__ = ["ensure_runtime_dependencies"]
