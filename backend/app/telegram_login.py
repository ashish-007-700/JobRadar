"""One-time interactive Telegram login.

Run from the backend/ directory with the virtualenv active:

    python -m app.telegram_login

Prompts for the login code (and 2FA password, if enabled) on the console and
saves an authenticated Telethon session file for the backend to reuse.
"""

import asyncio

from telethon import TelegramClient

from app.config import TELEGRAM_API_HASH, TELEGRAM_API_ID, TELEGRAM_PHONE, TELEGRAM_SESSION_PATH


async def main() -> None:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise SystemExit(
            "Set TELEGRAM_API_ID and TELEGRAM_API_HASH in backend/.env before authenticating."
        )

    client = TelegramClient(TELEGRAM_SESSION_PATH, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start(phone=TELEGRAM_PHONE or None)

    me = await client.get_me()
    print(f"Authenticated as {me.first_name} (@{me.username or 'no-username'}).")
    print(f"Session saved to {TELEGRAM_SESSION_PATH}.session")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
