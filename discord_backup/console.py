# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)
"""Lightweight coloured console helper."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from colorama import Fore, Style

_COLOUR_MAP = {
    "light_red": Fore.LIGHTRED_EX,
    "dark_red": Fore.RED,
    "yellow": Fore.YELLOW,
    "dark_blue": Fore.BLUE,
    "light_blue": Fore.LIGHTBLUE_EX,
    "dark_cyan": Fore.CYAN,
    "light_cyan": Fore.LIGHTCYAN_EX,
    "green": Fore.LIGHTGREEN_EX,
    "purple": Fore.MAGENTA,
    "pink": Fore.LIGHTMAGENTA_EX,
    "gray": Fore.LIGHTBLACK_EX,
    "black": Fore.BLACK,
    "white": Fore.WHITE,
}


@dataclass
class Console:
    """Lightweight coloured console helper."""

    accent: str = "purple"
    stream: object = sys.stdout
    status_callback: Callable[[str], None] | None = None

    def colour(self, name: str) -> str:
        return _COLOUR_MAP.get(name, "purple")

    def _notify(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)

    def _emit(
        self,
        prefix_colour: str,
        message: str,
        indent: int = 0,
        end: str = "\n",
    ) -> None:
        padding = "  " * max(0, indent)
        prefix = self.colour(prefix_colour) if prefix_colour else ""
        line = f"{padding}{prefix}{message}{Style.RESET_ALL}{end}"
        self.stream.write(line)
        self._notify(message)

    def info(self, message: str, indent: int = 0) -> None:
        self._emit("white", message, indent)

    def success(self, message: str, indent: int = 0) -> None:
        accent_colour = self.colour(self.accent)
        highlighted = f"{accent_colour}{message}{Style.RESET_ALL}"
        self._emit("green", highlighted, indent)

    def warn(self, message: str, indent: int = 0) -> None:
        self._emit("yellow", message, indent)

    def error(self, message: str, indent: int = 0) -> None:
        self._emit("light_red", message, indent)

    def prompt(self, message: str, indent: int = 0, end: str = " ") -> None:
        padding = "  " * max(0, indent)
        prefix = self.colour("light_blue")
        self.stream.write(f"{padding}{prefix}{message}{Style.RESET_ALL}{end}")
        self.stream.flush()
        self._notify(message)

    def rule(self, label: str = "", bar: str = "------------------------------------") -> None:
        self.info(bar, indent=2)
        if label:
            self.info(label, indent=2)

    def bullet_list(self, items: list[str], indent: int = 0) -> None:
        for item in items:
            self.info(f"• {item}", indent)


__all__ = ["Console"]
