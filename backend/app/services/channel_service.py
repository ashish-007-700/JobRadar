import re
from urllib.parse import urlparse

from postgrest.exceptions import APIError
from telethon.errors import (
    ChannelPrivateError,
    RPCError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.tl.types import Channel

from app.services import telegram_client
from app.services.supabase_client import get_supabase_client

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class ChannelValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def normalize_channel_username(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ChannelValidationError("Channel username or link is required.")

    path = urlparse(value).path if value.startswith(("http://", "https://")) else value
    parts = [part for part in path.split("/") if part]
    if parts and parts[0].lower() == "s":
        parts = parts[1:]
    if not parts:
        raise ChannelValidationError("Could not parse a channel username from the input.")

    username = parts[0].lstrip("@")
    if not USERNAME_PATTERN.match(username):
        raise ChannelValidationError("Invalid Telegram username format.")

    return username


async def resolve_channel(username: str) -> dict:
    try:
        client = telegram_client.get_client()
    except RuntimeError as exc:
        raise ChannelValidationError(str(exc), status_code=503) from exc

    if not client.is_connected():
        await client.connect()

    if not await client.is_user_authorized():
        raise ChannelValidationError(
            "Telegram authentication unavailable. Run the login script first.",
            status_code=503,
        )

    try:
        entity = await client.get_entity(username)
    except (UsernameNotOccupiedError, UsernameInvalidError, ValueError) as exc:
        raise ChannelValidationError("Telegram channel not found.") from exc
    except ChannelPrivateError as exc:
        raise ChannelValidationError(
            "Channel inaccessible. Your Telegram account cannot view this channel."
        ) from exc
    except RPCError as exc:
        raise ChannelValidationError(
            "Telegram API error while resolving the channel.", status_code=502
        ) from exc

    if not isinstance(entity, Channel):
        raise ChannelValidationError("This is not a supported Telegram channel.")

    return {
        "telegram_channel_id": entity.id,
        "channel_username": entity.username or username,
        "channel_name": entity.title,
    }


async def list_channels() -> list[dict]:
    client = get_supabase_client()
    try:
        result = client.table("channels").select("*").order("created_at", desc=True).execute()
    except APIError as exc:
        raise ChannelValidationError(str(exc), status_code=502) from exc
    return result.data


async def create_channel(raw_input: str) -> dict:
    username = normalize_channel_username(raw_input)
    resolved = await resolve_channel(username)

    client = get_supabase_client()
    try:
        result = (
            client.table("channels")
            .insert(
                {
                    "channel_username": resolved["channel_username"],
                    "channel_name": resolved["channel_name"],
                    "telegram_channel_id": resolved["telegram_channel_id"],
                }
            )
            .execute()
        )
    except APIError as exc:
        if exc.code == "23505":
            raise ChannelValidationError(
                "This channel is already configured.", status_code=409
            ) from exc
        raise ChannelValidationError("Failed to save the channel.", status_code=500) from exc

    return result.data[0]


def _raise_for_api_error(exc: APIError, channel_id: str) -> None:
    if exc.code == "22P02":  # invalid input syntax, e.g. a malformed UUID
        raise ChannelValidationError(f"Invalid channel id '{channel_id}'.", status_code=400) from exc
    raise ChannelValidationError(str(exc), status_code=502) from exc


async def update_channel_enabled(channel_id: str, enabled: bool) -> dict:
    client = get_supabase_client()
    try:
        result = client.table("channels").update({"enabled": enabled}).eq("id", channel_id).execute()
    except APIError as exc:
        _raise_for_api_error(exc, channel_id)
    if not result.data:
        raise ChannelValidationError("Channel not found.", status_code=404)
    return result.data[0]


async def delete_channel(channel_id: str) -> None:
    client = get_supabase_client()
    try:
        result = client.table("channels").delete().eq("id", channel_id).execute()
    except APIError as exc:
        _raise_for_api_error(exc, channel_id)
    if not result.data:
        raise ChannelValidationError("Channel not found.", status_code=404)


async def revalidate_channel(channel_id: str) -> dict:
    client = get_supabase_client()
    try:
        result = client.table("channels").select("*").eq("id", channel_id).execute()
    except APIError as exc:
        _raise_for_api_error(exc, channel_id)
    if not result.data:
        raise ChannelValidationError("Channel not found.", status_code=404)
    channel = result.data[0]

    try:
        resolved = await resolve_channel(channel["channel_username"])
    except ChannelValidationError as exc:
        if exc.status_code == 503:
            raise
        return {"accessible": False, "detail": exc.message, "channel": channel}

    updates = {}
    if resolved["telegram_channel_id"] != channel.get("telegram_channel_id"):
        updates["telegram_channel_id"] = resolved["telegram_channel_id"]
    if resolved["channel_name"] != channel.get("channel_name"):
        updates["channel_name"] = resolved["channel_name"]

    if updates:
        try:
            update_result = client.table("channels").update(updates).eq("id", channel_id).execute()
        except APIError as exc:
            raise ChannelValidationError(str(exc), status_code=502) from exc
        if update_result.data:
            channel = update_result.data[0]

    return {"accessible": True, "channel": channel}
