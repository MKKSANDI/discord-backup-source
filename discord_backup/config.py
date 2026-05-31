from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config.yml")
_DEFAULT_CONTENT = {
    "colour": "purple",
    "group_chat_msg": 1_209_600,
}


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration loaded from config.yml."""

    colour: str = "purple"
    group_chat_msg_threshold: int = 1_209_600  # 2 weeks by default timed in seconds

    @classmethod
    def load(cls, path: Path | str = DEFAULT_CONFIG_PATH) -> "AppConfig":
        cfg_path = Path(path)
        if not cfg_path.exists():
            try:
                cfg_path.write_text(yaml.safe_dump(_DEFAULT_CONTENT, sort_keys=False), encoding="utf-8")
            except OSError:
                pass
            return cls()

        with cfg_path.open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle) or {}

        colour = str(raw.get("colour", cls.colour)).strip()
        threshold = raw.get("group_chat_msg", cls.group_chat_msg_threshold)
        try:
            threshold_int = int(threshold)
        except (TypeError, ValueError):
            threshold_int = cls.group_chat_msg_threshold

        return cls(colour=colour or cls.colour, group_chat_msg_threshold=max(0, threshold_int))


__all__ = ["AppConfig", "DEFAULT_CONFIG_PATH"]
