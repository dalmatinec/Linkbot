import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

from db import (
    is_admin, get_all_admins, add_admin, remove_admin, 
    get_user, ban_user, unban_user, get_user_stats,
    get_setting, set_setting, get_all_settings,
    add_admin_log, get_all_users_for_export, get_link_logs,
    get_admin_logs, get_broadcasts
)
from models import BroadcastStates, EditSettingStates
from keyboards import (
    get_admin_keyboard, get_back_keyboard, get_confirm_keyboard,
    get_admin_list_keyboard, get_users_list_keyboard, get_settings_keyboard
)
from config import OWNER_ID, LOG_CHANNEL_ID

router = Router()

# ==================== ПРОВЕРКА АДМИНА ====================
async def check_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    if user_id == OWNER_ID:
        return True
    return is_admin(user_id)

# ==================== ВХОД В АДМИНКУ ====================
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    """Вход в админ-панель"""
    if not await check_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👋 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    add_admin_log(message.from_user.id, "enter_admin")

# ==================== ВЫХОД ИЗ АДМИНКИ ====================
@router.message(F.text == "🔙 Выйти из админки")
async def exit_admin(message: Message):
    """Выход из админ-панели"""
    from menu import get_main_menu
    
    await message.answer(
        "👋 Вы вышли из админ-панели",
        reply_markup=await get_main_menu()
    )

# ==================== СТАТИСТИКА ====================
@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    """Показать статистику"""
    if not await check_admin(message.from_user.id):
        return
    
    stats = get_user_stats()
    
    text = f"""📊 <b>СТАТИСТИКА БОТА</b>

👥 <b>Пользователи:</b>
• Всего: {stats['total']}
• Сегодня: {stats['today']}
• За неделю: {stats['week']}
• За месяц: {stats['month']}
• Активные сегодня: {stats['active_today']}
• Забанены: {stats['banned']}

🔗 <b>Ссылки (всего выдано):</b>
• Основной чат: {stats['chat_links']}
• Канал: {stats['channel_links']}
• Резервный доступ: {stats['reserve_links']}
• <b>Всего: {stats['total_links']}</b>
"""
    
    await message.answer(text, parse_mode="HTML")

