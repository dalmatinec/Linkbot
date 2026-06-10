from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

import db
from config import SUBSCRIBE_CHANNEL
from text import WELCOME_TEXT, RULES_TEXT, NOT_SUBSCRIBED, BANNED_MSG, LINK_MSG, LINK_WAIT, NO_LINK
from keyboards import main_menu, operators_menu, support_menu, subscribe_menu

router = Router()


class SupportState(StatesGroup):
    waiting_message = State()


BTN_NAMES = {
    "chat": "🌸 Наш чат",
    "channel": "📢 Наш канал",
    "reserve": "🔄 Резерв",
}

BTN_STAT_FIELDS = {
    "chat": "links_chat",
    "channel": "links_channel",
    "reserve": "links_reserve",
}


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(SUBSCRIBE_CHANNEL, user_id)
        return member.status not in ("left", "kicked", "banned")
    except Exception:
        return False


async def send_welcome(target: Message | CallbackQuery, bot: Bot):
    photo = FSInputFile("welcome.jpg")
    if isinstance(target, CallbackQuery):
        await target.message.answer_photo(photo, caption=WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")
    else:
        await target.answer_photo(photo, caption=WELCOME_TEXT, reply_markup=main_menu(), parse_mode="HTML")


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user

    if await db.is_banned(user.id):
        await message.answer(BANNED_MSG)
        return

    is_new = not await db.user_exists(user.id)
    await db.add_user(user.id, user.username, user.first_name)

    if not await check_subscription(bot, user.id):
        await message.answer(NOT_SUBSCRIBED, reply_markup=subscribe_menu(), parse_mode="HTML")
        return

    if is_new:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await db.increment_daily_stat(today, "new_users")

    await send_welcome(message, bot)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, call.from_user.id):
        await call.answer("❌ Вы ещё не подписались!", show_alert=True)
        return
    await call.message.delete()
    await send_welcome(call, bot)
    await call.answer()


@router.callback_query(F.data.in_({"chat", "channel", "reserve"}))
async def cb_link(call: CallbackQuery, bot: Bot):
    if await db.is_banned(call.from_user.id):
        await call.answer(BANNED_MSG, show_alert=True)
        return

    btn = call.data
    lifetime = await db.get_link_lifetime()

    active_link = await db.get_active_link(call.from_user.id, btn)
    if active_link:
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(LINK_MSG(BTN_NAMES[btn], active_link, lifetime), parse_mode="HTML")
        await call.answer()
        return

    if not await db.can_use_link(call.from_user.id, btn, lifetime):
        seconds = await db.time_until_available(call.from_user.id, btn, lifetime)
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(LINK_WAIT(seconds), parse_mode="HTML")
        await call.answer()
        return

    invite_link, expires_at = await db.create_invite_link(bot, btn)
    if not invite_link:
        await call.answer(NO_LINK, show_alert=True)
        return

    await db.record_link_usage(call.from_user.id, btn, invite_link, expires_at)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.increment_daily_stat(today, BTN_STAT_FIELDS[btn])

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(LINK_MSG(BTN_NAMES[btn], invite_link, lifetime), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "operators")
async def cb_operators(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=operators_menu())
    await call.answer()


@router.callback_query(F.data == "support")
async def cb_support(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=support_menu())
    await call.answer()


@router.callback_query(F.data == "rules")
async def cb_rules(call: CallbackQuery):
    await call.message.answer(RULES_TEXT, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=main_menu())
    await call.answer()


@router.message(Command("link"))
async def cmd_link_group(message: Message, bot: Bot):
    if message.chat.type not in ("group", "supergroup"):
        return
    me = await bot.get_me()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌸 Получить ссылку", url=f"https://t.me/{me.username}?start=link")
    ]])
    await message.reply("🔗 Ссылки доступны в личке с ботом 👇", reply_markup=kb)