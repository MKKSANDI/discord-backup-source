"""Dependency bootstrap helpers."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import time
from typing import Iterable, List, Tuple

try:
    from colorama import Fore, Style  # type: ignore
except Exception:  # colorama might not be installed yet
    class _Fallback:
        RESET_ALL = ""

        def __getattr__(self, _: str) -> str:
            return ""

    Fore = Style = _Fallback()  # type: ignore

_WINDOWS = os.name == "nt"

REQUIRED_PACKAGES: List[Tuple[str, str]] = [
    ("httpx", "httpx[http2]>=0.27"),
    ("h2", "h2>=4.1"),
    ("yaml", "PyYAML>=6.0"),
    ("Crypto", "pycryptodome>=3.18"),
    ("colorama", "colorama>=0.4"),
    ("prompt_toolkit", "prompt_toolkit>=3.0"),
    ("typer", "typer>=0.12"),
]

if _WINDOWS:
    REQUIRED_PACKAGES.append(("win32api", "pywin32>=305"))


def _missing_modules(specs: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    missing: List[Tuple[str, str]] = []
    for module, spec in specs:
        try:
            importlib.import_module(module)
        except Exception:
            missing.append((module, spec))
    return missing


def _progress(prefix: str, index: int, total: int) -> str:
    width = 24
    ratio = index / total if total else 1
    filled = int(width * ratio)
    bar = "#" * filled + "." * (width - filled)
    return f"{Style.RESET_ALL}{Fore.MAGENTA}{prefix}{Style.RESET_ALL}\n[{Fore.YELLOW}{bar}{Style.RESET_ALL}] {index}/{total}"


def _install_package(spec: str) -> None:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            spec,
        ]
    )


def ensure_runtime_dependencies(verbose: bool = True) -> None:
    """Ensure required modules are installed when running from source."""

    if getattr(sys, "frozen", False):
        return

    pending = _missing_modules(REQUIRED_PACKAGES)
    if not pending:
        return

    total = len(pending)
    if verbose:
        print(
            f"{Fore.CYAN}[bootstrap]{Style.RESET_ALL} Installing missing dependencies ({total} package(s))..."
        )

    for idx, (_, spec) in enumerate(pending, start=1):
        if verbose:
            print(_progress(f"Installing {spec}", idx - 1, total), end="\r", flush=True)
        try:
            _install_package(spec)
        except Exception as exc:
            message = (
                "Failed to install required dependencies.\n"
                "Run the following command manually:\n"
                f"    {sys.executable} -m pip install {spec}\n"
                f"Error: {exc}"
            )
            raise RuntimeError(message) from exc
        finally:
            if verbose:
                time.sleep(0.1)
                print(_progress(f"Installing {spec}", idx, total), end="\r", flush=True)

    if verbose:
        print()
        print(f"{Fore.GREEN}[bootstrap]{Style.RESET_ALL} Dependencies installed successfully.\n")


__all__ = ["ensure_runtime_dependencies"]
