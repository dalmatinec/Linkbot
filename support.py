from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import db
from config import ADMIN_CHAT_ID
from text import SUPPORT_PROMPT, SUPPORT_DELIVERED, SUPPORT_FORM_USER, SUPPORT_FORM_REPLY, FLOOD_BAN_MSG
from keyboards import support_action_menu

router = Router()


class SupportState(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "contact_support")
async def cb_contact_support(call: CallbackQuery, state: FSMContext):
    await state.set_state(SupportState.waiting_message)
    await call.message.answer(SUPPORT_PROMPT, parse_mode="HTML")
    await call.answer()


@router.message(SupportState.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user

    is_flood = await db.check_flood(user.id)
    if is_flood:
        await db.ban_user(user.id)
        await state.clear()
        await message.answer(FLOOD_BAN_MSG)
        return

    msg_id = await db.add_support_message(user.id, message.text)

    form = SUPPORT_FORM_USER(user.id, user.username, user.first_name, message.text)
    await bot.send_message(
        ADMIN_CHAT_ID,
        form,
        reply_markup=support_action_menu(user.id, msg_id),
        parse_mode="HTML"
    )

    await state.clear()
    await message.answer(SUPPORT_DELIVERED)


@router.callback_query(F.data.startswith("ban_from_support:"))
async def cb_ban_from_support(call: CallbackQuery):
    user_id = int(call.data.split(":")[1])
    await db.ban_user(user_id)
    await call.answer(f"🚫 Пользователь {user_id} заблокирован.", show_alert=True)


@router.message(F.reply_to_message, F.chat.id == ADMIN_CHAT_ID)
async def process_admin_reply(message: Message, bot: Bot):
    replied = message.reply_to_message
    if not replied or not replied.reply_markup:
        return

    markup = replied.reply_markup.inline_keyboard
    user_id = None
    msg_id = None

    for row in markup:
        for btn in row:
            if btn.callback_data and btn.callback_data.startswith("ban_from_support:"):
                user_id = int(btn.callback_data.split(":")[1])
            if btn.callback_data and btn.callback_data.startswith("reply_support:"):
                msg_id = int(btn.callback_data.split(":")[1])

    if not user_id:
        return

    admin_name = message.from_user.full_name
    reply_text = SUPPORT_FORM_REPLY(admin_name, message.text)
    await bot.send_message(user_id, reply_text, parse_mode="HTML")

    if msg_id:
        await db.mark_support_replied(msg_id, message.message_id)

    await message.reply("✅ Ответ отправлен пользователю.")