# ==================== РАССЫЛКА (FSM) ====================
@router.message(F.text == "📨 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    """Начать рассылку"""
    if not await check_admin(message.from_user.id):
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        "📨 <b>Создание рассылки</b>\n\n"
        "Отправьте сообщение, которое хотите разослать.\n"
        "Это может быть текст, фото, видео, документ или любое другое сообщение.\n\n"
        "❗ Сообщение будет переслано КАК ЕСТЬ (с подписью 'Переслано от ...')\n\n"
        "Для отмены отправьте /cancel",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@router.message(StateFilter(BroadcastStates.waiting_for_message), F.text == "🔙 Назад")
async def cancel_broadcast(message: Message, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await message.answer(
        "❌ Рассылка отменена",
        reply_markup=get_admin_keyboard()
    )

@router.message(StateFilter(BroadcastStates.waiting_for_message), F.text == "/cancel")
async def force_cancel_broadcast(message: Message, state: FSMContext):
    """Принудительная отмена"""
    await state.clear()
    await message.answer(
        "❌ Рассылка отменена",
        reply_markup=get_admin_keyboard()
    )

@router.message(StateFilter(BroadcastStates.waiting_for_message))
async def get_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Получить сообщение для рассылки"""
    # Сохраняем сообщение (его можно будет переслать)
    await state.update_data(broadcast_message=message)
    await state.set_state(BroadcastStates.confirm)
    
    # Показываем превью
    await message.answer(
        "📨 <b>Подтверждение рассылки</b>\n\n"
        "Вот как будет выглядеть сообщение для пользователей:\n"
        "⚠️ Оно будет отправлено КАК ПЕРЕСЛАННОЕ (от вашего имени)\n\n"
        "Подтвердите отправку:",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard()
    )
    
    # Пересылаем сообщение для превью
    await message.forward(chat_id=message.chat.id)

@router.callback_query(StateFilter(BroadcastStates.confirm), F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка рассылки"""
    data = await state.get_data()
    broadcast_msg = data.get('broadcast_message')
    
    if not broadcast_msg:
        await callback.answer("Ошибка: сообщение не найдено")
        await state.clear()
        return
    
    await callback.answer("⏳ Начинаю рассылку...")
    
    # Получаем всех пользователей
    from db import get_all_users
    
    users = get_all_users()
    success = 0
    failed = 0
    
    for user in users:
        if user['banned']:
            continue
        
        try:
            # Пересылаем сообщение (как репост)
            await bot.forward_message(
                chat_id=user['user_id'],
                from_chat_id=broadcast_msg.chat.id,
                message_id=broadcast_msg.message_id
            )
            success += 1
            await asyncio.sleep(0.05)  # Защита от флуда
        except Exception as e:
            failed += 1
    
    # Логируем рассылку
    from db import add_broadcast_log
    broadcast_id = add_broadcast_log(callback.from_user.id, success, failed)
    
    # Результат
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"🚫 Пропущено (бан): {len([u for u in users if u['banned']])}",
        parse_mode="HTML"
    )
    
    # Лог в канал
    if LOG_CHANNEL_ID:
        await bot.send_message(
            LOG_CHANNEL_ID,
            f"📨 Рассылка #{broadcast_id}\n"
            f"Отправил: {callback.from_user.id}\n"
            f"Успешно: {success}\n"
            f"Ошибок: {failed}"
        )
    
    await state.clear()
    
    # Возвращаем в админку
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(StateFilter(BroadcastStates.confirm), F.data == "broadcast_cancel")
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

# ==================== АДМИНЫ ====================
@router.message(F.text == "👤 Админы")
async def manage_admins(message: Message):
    """Управление админами"""
    if not await check_admin(message.from_user.id):
        return
    
    admins = get_all_admins()
    text = "👥 <b>Список администраторов</b>\n\n"
    
    for admin in admins:
        text += f"• {admin['username'] or 'ID:' + str(admin['user_id'])} — {admin['role']}\n"
    
    text += "\n➕ Чтобы добавить админа, отправьте /add_admin @username\n"
    text += "➖ Чтобы удалить, нажмите кнопку ниже"
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_list_keyboard(admins)
    )

@router.message(Command("add_admin"))
async def add_admin_command(message: Message):
    """Добавить админа через команду"""
    if not await check_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /add_admin @username")
        return
    
    username = args[1].lstrip('@')
    
    # Поиск пользователя по username (нужно получить ID)
    try:
        from aiogram import Bot
        from config import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)
        chat = await bot.get_chat(f"@{username}")
        user_id = chat.id
        await bot.close()
        
        add_admin(user_id, username, 'admin', message.from_user.id)
        await message.answer(f"✅ Админ @{username} добавлен")
        
        # Лог
        add_admin_log(message.from_user.id, "add_admin", username)
        
    except Exception as e:
        await message.answer(f"❌ Не удалось найти пользователя @{username}")

@router.callback_query(F.data.startswith("del_admin_"))
async def delete_admin_callback(callback: CallbackQuery):
    """Удалить админа"""
    if not await check_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    # Нельзя удалить владельца
    if user_id == OWNER_ID:
        await callback.answer("❌ Нельзя удалить владельца бота")
        return
    
    user = get_user(user_id)
    username = user.get('username', str(user_id)) if user else str(user_id)
    
    remove_admin(user_id, callback.from_user.id)
    
    await callback.answer(f"✅ Админ удален")
    await callback.message.edit_text(f"✅ Админ {username} удален")
    
    # Показываем обновленный список
    admins = get_all_admins()
    text = "👥 <b>Список администраторов</b>\n\n"
    for admin in admins:
        text += f"• {admin['username'] or 'ID:' + str(admin['user_id'])} — {admin['role']}\n"
    
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_list_keyboard(admins)
    )

# ==================== БАНЫ ====================
@router.message(F.text == "🚫 Баны")
async def ban_menu(message: Message):
    """Меню банов"""
    if not await check_admin(message.from_user.id):
        return
    
    from db import get_all_users
    
    users = get_all_users()
    
    await message.answer(
        "🚫 <b>Управление банами</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_users_list_keyboard(users[:50], "ban")  # Первые 50
    )

@router.callback_query(F.data.startswith("ban_"))
async def ban_user_callback(callback: CallbackQuery):
    """Забанить пользователя"""
    if not await check_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[1])
    
    if user_id == OWNER_ID:
        await callback.answer("❌ Нельзя забанить владельца")
        return
    
    ban_user(user_id, callback.from_user.id)
    
    await callback.answer("✅ Пользователь забанен")
    
    # Обновляем список
    from db import get_all_users
    users = get_all_users()
    await callback.message.edit_reply_markup(
        reply_markup=get_users_list_keyboard(users[:50], "ban")
    )

@router.callback_query(F.data.startswith("unban_"))
async def unban_user_callback(callback: CallbackQuery):
    """Разбанить пользователя"""
    if not await check_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[1])
    
    unban_user(user_id, callback.from_user.id)
    
    await callback.answer("✅ Пользователь разбанен")
    
    # Обновляем список
    from db import get_all_users
    users = get_all_users()
    await callback.message.edit_reply_markup(
        reply_markup=get_users_list_keyboard(users[:50], "unban")
    )

# ==================== НАСТРОЙКИ ====================
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    """Меню настроек"""
    if not await check_admin(message.from_user.id):
        return
    
    settings = get_all_settings()
    
    text = "⚙️ <b>Настройки бота</b>\n\n"
    for key, value in settings.items():
        display = value[:30] + "..." if len(value) > 30 else value
        text += f"• <b>{key}</b>: {display or '(пусто)'}\n"
    
    text += "\nНажмите на параметр чтобы изменить"
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_settings_keyboard(settings)
    )

@router.callback_query(F.data.startswith("edit_setting_"))
async def edit_setting(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование настройки"""
    if not await check_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    setting_key = callback.data.replace("edit_setting_", "")
    current_value = get_setting(setting_key)
    
    await state.update_data(editing_setting=setting_key)
    await state.set_state(EditSettingStates.waiting_for_value)
    
    await callback.message.answer(
        f"✏️ <b>Редактирование: {setting_key}</b>\n\n"
        f"Текущее значение:\n<code>{current_value or '(пусто)'}</code>\n\n"
        f"Отправьте новое значение.\n"
        f"Для отмены отправьте /cancel",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(StateFilter(EditSettingStates.waiting_for_value))
async def save_setting(message: Message, state: FSMContext):
    """Сохранить настройку"""
    if not await check_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    setting_key = data.get('editing_setting')
    
    new_value = message.text
    set_setting(setting_key, new_value, message.from_user.id)
    
    await state.clear()
    await message.answer(
        f"✅ Настройка <b>{setting_key}</b> обновлена!\n\n"
        f"Новое значение:\n<code>{new_value[:100]}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )

@router.message(StateFilter(EditSettingStates.waiting_for_value), F.text == "/cancel")
async def cancel_edit(message: Message, state: FSMContext):
    """Отмена редактирования"""
    await state.clear()
    await message.answer(
        "❌ Редактирование отменено",
        reply_markup=get_admin_keyboard()
    )

# ==================== ЛОГИ ====================
@router.message(F.text == "📋 Логи")
async def show_logs(message: Message):
    """Показать логи"""
    if not await check_admin(message.from_user.id):
        return
    
    # Получаем последние логи
    from db import get_recent_logs
    
    logs = get_recent_logs(30)  # Последние 30 логов
    
    if not logs:
        await message.answer("📋 Логов пока нет")
        return
    
    text = "📋 <b>Последние действия</b>\n\n"
    for log in logs:
        text += f"• {log['created_at'][:16]} | {log['action']}"
        if log['target']:
            text += f" | {log['target'][:30]}"
        text += "\n"
    
    # Если текст слишком длинный, режем
    if len(text) > 4000:
        text = text[:4000] + "..."
    
    await message.answer(text, parse_mode="HTML")

# ==================== НАЗАД В АДМИНКЕ ====================
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в меню админки"""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()