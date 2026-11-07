"""Юзербот: раз в INTERVAL_MIN минут упоминает гостевого бота в каждой группе из CHATS.

Аккаунт должен состоять в этих группах. Первый запуск попросит номер и код из Telegram,
дальше сессия хранится в файле userbot.session.
"""
import asyncio
import logging
import random

from telethon import TelegramClient, errors

from config import (
    API_HASH,
    API_ID,
    BOT_USERNAME,
    CHATS,
    DELETE_AFTER_SEC,
    DELETE_TRIGGER,
    INTERVAL_MIN,
    PAUSE_BETWEEN_CHATS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("userbot")


async def ping(client: TelegramClient, chat) -> None:
    try:
        msg = await client.send_message(chat, f"@{BOT_USERNAME}")
        log.info("Вызвал бота в %s", chat)
        if DELETE_TRIGGER:
            await asyncio.sleep(DELETE_AFTER_SEC)
            await msg.delete()
    except errors.FloodWaitError as e:
        log.warning("FloodWait %s сек, жду", e.seconds)
        await asyncio.sleep(e.seconds + 5)
    except (
        errors.ChatWriteForbiddenError,
        errors.ChannelPrivateError,
        errors.UserBannedInChannelError,
        errors.ChatAdminRequiredError,
    ) as e:
        log.warning("Нет доступа к %s: %s", chat, type(e).__name__)
    except Exception as e:
        log.error("Ошибка в %s: %s", chat, e)


async def main() -> None:
    client = TelegramClient("userbot", API_ID, API_HASH)
    async with client:
        me = await client.get_me()
        log.info("Запущен как %s (id %s)", me.username, me.id)
        while True:
            for chat in CHATS:
                await ping(client, chat)
                await asyncio.sleep(random.uniform(*PAUSE_BETWEEN_CHATS))
            # небольшой разброс, чтобы не стучать в одну и ту же секунду
            await asyncio.sleep(INTERVAL_MIN * 60 + random.uniform(-120, 120))


if __name__ == "__main__":
    asyncio.run(main())
