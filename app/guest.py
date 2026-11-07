"""Гостевой режим: бот не состоит в группе, его вызывают упоминанием.

Два случая:
  1. Круг рассылки: юзербот пишет «@бот», планировщик ждёт пост для этой группы.
  2. Ручной вызов в любой момент: упоминание от юзербота (и от владельцев, если включено
     в настройках), когда планировщик ничего не ждёт. Бот публикует следующий пост по кругу.
Остальные упоминания игнорируются.
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
    owner_ok = caller.id in config.OWNER_IDS and sched.db.setting("owner_mentions")
    if not is_ub and not owner_ok:
        log.info("Пропуск: вызвал не юзербот (%s)", caller.id)
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

    # 2. ручной вызов: не чаще manual_gap минут на группу и в пределах суточного лимита
    reason = sched.manual_block(chat_id)
    if reason:
        log.info("Ручной вызов в %s пропущен: %s", chat_id, reason)
        drop_mention(sched, chat_id, message)
        return
    picked = sched.manual_post(chat_id)
    if picked is None:
        log.info("Ручной вызов в %s: нет постов", chat_id)
        return
    post, cid = picked
    try:
        if post.get("mode") == "forward":  # пересылку гостевой бот не умеет, её делает юзербот
            await sched.forward_post(chat_id, post)
        else:
            await message.answer_guest_query(result=guest_result(post))
        sched.db.log_sent(chat_id, cid, post["id"], True)
        log.info("Ручной вызов в %s: отправлен пост %s", chat_id, post["id"])
    except Exception as e:
        sched.manual_ts.pop(chat_id, None)  # не получилось - слот не тратим
        log.warning("Ручной вызов в %s не удался: %s", chat_id, e)
        sched.db.log_sent(chat_id, cid, post["id"], False, f"ручной вызов: {e}"[:200])
    drop_mention(sched, chat_id, message)


def drop_mention(sched: Scheduler, chat_id: int, message: Message) -> None:
    """Убрать «@бот» через delete_after сек. Чужое сообщение юзербот удалит, только если он админ группы."""
    if sched.db.setting("delete_trigger") and sched.ub.ready:
        asyncio.create_task(sched._delete_later(chat_id, message.message_id))
