import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers_user import router as user_router
from handlers_group import router as group_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_scheduler(bot: Bot):
    from send_group import run_scheduled_mailing
    while True:
        try:
            await run_scheduled_mailing(bot)
        except Exception as e:
            logger.exception(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(5)


async def main():
    logger.info("Запуск бота...")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    dp.include_router(user_router)
    dp.include_router(group_router)

    scheduler_task = asyncio.create_task(run_scheduler(bot))

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запущен!")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())