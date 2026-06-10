import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta, time as dtime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import db
from config import BOT_TOKEN, ADMIN_CHAT_ID, DAILY_REPORT_TIME
from text import DAILY_REPORT
import handlers
import admin
import support
import send


async def daily_report(bot: Bot):
    report_time = dtime.fromisoformat(DAILY_REPORT_TIME)
    while True:
        now = datetime.now(timezone.utc)
        target = datetime.combine(now.date(), report_time, tzinfo=timezone.utc)
        if now >= target:
            target = datetime.combine(
                now.date() + timedelta(days=1), report_time, tzinfo=timezone.utc
            )
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = await db.get_daily_stats(today)
        total = await db.get_total_users()
        banned = await db.get_banned_count()
        text = DAILY_REPORT(stats) + f"\n\n👥 Всего пользователей: <b>{total}</b>\n🚫 Забанено: <b>{banned}</b>"
        await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML")


async def cleanup_flood():
    while True:
        await asyncio.sleep(3600)
        async with __import__("aiosqlite").connect(db.DB_PATH) as conn:
            await conn.execute(
                "DELETE FROM flood_control WHERE message_ts < ?",
                (time.time() - 60,)
            )
            await conn.commit()


async def main():
    logging.basicConfig(level=logging.INFO)

    await db.init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    dp.include_router(handlers.router)
    dp.include_router(admin.router)
    dp.include_router(support.router)
    dp.include_router(send.router)

    asyncio.create_task(daily_report(bot))
    asyncio.create_task(cleanup_flood())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())