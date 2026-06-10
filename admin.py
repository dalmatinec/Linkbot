from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

import db
from config import OWNER_ID
from keyboards import admin_menu, links_menu, timer_menu, admin_admins_menu
from text import DAILY_REPORT

router = Router()


class AdminState(StatesGroup):
    waiting_link = State()
    waiting_add_admin = State()
    waiting_del_admin = State()


async def is_admin(user_id: int) -> bool:
    admins = await db.get_admins()
    return user_id in admins or user_id == OWNER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    await message.answer("👑 <b>Панель администратора</b>", reply_markup=admin_menu(), parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer(
        "👑 <b>Команды админа:</b>\n"
        "/admin — панель управления\n"
        "/broadcast — рассылка\n"
        "/help — помощь",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_links")
async def cb_admin_links(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await call.message.edit_text(
        "🔗 <b>Управление ссылками</b>\n\nВыберите чат для редактирования:",
        reply_markup=links_menu(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.in_({"edit_chat", "edit_channel", "edit_reserve"}))
async def cb_edit_link(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    btn = call.data.replace("edit_", "")
    await state.set_state(AdminState.waiting_link)
    await state.update_data(edit_btn=btn)
    await call.message.answer(f"✏️ Отправьте ID чата для <b>{btn}</b>:\n\nПример: <code>-1001234567890</code>", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_link)
async def process_new_link(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.lstrip("-").isdigit():
        await message.answer("⚠️ Введите корректный числовой ID чата. Пример: <code>-1001234567890</code>", parse_mode="HTML")
        return
    data = await state.get_data()
    btn = data.get("edit_btn")
    await db.update_link(btn, int(text))
    await state.clear()
    await message.answer(f"✅ ID чата для <b>{btn}</b> обновлён: <code>{text}</code>", parse_mode="HTML")


@router.callback_query(F.data == "admin_timer")
async def cb_admin_timer(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    lifetime = await db.get_link_lifetime()
    await call.message.edit_text(
        f"⏱ <b>Таймер ссылок</b>\n\nТекущее значение: <b>{lifetime} мин</b>\n\nВыберите новое:",
        reply_markup=timer_menu(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.in_({"timer_15", "timer_30", "timer_60"}))
async def cb_set_timer(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    minutes = int(call.data.split("_")[1])
    await db.set_link_lifetime(minutes)
    await call.message.edit_text(
        f"✅ Таймер установлен: <b>{minutes} мин</b>",
        reply_markup=timer_menu(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = await db.get_daily_stats(today)
    total = await db.get_total_users()
    banned = await db.get_banned_count()
    text = DAILY_REPORT(stats) + f"\n\n👥 Всего пользователей: <b>{total}</b>\n🚫 Забанено: <b>{banned}</b>"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin_admins")
async def cb_admin_admins(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await call.message.edit_text(
        "👑 <b>Управление админами</b>",
        reply_markup=admin_admins_menu(), parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "add_admin")
async def cb_add_admin(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.waiting_add_admin)
    await call.message.answer("➕ Введите <b>user_id</b> нового админа:", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_add_admin)
async def process_add_admin(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Введите корректный числовой user_id.")
        return
    user_id = int(message.text.strip())
    await db.add_admin(user_id)
    await state.clear()
    await message.answer(f"✅ Пользователь <code>{user_id}</code> назначен админом.", parse_mode="HTML")


@router.callback_query(F.data == "del_admin")
async def cb_del_admin(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.waiting_del_admin)
    await call.message.answer("➖ Введите <b>user_id</b> админа для удаления:", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_del_admin)
async def process_del_admin(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Введите корректный числовой user_id.")
        return
    user_id = int(message.text.strip())
    await db.remove_admin(user_id)
    await state.clear()
    await message.answer(f"❌ Пользователь <code>{user_id}</code> снят с должности админа.", parse_mode="HTML")


@router.callback_query(F.data == "list_admins")
async def cb_list_admins(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    admins = await db.get_admins()
    if not admins:
        await call.answer("Список админов пуст.", show_alert=True)
        return
    lines = "\n".join(f"• <code>{uid}</code>" for uid in admins)
    await call.message.answer(f"👑 <b>Список админов:</b>\n\n{lines}", parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "back_admin")
async def cb_back_admin(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await call.message.edit_text(
        "👑 <b>Панель администратора</b>",
        reply_markup=admin_menu(), parse_mode="HTML"
    )
    await call.answer()