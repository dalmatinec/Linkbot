from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

import db
from admin import is_admin
from text import BROADCAST_CONFIRM, BROADCAST_DONE
from keyboards import confirm_menu

router = Router()


class BroadcastState(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    await state.set_state(BroadcastState.waiting_message)
    await message.answer("📨 Перешлите сообщение для рассылки:")


@router.message(BroadcastState.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    count = await db.get_total_users()
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await state.set_state(BroadcastState.waiting_confirm)
    await message.answer(BROADCAST_CONFIRM(count), reply_markup=confirm_menu(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_send")
async def cb_confirm_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    await state.clear()

    user_ids = await db.get_all_user_ids()
    success = 0
    failed = 0

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("⏳ Рассылка начата...")

    for user_id in user_ids:
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.5)

    await call.message.answer(BROADCAST_DONE(success, failed), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "cancel_send")
async def cb_cancel_send(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("❌ Рассылка отменена.")
    await call.answer()