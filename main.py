import asyncio

from datetime import datetime, timedelta

from aiogram import Bot
from aiogram import Dispatcher

from config import BOT_TOKEN

from db import init_db

from handlers import router

from admin import (
    send_daily_report,
    create_backup,
    cleanup_backups,
    send_backup_log
)


async def scheduler(bot: Bot):

    while True:

        now = datetime.now()

        target = now.replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0
        )

        if now >= target:
            target += timedelta(days=1)

        sleep_seconds = (
            target - now
        ).total_seconds()

        await asyncio.sleep(
            sleep_seconds
        )

        try:

            await send_daily_report(
                bot
            )

        except Exception as e:

            print(
                "Daily report error:",
                e
            )

        try:

            backup_path = (
                create_backup()
            )

            cleanup_backups()

            await send_backup_log(
                bot,
                backup_path
            )

        except Exception as e:

            print(
                "Backup error:",
                e
            )


async def on_startup(
    bot: Bot
):

    asyncio.create_task(
        scheduler(bot)
    )

    print(
        "Scheduler started"
    )


async def main():

    init_db()

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()

    dp.include_router(
        router
    )

    await on_startup(
        bot
    )

    print(
        "Bot started"
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Bot stopped"
        )