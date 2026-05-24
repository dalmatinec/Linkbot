import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN

from db import (
    init_db,
    add_admin
)

from handlers import router as handlers_router
from admin import router as admin_router

from config import OWNER_ID


async def main():

    init_db()

    add_admin(
        OWNER_ID,
        "owner"
    )

    bot = Bot(
        token=BOT_TOKEN,
        parse_mode="HTML"
    )

    dp = Dispatcher()

    dp.include_router(
        handlers_router
    )

    dp.include_router(
        admin_router
    )

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())