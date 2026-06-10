from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

import db
from config import OWNER_ID
from keyboards import admin_menu, links_menu, timer_menu, user_action_menu
from text import DAILY_REPORT

router = Router()


class AdminState(StatesGroup):
    waiting_link = State()
    waiting_user_id = State()


async def is_admin(user_id: int) -> bool:
    admins = await db.get_admins()
    return user_id in admins or user_id == OWNER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    await message.answer("👑 <b>Панель администратора</b>", reply_markup=admin_menu(), parse_mode="HTML")


@router.callback_query(F.data == "admin_links")
async def cb_admin_links(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await call.message.edit_text("🔗 <b>Управление ссылками</b>\n\nВыберите ссылку для редактирования:",
                                  reply_markup=links_menu(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.in_({"edit_chat", "edit_channel", "edit_reserve"}))
async def cb_edit_link(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    btn = call.data.replace("edit_", "")
    await state.set_state(AdminState.waiting_link)
    await state.update_data(edit_btn=btn)
    await call.message.answer(f"✏️ Отправьте новую ссылку для <b>{btn}</b>:", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_link)
async def process_new_link(message: Message, state: FSMContext):
    data = await state.get_data()
    btn = data.get("edit_btn")
    await db.update_link(btn, message.text.strip())
    await state.clear()
    await message.answer(f"✅ Ссылка для <b>{btn}</b> обновлена.", parse_mode="HTML")


@router.callback_query(F.data == "admin_timer")
async def cb_admin_timer(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    lifetime = await db.get_link_lifetime()
    await call.message.edit_text(f"⏱ <b>Таймер ссылок</b>\n\nТекущее значение: <b>{lifetime} мин</b>\n\nВыберите новое:",
                                  reply_markup=timer_menu(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.in_({"timer_15", "timer_30", "timer_60"}))
async def cb_set_timer(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    minutes = int(call.data.split("_")[1])
    await db.set_link_lifetime(minutes)
    await call.message.edit_text(f"✅ Таймер установлен: <b>{minutes} мин</b>", reply_markup=timer_menu(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.waiting_user_id)
    await call.message.answer("👤 Введите <b>user_id</b> пользователя:", parse_mode="HTML")
    await call.answer()


@router.message(AdminState.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("⚠️ Введите корректный числовой user_id.")
        return
    user_id = int(message.text.strip())
    await state.clear()
    await message.answer(
        f"👤 Действия над пользователем <code>{user_id}</code>:",
        reply_markup=user_action_menu(user_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ban_user:"))
async def cb_ban_user(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await db.ban_user(user_id)
    await call.answer(f"🚫 Пользователь {user_id} заблокирован.", show_alert=True)


@router.callback_query(F.data.startswith("unban_user:"))
async def cb_unban_user(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await db.unban_user(user_id)
    await call.answer(f"✅ Пользователь {user_id} разблокирован.", show_alert=True)


@router.callback_query(F.data.startswith("make_admin:"))
async def cb_make_admin(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await db.add_admin(user_id)
    await call.answer(f"👑 Пользователь {user_id} назначен админом.", show_alert=True)


@router.callback_query(F.data.startswith("remove_admin:"))
async def cb_remove_admin(call: CallbackQuery):
    if not await is_admin(call.from_user.id):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await db.remove_admin(user_id)
    await call.answer(f"❌ Пользователь {user_id} снят с должности админа.", show_alert=True)


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
    await call.message.edit_text("👑 <b>Панель администратора</b>", reply_markup=admin_menu(), parse_mode="HTML")
    await call.answer()