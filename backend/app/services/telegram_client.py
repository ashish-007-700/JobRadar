from telethon import TelegramClient
from telethon.errors import RPCError

from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_SESSION_PATH

_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            raise RuntimeError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in the environment."
            )
        _client = TelegramClient(TELEGRAM_SESSION_PATH, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    return _client


async def connect() -> None:
    client = get_client()
    if not client.is_connected():
        await client.connect()


async def disconnect() -> None:
    global _client
    if _client is not None and _client.is_connected():
        await _client.disconnect()


async def get_status() -> dict:
    try:
        client = get_client()
    except RuntimeError as exc:
        return {"connected": False, "authenticated": False, "detail": str(exc)}

    try:
        if not client.is_connected():
            await client.connect()
        authenticated = await client.is_user_authorized()
        user_label = None
        if authenticated:
            me = await client.get_me()
            user_label = getattr(me, "username", None) or getattr(me, "first_name", None)
        return {
            "connected": client.is_connected(),
            "authenticated": authenticated,
            "user": user_label,
        }
    except RPCError:
        return {"connected": False, "authenticated": False, "detail": "Telegram API error"}
    except Exception:
        return {"connected": False, "authenticated": False, "detail": "Unable to reach Telegram"}
