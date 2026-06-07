import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from db import init_db
from middlewares import RegisterMiddleware, LoggingMiddleware, BanCheckMiddleware
from handlers import router as handlers_router
from admin import router as admin_router
from scheduler import daily_report

logging.basicConfig(level=logging.INFO)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="link", description="Получить ссылку на бота")
    ]
    await bot.set_my_commands(commands)

async def main():
    init_db()
    
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    dp.update.middleware(RegisterMiddleware())
    dp.update.middleware(BanCheckMiddleware())
    dp.update.middleware(LoggingMiddleware(bot))
    
    dp.include_router(handlers_router)
    dp.include_router(admin_router)
    
    await set_commands(bot)
    asyncio.create_task(daily_report(bot))
    
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())