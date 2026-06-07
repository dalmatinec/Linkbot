import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db import init_db

# handlers подключим позже, файл уже будет существовать
import handlers


logging.basicConfig(
    level=logging.INFO
)

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

dp = Dispatcher(storage=MemoryStorage())


async def main():

    # инициализация базы
    init_db()

    # регистрация роутеров/хендлеров
    dp.include_router(handlers.router)

    print("Bot started...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())