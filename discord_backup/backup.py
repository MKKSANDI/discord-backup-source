from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

from .config import AppConfig
from .console import Console
from .http_client import DiscordHTTPClient
from .models import (
    BackupBundle,
    DMHistoryEntry,
    GuildInvite,
    GroupChatInvite,
    RelationshipSnapshot,
    UserProfile,
    format_backup_filename,
)
from .results import BackupResult
from .utils import encode_bytes_to_base64, snowflake_to_timestamp, utc_timestamp


ALLOWED_INVITE_CHANNEL_TYPES = {0, 2, 3, 5, 13}
PREFERRED_CHANNEL_KEYWORDS = ("general", "rules", "news", "chat", "welcome", "txt")
INVITE_PAYLOAD_DEFAULT = {
    "max_age": 2_592_000,
    "max_uses": 0,
    "target_type": None,
    "target_user_id": None,
    "temporary": False,
    "validate": None,
}


class BackupError(RuntimeError):
    """Raised when a fatal backup error occurs."""


@dataclass(slots=True)
class BackupService:
    http: DiscordHTTPClient
    token: str
    config: AppConfig
    console: Console

    guild_invite_limit: int = 4

    async def run(self) -> BackupResult:
        start = time.perf_counter()
        me = await self._fetch_me()
        profile = await self._build_profile(me)

        relationships_task = asyncio.create_task(self._fetch_relationships())
        settings_task = asyncio.create_task(self._fetch_settings())
        channels_task = asyncio.create_task(self._fetch_channels())
        guilds_task = asyncio.create_task(self._fetch_guild_invites())

        relationships, settings, channels, guild_result = await asyncio.gather(
            relationships_task,
            settings_task,
            channels_task,
            guilds_task,
        )

        group_chats, gc_success = await self._build_group_chats(channels)
        dm_history = self._build_dm_history(channels)

        bundle = BackupBundle(
            version="2.0.0-dev",
            profile=profile,
            relationships=relationships,
            guilds=guild_result.invites,
            group_chats=group_chats,
            dm_history=dm_history,
            guild_folders=settings.guild_folders,
            settings=settings.proto_settings,
        )

        duration = time.perf_counter() - start

        return BackupResult(
            bundle=bundle,
            duration=duration,
            guild_success=guild_result.success,
            guild_total=guild_result.total,
            group_chat_success=gc_success,
            group_chat_total=len(group_chats),
        )

    async def save(self, result: BackupResult, directory: Path = Path("backups")) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        tag = f"{result.bundle.profile.username}#{result.bundle.profile.discriminator}"
        filename = format_backup_filename(tag, timestamp=utc_timestamp())
        target = directory / filename
        with target.open("w", encoding="utf-8") as handle:
            json.dump(result.bundle.to_dict(), handle, indent=4)
        return target

    async def _fetch_me(self) -> dict[str, Any]:
        self.console.info("Authenticating token...")
        response = await self.http.request(
            "GET",
            "users/@me",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        if response.status_code != 200:
            raise BackupError("Invalid token or authentication failed")
        payload = response.json()
        self.console.success("Authenticated user info")
        return payload

    async def _fetch_asset(self, url: str) -> bytes:
        try:
            response = await self.http.request(
                "GET",
                url,
                token=None,
                super_properties=False,
                include_locale=False,
                origin=None,
                headers={"Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"},
            )
            if response.status_code == 200:
                return response.content
        except httpx.HTTPError:
            pass
        return b""

    async def _build_profile(self, me: dict[str, Any]) -> UserProfile:
        avatar_bytes = b""
        if me.get("avatar"):
            avatar_url = f"https://cdn.discordapp.com/avatars/{me['id']}/{me['avatar']}.png?size=4096"
            avatar_bytes = await self._fetch_asset(avatar_url)

        banner_bytes = b""
        if me.get("banner"):
            banner_url = f"https://cdn.discordapp.com/banners/{me['id']}/{me['banner']}.png?size=4096"
            banner_bytes = await self._fetch_asset(banner_url)

        profile = UserProfile(
            user_id=str(me.get("id")),
            username=me.get("username", "unknown"),
            discriminator=str(me.get("discriminator", "0")),
            bio=me.get("bio", ""),
            avatar_bytes=encode_bytes_to_base64(avatar_bytes),
            banner_bytes=encode_bytes_to_base64(banner_bytes),
        )
        self.console.success("Captured profile, avatar and banner")
        return profile

    async def _fetch_relationships(self) -> RelationshipSnapshot:
        response = await self.http.request(
            "GET",
            "users/@me/relationships",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        data = response.json() if response.status_code == 200 else []
        relationship_map: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
        for user in data:
            user_type = user.get("type")
            user_id = str(user.get("id"))
            if user_type in relationship_map and user_id:
                relationship_map[user_type].append(user_id)
        self.console.success("Fetched relationships")
        return RelationshipSnapshot(
            friends=relationship_map[1],
            blocked=relationship_map[2],
            incoming=relationship_map[3],
            outgoing=relationship_map[4],
        )

    @dataclass(slots=True)
    class _Settings:
        guild_folders: list[dict[str, Any]]
        proto_settings: dict[str, Any] | None

    async def _fetch_settings(self) -> _Settings:
        folders_response = await self.http.request(
            "GET",
            "users/@me/settings",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        folders_payload = folders_response.json() if folders_response.status_code == 200 else {}
        folders = folders_payload.get("guild_folders", [])

        proto_response = await self.http.request(
            "GET",
            "users/@me/settings-proto/2",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        proto_settings = (
            proto_response.json().get("settings")
            if proto_response.status_code == 200
            else None
        )

        self.console.success("Backed up settings and guild folders")
        return self._Settings(guild_folders=folders, proto_settings=proto_settings)

    @dataclass(slots=True)
    class _GuildResult:
        invites: list[GuildInvite]
        success: int
        total: int

    async def _fetch_guild_invites(self) -> _GuildResult:
        response = await self.http.request(
            "GET",
            "users/@me/guilds",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        guilds = response.json() if response.status_code == 200 else []
        invites: list[GuildInvite] = []
        success = 0
        total = len(guilds)

        for index, guild in enumerate(guilds, start=1):
            self.console.info(
                f"[{index}/{total}] Preparing invite for {guild.get('name', 'Unknown')}"
            )
            invite = await self._create_invite_for_guild(guild)
            invites.append(invite)
            if invite.invite_code and invite.invite_code != "Unable to create.":
                success += 1
            else:
                self.console.warn(
                    f"Failed to create invite for {guild.get('name', 'Unknown')}"
                )
        return self._GuildResult(invites=invites, success=success, total=total)

    async def _create_invite_for_guild(self, guild: dict[str, Any]) -> GuildInvite:
        guild_id = str(guild.get("id"))
        name = guild.get("name", "Unknown")
        if "VANITY_URL" in guild.get("features", []):
            vanity_response = await self.http.request(
                "GET",
                f"guilds/{guild_id}",
                token=self.token,
                include_debug=True,
                include_locale=True,
                super_properties=True,
            )
            if vanity_response.status_code == 200:
                code = vanity_response.json().get("vanity_url_code")
                if code:
                    self.console.success(f"Using vanity invite for {name}: {code}")
                    return GuildInvite(guild_id=guild_id, name=name, invite_code=code)

        channels = await self.http.json(
            "GET",
            f"guilds/{guild_id}/channels",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )

        typed_channels = [c for c in channels if c.get("type") in ALLOWED_INVITE_CHANNEL_TYPES]
        prioritized = sorted(
            typed_channels,
            key=lambda channel: (
                min(
                    (channel.get("name", "").find(keyword) if keyword in channel.get("name", "") else 999)
                    for keyword in PREFERRED_CHANNEL_KEYWORDS
                ),
                channel.get("position", 9999),
            ),
        )

        for channel in prioritized:
            code = await self._attempt_invite_creation(channel, payload=INVITE_PAYLOAD_DEFAULT)
            if code:
                self.console.success(
                    f"Invite created in #{channel.get('name', 'unknown')} -> {code}"
                )
                return GuildInvite(guild_id=guild_id, name=name, invite_code=code)

        for channel in prioritized:
            code = await self._attempt_invite_creation(channel, payload={"max_age": 0, "max_uses": 0, "temporary": False})
            if code:
                self.console.success(
                    f"Fallback invite in #{channel.get('name', 'unknown')} -> {code}"
                )
                return GuildInvite(guild_id=guild_id, name=name, invite_code=code)

        return GuildInvite(guild_id=guild_id, name=name, invite_code="Unable to create.")

    async def _attempt_invite_creation(self, channel: dict[str, Any], payload: dict[str, Any]) -> str | None:
        channel_id = channel.get("id")
        if not channel_id:
            return None
        response = await self.http.request(
            "POST",
            f"channels/{channel_id}/invites",
            token=self.token,
            json_payload=payload,
            include_debug=True,
            include_locale=True,
            super_properties=True,
            expected_status=(200,),
        )
        if response.status_code == 200:
            return response.json().get("code")
        return None

    async def _fetch_channels(self) -> list[dict[str, Any]]:
        response = await self.http.request(
            "GET",
            "users/@me/channels",
            token=self.token,
            include_debug=True,
            include_locale=True,
            super_properties=True,
        )
        channels = response.json() if response.status_code == 200 else []
        self.console.success(f"Loaded {len(channels)} private channels")
        return channels

    async def _build_group_chats(self, channels: list[dict[str, Any]]) -> tuple[list[GroupChatInvite], int]:
        threshold = max(0, self.config.group_chat_msg_threshold)
        group_channels = [c for c in channels if c.get("type") == 3]
        invites: list[GroupChatInvite] = []
        success = 0
        for index, channel in enumerate(group_channels, start=1):
            name = channel.get("name", f"GC-{index}")
            self.console.info(
                f"[{index}/{len(group_channels)}] Processing group chat {name}"
            )
            last_message_id = channel.get("last_message_id")
            age_seconds = 0
            timestamp = snowflake_to_timestamp(last_message_id)
            if timestamp:
                age_seconds = time.time() - timestamp

            if threshold and age_seconds > threshold:
                self.console.warn(
                    f"Skipped group chat '{name}' (inactive for {int(age_seconds)}s)"
                )
                continue

            response = await self.http.request(
                "POST",
                f"channels/{channel['id']}/invites",
                token=self.token,
                json_payload={"max_age": 604800},
                include_debug=True,
                include_locale=True,
                super_properties=True,
                expected_status=(200,),
            )
            if response.status_code == 200:
                code = response.json().get("code")
                invites.append(
                    GroupChatInvite(
                        channel_id=str(channel.get("id")),
                        name=name,
                        invite_code=code,
                        owner_id=str(channel.get("owner_id")),
                        recipients=[str(user.get("id")) for user in channel.get("recipients", [])],
                        last_message_id=last_message_id,
                    )
                )
                success += 1
                self.console.success(f"Invite created for group chat {name}: {code}")
            else:
                invites.append(
                    GroupChatInvite(
                        channel_id=str(channel.get("id")),
                        name=name,
                        invite_code="Unable to create.",
                        owner_id=str(channel.get("owner_id")),
                        recipients=[str(user.get("id")) for user in channel.get("recipients", [])],
                        last_message_id=last_message_id,
                    )
                )
                self.console.warn(f"Failed to create invite for group chat {name}")
        return invites, success

    def _build_dm_history(self, channels: list[dict[str, Any]]) -> list[DMHistoryEntry]:
        dms = [c for c in channels if c.get("type") == 1]
        history: list[DMHistoryEntry] = []
        for dm in dms:
            recipient = (dm.get("recipients") or [{}])[0]
            user_tag = f"{recipient.get('username', 'unknown')}#{recipient.get('discriminator', '0000')}"
            history.append(
                DMHistoryEntry(
                    user_id=str(recipient.get("id")),
                    user_tag=user_tag,
                    last_message_id=dm.get("last_message_id"),
                    timestamp=snowflake_to_timestamp(dm.get("last_message_id")),
                )
            )
        history.sort(key=lambda entry: int(entry.last_message_id or 0), reverse=True)
        self.console.success(f"Collected {len(history)} DM history entries")
        return history


__all__ = ["BackupService", "BackupError"]
