"""Гостевой режим: бот не состоит в группе, его вызывают упоминанием.

Два случая:
  1. Круг рассылки: юзербот пишет «@бот», планировщик ждёт пост для этой группы.
  2. Ручной вызов в любой момент: упоминание от юзербота или владельца (OWNER_IDS),
     когда планировщик ничего не ждёт. Бот публикует следующий пост по кругу.
Посторонние упоминания игнорируются.
"""
import asyncio
import logging

from aiogram import Router
from aiogram.types import Message

from . import config
from .posts import guest_result
from .scheduler import Scheduler

log = logging.getLogger(__name__)
router = Router()


@router.guest_message()
async def on_guest(message: Message, sched: Scheduler) -> None:
    # Во входящем гостевом сообщении автор вызова - обычный from_user.
    # guest_bot_caller_user заполняется только у сообщений, которые отправил сам гостевой бот.
    caller = message.from_user or message.guest_bot_caller_user
    chat_id = message.chat.id
    log.info("Гостевой вызов в %s от %s", chat_id, caller.id if caller else None)
    if not caller:
        return
    is_ub = sched.ub.ready and caller.id == sched.ub.me.id
    if not is_ub and caller.id not in config.OWNER_IDS:
        log.info("Пропуск: вызвал посторонний %s", caller.id)
        return

    # 1. вызов из круга рассылки
    call = sched.take(chat_id) if is_ub else None
    if call is not None:
        try:
            await message.answer_guest_query(result=guest_result(call.post))
            if not call.fut.done():
                call.fut.set_result(True)
        except Exception as e:
            log.warning("Гостевой ответ в %s не ушёл: %s", chat_id, e)
            if not call.fut.done():
                call.fut.set_result(f"бот: {e}"[:200])
        return

    # 2. ручной вызов
    picked = sched.manual_post(chat_id)
    if picked is None:
        log.info("Ручной вызов в %s: нет постов", chat_id)
        return
    post, cid = picked
    try:
        if post.get("mode") == "forward":  # пересылку гостевой бот не умеет, её делает юзербот
            if not sched.ub.ready:
                raise RuntimeError("юзербот не авторизован")
            await sched.ub.forward(chat_id, post["src_id"], sched.bot_username)
        else:
            await message.answer_guest_query(result=guest_result(post))
        sched.db.log_sent(chat_id, cid, post["id"], True)
        log.info("Ручной вызов в %s: отправлен пост %s", chat_id, post["id"])
        # убираем «@бот»; чужое сообщение юзербот удалит, только если он админ группы
        if sched.db.setting("delete_trigger") and sched.ub.ready:
            asyncio.create_task(sched._delete_later(chat_id, message.message_id))
    except Exception as e:
        log.warning("Ручной вызов в %s не удался: %s", chat_id, e)
        sched.db.log_sent(chat_id, cid, post["id"], False, f"ручной вызов: {e}"[:200])
