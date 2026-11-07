"""Запуск: python -m app (бот + юзербот + планировщик), вход юзербота: python -m app login."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import events

from . import admin, config, guest
from .db import DB
from .scheduler import Scheduler
from .userbot import Userbot, login

log = logging.getLogger("linkbot")


async def main() -> None:
    if not config.BOT_TOKEN or not config.OWNER_IDS:
        sys.exit("Заполните BOT_TOKEN и OWNER_IDS в .env")
    db = DB(config.DB_PATH)
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    me = await bot.get_me()
    if not getattr(me, "supports_guest_queries", True):
        log.warning("У бота не включён Guest Mode: @BotFather → Bot Settings → Guest Mode")

    ub = Userbot()
    ub_ok = await ub.start()
    sched = Scheduler(db, bot, ub, me.username)

    dp = Dispatcher(storage=MemoryStorage())
    dp["db"], dp["sched"], dp["ub"] = db, sched, ub
    dp.include_router(guest.router)
    dp.include_router(admin.router)

    if not ub_ok:
        await sched.notify("⚠️ Юзербот не авторизован. На сервере: <code>python -m app login</code>, потом перезапуск.")
    else:
        @ub.client.on(events.ChatAction)
        async def on_join(e) -> None:  # юзербот зашёл в группу - сразу обновляем список
            if (e.user_joined or e.user_added) and e.user_id == ub.me.id:
                try:
                    await sched.sync_groups()
                except Exception:
                    log.exception("Ошибка обновления групп")

    asyncio.create_task(sched.loop())
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Бот @%s запущен", me.username)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await ub.client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("telethon").setLevel(logging.WARNING)
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        asyncio.run(login())
    else:
        asyncio.run(main())
