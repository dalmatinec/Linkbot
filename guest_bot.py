"""Гостевой бот: по упоминанию от разрешённого аккаунта публикует рекламный пост.

Нужен свежий aiogram с поддержкой Bot API 10.0 (guest mode).
В @BotFather у бота должен быть включён Guest Mode.
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
    Message,
)

from config import ALLOWED_CALLERS, BOT_TOKEN, POSTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("guest_bot")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Номер следующего поста для каждой группы (в памяти; при перезапуске начнёт с первого)
counters: dict[int, int] = {}


def build_result(post: dict, idx: int) -> InlineQueryResultArticle:
    keyboard = None
    if post.get("buttons"):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t, url=u)] for t, u in post["buttons"]]
        )
    preview_url = post.get("preview_url")
    return InlineQueryResultArticle(
        id=str(idx),
        title=post["title"],
        input_message_content=InputTextMessageContent(
            message_text=post["text"],
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                url=preview_url,
                is_disabled=not preview_url,
                prefer_large_media=True,
            ),
        ),
        reply_markup=keyboard,
    )


@dp.guest_message()
async def on_guest_message(message: Message) -> None:
    caller = message.guest_bot_caller_user
    if caller is None or caller.id not in ALLOWED_CALLERS:
        log.info("Игнор: вызов от %s в чате %s", caller.id if caller else None, message.chat.id)
        return

    chat_id = message.chat.id
    i = counters.get(chat_id, 0)
    counters[chat_id] = i + 1
    post = POSTS[i % len(POSTS)]

    try:
        await message.answer_guest_query(result=build_result(post, i))
        log.info("Пост '%s' -> %s (%s)", post["title"], message.chat.title, chat_id)
    except Exception as e:
        log.error("Не удалось ответить в %s: %s", chat_id, e)


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
