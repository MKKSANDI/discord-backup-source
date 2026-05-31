from __future__ import annotations

import base64
from datetime import datetime, timezone


def snowflake_to_timestamp(snowflake: str | int | None) -> int | None:
    if not snowflake:
        return None
    try:
        value = int(snowflake)
    except (TypeError, ValueError):
        return None
    timestamp = ((value >> 22) + 1420070400000) / 1000
    return int(timestamp)


def encode_bytes_to_base64(data: bytes | None) -> str:
    if not data:
        return ""
    return base64.b64encode(data).decode("ascii")


def decode_base64_to_bytes(payload: str | None) -> bytes:
    if not payload:
        return b""
    return base64.b64decode(payload)


def utc_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


__all__ = [
    "snowflake_to_timestamp",
    "encode_bytes_to_base64",
    "decode_base64_to_bytes",
    "utc_timestamp",
]
