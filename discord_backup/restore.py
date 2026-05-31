from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx

from .console import Console
from .http_client import DiscordHTTPClient
from .utils import decode_base64_to_bytes, snowflake_to_timestamp

READ_ME = (
    "After you have joined all the servers, run `restore folders` to rebuild folder ordering.\n\n"
    "Coded with <3 by https://github.com/itschasa/discord-backup"
)


class RestoreError(RuntimeError):
    ...


@dataclass(slots=True)
class RestoreSummary:
    duration: float
    guild_id: str
    folder_restore_attempted: bool
    favourite_gifs_status: str


@dataclass(slots=True)
class RestoreService:
    http: DiscordHTTPClient
    token: str
    bot_token: str
    backup: dict[str, Any]
    console: Console

    async def run(self, *, restore_folders: bool, expected_version: str | None = None, allow_mismatch: bool = False) -> RestoreSummary:
        start = time.perf_counter()

        if expected_version and not allow_mismatch:
            backup_version = self.backup.get("version")
            if backup_version and backup_version != expected_version:
                raise RestoreError(
                    f"Backup was created on {backup_version}, current version is {expected_version}. Use --allow-version-mismatch to continue."
                )

        await self._validate_user_token()
        await self._validate_bot_token()

        await self._write_user_assets()
        favourite_status = await self._restore_favourite_gifs()

        guild_id = await self._rebuild_backup_server()

        if restore_folders:
            await self._restore_folders()

        duration = time.perf_counter() - start
        return RestoreSummary(
            duration=duration,
            guild_id=guild_id,
            folder_restore_attempted=restore_folders,
            favourite_gifs_status=favourite_status,
        )

    async def _validate_user_token(self) -> None:
        response = await self.http.request(
            "GET",
            "users/@me",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        if response.status_code != 200:
            raise RestoreError("User token is invalid or unauthorized")
        self.console.success("Validated user token")

    async def _validate_bot_token(self) -> None:
        async with httpx.AsyncClient(base_url="https://discord.com/api/v9", timeout=30.0, http2=True) as bot_client:
            response = await bot_client.get(
                "users/@me",
                headers={
                    "Authorization": f"Bot {self.bot_token}",
                    "User-Agent": "DiscordBot (https://discord.com, 1.0)",
                    "Accept-Encoding": "identity",
                },
            )
        if response.status_code != 200:
            raise RestoreError("Bot token is invalid or missing required scopes")
        self.console.success("Validated bot token")

    async def _write_user_assets(self) -> None:
        timestamp = int(time.time())
        avatar_bytes = decode_base64_to_bytes(self.backup.get("avatar-bytes"))
        if avatar_bytes:
            path = Path(f"pfp-{timestamp}.gif")
            path.write_bytes(avatar_bytes)
            self.console.success(f"Saved avatar to {path}")

        banner_bytes = decode_base64_to_bytes(self.backup.get("banner-bytes"))
        if banner_bytes:
            path = Path(f"banner-{timestamp}.gif")
            path.write_bytes(banner_bytes)
            self.console.success(f"Saved banner to {path}")

        bio_path = Path(f"bio-{timestamp}.txt")
        bio_path.write_text(self.backup.get("bio", ""), encoding="utf-8")
        self.console.success(f"Saved bio to {bio_path}")

    async def _restore_favourite_gifs(self) -> str:
        settings = self.backup.get("settings")
        if not settings:
            self.console.warn("No favourite GIF settings present in backup")
            return "Skipped"
        response = await self.http.request(
            "PATCH",
            "users/@me/settings-proto/2",
            token=self.token,
            json_payload={"settings": settings},
            include_debug=True,
            include_locale=True,
            super_properties=True,
            expected_status=(200,),
        )
        if response.status_code == 200:
            self.console.success("Restored favourite GIFs")
            return "Done"
        self.console.warn(f"Failed to restore favourite GIFs ({response.status_code})")
        return "Failed"

    async def _rebuild_backup_server(self) -> str:
        channels = self._build_template_channels()
        icon_b64 = await self._fetch_icon_image()
        payload = {
            "name": "Discord Backup",
            "icon": icon_b64,
            "channels": channels,
            "system_channel_id": "0",
            "guild_template_code": "2TffvPucqHkN",
        }

        response = await self.http.request(
            "POST",
            "guilds",
            token=self.token,
            json_payload=payload,
            include_debug=True,
            include_locale=True,
            super_properties=True,
            expected_status=(201, 200),
        )
        if response.status_code not in {200, 201}:
            raise RestoreError(f"Failed to create backup guild ({response.status_code})")
        guild_id = str(response.json().get("id"))
        self.console.success(f"Created backup guild ({guild_id})")

        channel_map = await self._fetch_guild_channels(guild_id)

        await self._send_guidance(channel_map["read-me"], guild_id, READ_ME)
        await self._send_missing_guilds(channel_map["missing-guilds"], guild_id)
        await self._send_group_chats(channel_map["group-chats"], guild_id)
        await self._send_dm_history(channel_map["dm-history"], guild_id)
        await self._send_relationships(channel_map["friends"], guild_id)
        await self._send_folder_breakdown(channel_map, guild_id)

        return guild_id

    def _build_template_channels(self) -> list[dict[str, Any]]:
        channels = [
            {"id": "0", "parent_id": None, "name": "read-me", "type": 0},
            {"id": "1", "parent_id": None, "name": "group-chats", "type": 0},
            {"id": "2", "parent_id": None, "name": "missing-guilds", "type": 0},
            {"id": "3", "parent_id": None, "name": "dm-history", "type": 0},
            {"id": "4", "parent_id": None, "name": "friends", "type": 0},
        ]
        for index, folder in enumerate(self.backup.get("guild_folders", []), start=5):
            channels.append(
                {
                    "id": str(index),
                    "parent_id": None,
                    "name": f"folder-{index-5}",
                    "type": 0,
                }
            )
        return channels

    async def _fetch_icon_image(self) -> str | None:
        try:
            async with httpx.AsyncClient() as client:
                image = await client.get("https://i.imgur.com/b6B3Fbw.jpg")
                image.raise_for_status()
                data = base64.b64encode(image.content).decode("ascii")
                if len(data) < 500:
                    return None
                return f"data:image/jpeg;base64,{data}"
        except httpx.HTTPError:
            return None

    async def _fetch_guild_channels(self, guild_id: str) -> dict[str, str]:
        response = await self.http.request(
            "GET",
            f"guilds/{guild_id}/channels",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        channel_map: dict[str, str] = {}
        for channel in response.json():
            channel_map[channel["name"]] = str(channel["id"])
        return channel_map

    async def _send_guidance(self, channel_id: str, guild_id: str, message: str) -> None:
        await self._send_messages(channel_id, guild_id, [message])

    async def _send_missing_guilds(self, channel_id: str, guild_id: str) -> None:
        messages: list[str] = [""]
        for guild in self.backup.get("guilds", []):
            invite_code = guild.get("invite-code")
            if invite_code and invite_code != "Unable to create.":
                entry = f"{guild.get('name')} (`{guild.get('id')}`)\nhttps://discord.gg/{invite_code}\n\n"
            else:
                entry = f"{guild.get('name')} (`{guild.get('id')}`) - invite unavailable (missing perms)\n\n"
            if len(messages[-1]) + len(entry) > 1900:
                messages.append(entry)
            else:
                messages[-1] += entry
        await self._send_messages(channel_id, guild_id, messages)

    async def _send_group_chats(self, channel_id: str, guild_id: str) -> None:
        header = (
            "**Group Chats**\nInvites expire after 7 days. Ensure your old account is still present.\n\n"
        )
        messages: list[str] = [header]
        for group in self.backup.get("group-chats", []):
            code = group.get("invite-code")
            if not code or code == "Unable to create.":
                entry = f"{group.get('name')} - invite unavailable\n\n"
            else:
                entry = f"{group.get('name')}\nhttps://discord.gg/{code}\n\n"
            if len(messages[-1]) + len(entry) > 1900:
                messages.append(entry)
            else:
                messages[-1] += entry
        await self._send_messages(channel_id, guild_id, messages)

    async def _send_dm_history(self, channel_id: str, guild_id: str) -> None:
        messages = ["**DM History**\nFormat: `user | mention | last_dm`\n\n"]
        for dm in self.backup.get("dm-history", []):
            timestamp = dm.get("timestamp")
            if timestamp:
                marker = f"<t:{int(timestamp)}:R>"
            else:
                marker = "never"
            entry = f"{dm.get('user')} | <@{dm.get('user_id')}> | {marker}\n"
            if len(messages[-1]) + len(entry) > 1900:
                messages.append(entry)
            else:
                messages[-1] += entry
        await self._send_messages(channel_id, guild_id, messages)

    async def _send_relationships(self, channel_id: str, guild_id: str) -> None:
        sections = {
            "Friends": self.backup.get("friends", []),
            "Incoming": self.backup.get("incoming", []),
            "Outgoing": self.backup.get("outgoing", []),
            "Blocked": self.backup.get("blocked", []),
        }
        messages = ["**Relationships**\n\n"]
        for title, ids in sections.items():
            if not ids:
                continue
            header = f"\n{title}\n"
            if len(messages[-1]) + len(header) > 1900:
                messages.append(header)
            else:
                messages[-1] += header
            for snowflake in ids:
                tag = await self._lookup_user_tag(snowflake)
                entry = f"<@{snowflake}> | {tag}\n"
                if len(messages[-1]) + len(entry) > 1900:
                    messages.append(entry)
                else:
                    messages[-1] += entry
        await self._send_messages(channel_id, guild_id, messages)

    async def _send_folder_breakdown(self, channel_map: dict[str, str], guild_id: str) -> None:
        folders = self.backup.get("guild_folders", [])
        for index, folder in enumerate(folders):
            channel_name = f"folder-{index}"
            channel_id = channel_map.get(channel_name)
            if not channel_id:
                continue
            header = f"**Folder:** {folder.get('name', f'Folder {index}')}\n\n"
            messages = [header]
            for guild_id_str in folder.get("guild_ids", []):
                invite = next((g for g in self.backup.get("guilds", []) if str(g.get("id")) == str(guild_id_str)), None)
                if invite and invite.get("invite-code") and invite.get("invite-code") != "Unable to create.":
                    entry = f"{invite.get('name')} (`{guild_id_str}`)\nhttps://discord.gg/{invite['invite-code']}\n\n"
                else:
                    entry = f"Missing invite for `{guild_id_str}`\n\n"
                if len(messages[-1]) + len(entry) > 1900:
                    messages.append(entry)
                else:
                    messages[-1] += entry
            await self._send_messages(channel_id, guild_id, messages)

    async def _send_messages(self, channel_id: str, guild_id: str, messages: Sequence[str]) -> None:
        for message in messages:
            if not message.strip():
                continue
            payload = {
                "content": message[:1999],
                "nonce": self._nonce(),
                "tts": False,
            }
            response = await self.http.request(
                "POST",
                f"channels/{channel_id}/messages",
                token=self.token,
                json_payload=payload,
                include_debug=True,
                include_locale=True,
                super_properties=True,
                referer=f"https://discord.com/channels/{guild_id}/{channel_id}",
                expected_status=(200,),
            )
            if response.status_code == 200:
                self.console.success(f"Sent message to channel {channel_id}")
            else:
                self.console.warn(
                    f"Failed to send message to channel {channel_id} ({response.status_code})"
                )
            await asyncio.sleep(1)

    def _nonce(self) -> str:
        return str(int((time.time() * 1000 - 1420070400000) << 22))

    async def _lookup_user_tag(self, user_id: str) -> str:
        async with httpx.AsyncClient(base_url="https://discord.com/api/v9", timeout=30.0, http2=True) as client:
            while True:
                response = await client.get(
                    f"users/{user_id}",
                    headers={
                        "Authorization": f"Bot {self.bot_token}",
                        "User-Agent": "DiscordBot (https://discord.com, 1.0)",
                        "Accept-Encoding": "identity",
                    },
                )
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 1)
                    await asyncio.sleep(float(retry_after) + 0.25)
                    continue
                if response.status_code != 200:
                    return "Unknown"
                data = response.json()
                return f"{data.get('username')}#{data.get('discriminator')}"

    async def _restore_folders(self) -> None:
        folders = self.backup.get("guild_folders")
        if not folders:
            self.console.warn("Backup does not contain guild folders")
            return

        response = await self.http.request(
            "GET",
            "users/@me/guilds",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        owned_ids = {str(guild.get("id")) for guild in response.json()}

        payload = []
        for folder in folders:
            filtered = [str(gid) for gid in folder.get("guild_ids", []) if str(gid) in owned_ids]
            payload.append({"name": folder.get("name"), "color": folder.get("color"), "guild_ids": filtered})

        response = await self.http.request(
            "PATCH",
            "users/@me/settings",
            token=self.token,
            json_payload={"guild_folders": payload},
            include_debug=True,
            include_locale=True,
            super_properties=True,
            expected_status=(200,),
        )
        if response.status_code == 200:
            self.console.success("Restored guild folders")
        else:
            self.console.warn(f"Failed to restore guild folders ({response.status_code})")


__all__ = ["RestoreService", "RestoreError", "RestoreSummary"]

