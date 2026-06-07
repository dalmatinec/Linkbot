from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

import config

from menu import (
    main_menu,
    back_menu,
    open_bot_keyboard
)

from db import (
    add_user,
    update_activity,
    add_link_log,
    is_admin
)


router = Router()


# =========================
# UTILS
# =========================

def log_and_update(user_id: int, category: str):
    update_activity(user_id)
    add_link_log(user_id, category)


# =========================
# START
# =========================
@router.message(F.text == "/start")
async def start(message: Message):

    user = message.from_user

    add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    update_activity(user.id)

    text = (
        "👋 Привет!\n\n"
        "Выбери нужный раздел ниже."
    )

    await message.answer(
        text,
        reply_markup=main_menu()
    )


# =========================
# LINK COMMAND
# =========================
@router.message(F.text == "/link")
async def link(message: Message, bot: Bot):

    me = await bot.get_me()

    await message.answer(
        "Для получения ссылки откройте бота.",
        reply_markup=open_bot_keyboard(me.username)
    )


# =========================
# CALLBACK ROUTER
# =========================
@router.callback_query()
async def callbacks(call: CallbackQuery):

    user_id = call.from_user.id
    data = call.data

    update_activity(user_id)

    # ---------------- MAIN MENU ----------------
    if data == "main_menu":
        await call.message.edit_text(
            "👋 Главное меню",
            reply_markup=main_menu()
        )
        return

    # ---------------- CHAT ----------------
    if data == "chat":
        log_and_update(user_id, "chat")

        await call.message.edit_text(
            "💬 Основной чат",
            reply_markup=back_menu()
        )
        return

    # ---------------- CHANNEL ----------------
    if data == "channel":
        log_and_update(user_id, "channel")

        await call.message.edit_text(
            "📺 Канал",
            reply_markup=back_menu()
        )
        return

    # ---------------- OPERATORS ----------------
    if data == "operator1":

        log_and_update(user_id, "reserve")

        await call.message.edit_text(
            "🤍 Оператор SIS\n\n"
            "@operator_sis\n\n"
            "Сохрани вечный юзер.",
            reply_markup=back_menu()
        )
        return

    if data == "operator2":

        log_and_update(user_id, "reserve")

        await call.message.edit_text(
            "💚 Оператор BRO\n\n"
            "@operator_bro\n\n"
            "Сохрани вечный юзер.",
            reply_markup=back_menu()
        )
        return

    # ---------------- SITE ----------------
    if data == "site":

        await call.message.edit_text(
            "🌐 Сайт\n\nСкоро будет доступен.",
            reply_markup=back_menu()
        )
        return

    # ---------------- RESERVE ----------------
    if data == "reserve":

        log_and_update(user_id, "reserve")

        await call.message.edit_text(
            "🔐 Резервный доступ\n\nСкоро будет доступен.",
            reply_markup=back_menu()
        )
        return

    # ---------------- INFO ----------------
    if data == "info":

        await call.message.edit_text(
            "ℹ️ Информация\n\n"
            "Это навигационный бот с разделами и статистикой.",
            reply_markup=back_menu()
        )
        return

    # ---------------- ADMIN ----------------
    if data.startswith("admin_"):

        if not is_admin(user_id):
            await call.answer("Нет доступа", show_alert=True)
            return

        await call.message.edit_text(
            "⚙️ Админ панель",
            reply_markup=back_menu()
        )
        return

    await call.answer()