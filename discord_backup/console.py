from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, Iterable

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


@dataclass(slots=True)
class Console:
    """Lightweight coloured console helper."""

    accent: str = "purple"
    stream: any = sys.stdout
    status_callback: Callable[[str], None] | None = None

    def colour(self, name: str) -> str:
        return _COLOUR_MAP.get(name, _COLOUR_MAP["purple"])

    def _notify(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)

    def _safe_text(self, text: str) -> str:
        encoding = getattr(self.stream, "encoding", None) or "utf-8"
        try:
            text.encode(encoding, errors="strict")
            return text
        except UnicodeEncodeError:
            return text.encode(encoding, errors="replace").decode(encoding, errors="replace")

    def _emit(self, prefix_colour: str, message: str, *, indent: int = 0, end: str = "\n") -> None:
        padding = " " * max(indent, 0)
        prefix = f"{self.colour(prefix_colour)}>{Style.RESET_ALL} "
        payload = f"{padding}{prefix}{message}{Style.RESET_ALL}{end}"
        self.stream.write(self._safe_text(payload))
        self._notify(message)

    def info(self, message: str, *, indent: int = 0) -> None:
        self._emit("white", message, indent=indent)

    def success(self, message: str, *, indent: int = 0) -> None:
        accent_colour = self.colour(self.accent)
        highlighted = f"{accent_colour}{message}{Style.RESET_ALL}"
        self._emit("green", highlighted, indent=indent)

    def warn(self, message: str, *, indent: int = 0) -> None:
        self._emit("yellow", message, indent=indent)

    def error(self, message: str, *, indent: int = 0) -> None:
        self._emit("light_red", message, indent=indent)

    def prompt(self, message: str, *, indent: int = 0, end: str = "") -> None:
        padding = " " * max(indent, 0)
        prefix = f"{self.colour('light_blue')}>{Style.RESET_ALL} "
        payload = f"{padding}{prefix}{message}{Style.RESET_ALL}{end}"
        self.stream.write(self._safe_text(payload))
        self.stream.flush()
        self._notify(message)

    def rule(self, label: str | None = None) -> None:
        bar = "-" * 36
        if label:
            self.info(f"{bar} {label} {bar}")
        else:
            self.info(bar * 2)

    def bullet_list(self, items: Iterable[str], *, indent: int = 2) -> None:
        for item in items:
            self.info(f"- {item}", indent=indent)


__all__ = ["Console"]
