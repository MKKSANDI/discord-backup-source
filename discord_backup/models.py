# Decompiled from DiscordBackup.exe (PyInstaller, Python 3.13)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class UserProfile:
    user_id: str
    username: str
    discriminator: str
    bio: str
    avatar_bytes: str | None = None
    banner_bytes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "discriminator": self.discriminator,
            "bio": self.bio,
            "avatar_bytes": self.avatar_bytes,
            "banner_bytes": self.banner_bytes,
        }


@dataclass(slots=True)
class RelationshipSnapshot:
    friends: list[str]
    blocked: list[str]
    incoming: list[str]
    outgoing: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "friends": self.friends,
            "blocked": self.blocked,
            "incoming": self.incoming,
            "outgoing": self.outgoing,
        }


@dataclass(slots=True)
class GuildInvite:
    guild_id: str
    name: str
    invite_code: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "guild_id": self.guild_id,
            "name": self.name,
            "invite_code": self.invite_code or "Unable to create.",
        }


@dataclass(slots=True)
class GroupChatInvite:
    channel_id: str
    name: str
    invite_code: str | None
    owner_id: str
    recipients: list[str]
    last_message_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "invite_code": self.invite_code,
            "owner_id": self.owner_id,
            "recipients": self.recipients,
            "last_message_id": self.last_message_id,
        }


@dataclass(slots=True)
class DMHistoryEntry:
    user_id: str
    user_tag: str
    last_message_id: str | None
    timestamp: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_tag": self.user_tag,
            "last_message_id": self.last_message_id,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class BackupBundle:
    version: str
    profile: UserProfile
    relationships: RelationshipSnapshot
    guilds: list[GuildInvite]
    group_chats: list[GroupChatInvite]
    dm_history: list[DMHistoryEntry]
    guild_folders: list[dict[str, Any]]
    settings: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "version": self.version,
            "guilds": [g.to_dict() for g in self.guilds],
            "group-chats": [gc.to_dict() for gc in self.group_chats],
            "dm-history": [dm.to_dict() for dm in self.dm_history],
            "guild_folders": self.guild_folders,
            "settings": self.settings,
        }
        data.update(self.profile.to_dict())
        data.update(self.relationships.to_dict())
        return data


def format_backup_filename(tag: str, timestamp: float | None = None) -> str:
    dt = datetime.utcfromtimestamp(timestamp or datetime.utcnow().timestamp())
    safe_tag = tag.replace("#", "-").replace(" ", "_")
    return f"{safe_tag} @ {dt.strftime('%Y-%m-%d %H-%M-%S')}.bkup"


__all__ = [
    "UserProfile",
    "RelationshipSnapshot",
    "GuildInvite",
    "GroupChatInvite",
    "DMHistoryEntry",
    "BackupBundle",
    "format_backup_filename",
]
