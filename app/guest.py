"""Гостевой режим: бот не состоит в группе, его вызывает наш юзербот упоминанием."""
import logging

from aiogram import Router
from aiogram.types import Message

from .posts import guest_result
from .scheduler import Scheduler

log = logging.getLogger(__name__)
router = Router()


@router.guest_message()
async def on_guest(message: Message, sched: Scheduler) -> None:
    caller = message.guest_bot_caller_user
    # отвечаем только нашему юзерботу и только когда планировщик ждёт пост для этой группы
    if not caller or not sched.ub.ready or caller.id != sched.ub.me.id:
        return
    call = sched.take(message.chat.id)
    if call is None:
        return
    try:
        await message.answer_guest_query(result=guest_result(call.post))
        if not call.fut.done():
            call.fut.set_result(True)
    except Exception as e:
        log.warning("Гостевой ответ в %s не ушёл: %s", message.chat.id, e)
        if not call.fut.done():
            call.fut.set_result(f"бот: {e}"[:200])
