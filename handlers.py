import asyncio
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from db import (
    register_user, update_activity, get_setting, can_get_link,
    update_link_usage, add_admin_log
)
from keyboards import get_link_keyboard, get_operators_keyboard
from config import OWNER_ID, LOG_CHANNEL_ID

router = Router()

# ==================== КОМАНДА START ====================
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start - регистрация пользователя"""
    user = message.from_user
    
    # Регистрируем пользователя (уже в middleware, но на всякий случай)
    register_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    
    # Приветственное сообщение
    from menu import get_main_menu
    main_menu = await get_main_menu()
    
    await message.answer(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я бот для получения доступа к ресурсам.\n\n"
        f"Используй кнопки меню для навигации:",
        reply_markup=main_menu
    )
    
    # Лог в канал
    if LOG_CHANNEL_ID:
        try:
            await message.bot.send_message(
                LOG_CHANNEL_ID,
                f"🆕 Новый пользователь: {user.first_name} (@{user.username}) [ID: {user.id}]"
            )
        except:
            pass

# ==================== КОМАНДА LINK ====================
@router.message(Command("link"))
async def cmd_link(message: Message):
    """Обработчик команды /link - получить ссылку на бота"""
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    await message.answer(
        "🔗 <b>Для получения ссылки откройте бота</b>\n\n"
        f"Нажмите на кнопку ниже, чтобы открыть бота:",
        parse_mode="HTML",
        reply_markup=get_link_keyboard("site", f"https://t.me/{bot_username}")
    )

# ==================== ОСНОВНОЙ ЧАТ ====================
@router.message(F.text == "💬 Основной чат")
async def get_chat_link(message: Message):
    """Выдача ссылки на основной чат"""
    user_id = message.from_user.id
    
    # Проверяем кд
    can, seconds = can_get_link(user_id, 'chat')
    
    if not can:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        await message.answer(
            f"⏳ Вы уже получали ссылку на чат!\n\n"
            f"Следующую ссылку можно получить через {hours}ч {minutes}мин"
        )
        return
    
    # Получаем ссылку из настроек
    chat_link = get_setting('chat_link')
    
    if not chat_link:
        await message.answer("❌ Ссылка на чат еще не настроена администратором")
        return
    
    # Обновляем статистику и логируем
    update_link_usage(user_id, 'chat')
    
    await message.answer(
        "🔗 <b>Вот ссылка на основной чат:</b>\n\n"
        f"{chat_link}\n\n"
        "⚠️ Ссылка действительна для вас одного!\n"
        "Не передавайте её другим.",
        parse_mode="HTML",
        reply_markup=get_link_keyboard("chat", chat_link)
    )
    
    # Лог в канал
    if LOG_CHANNEL_ID:
        user = message.from_user
        await message.bot.send_message(
            LOG_CHANNEL_ID,
            f"🔗 Пользователь {user.first_name} (@{user.username}) [ID: {user.id}] получил ссылку на ЧАТ"
        )

# ==================== КАНАЛ ====================
@router.message(F.text == "📺 Канал")
async def get_channel_link(message: Message):
    """Выдача ссылки на канал"""
    user_id = message.from_user.id
    
    # Проверяем кд
    can, seconds = can_get_link(user_id, 'channel')
    
    if not can:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        await message.answer(
            f"⏳ Вы уже получали ссылку на канал!\n\n"
            f"Следующую ссылку можно получить через {hours}ч {minutes}мин"
        )
        return
    
    # Получаем ссылку из настроек
    channel_link = get_setting('channel_link')
    
    if not channel_link:
        await message.answer("❌ Ссылка на канал еще не настроена администратором")
        return
    
    # Обновляем статистику и логируем
    update_link_usage(user_id, 'channel')
    
    await message.answer(
        "🔗 <b>Вот ссылка на канал:</b>\n\n"
        f"{channel_link}\n\n"
        "⚠️ Ссылка действительна для вас одного!\n"
        "Не передавайте её другим.",
        parse_mode="HTML",
        reply_markup=get_link_keyboard("channel", channel_link)
    )
    
    # Лог в канал
    if LOG_CHANNEL_ID:
        user = message.from_user
        await message.bot.send_message(
            LOG_CHANNEL_ID,
            f"🔗 Пользователь {user.first_name} (@{user.username}) [ID: {user.id}] получил ссылку на КАНАЛ"
        )

# ==================== ОПЕРАТОР ====================
@router.message(F.text == "🤍 Оператор")
async def get_operator(message: Message):
    """Показать кнопки операторов"""
    # Получаем ссылки из настроек
    operator1_name = get_setting('operator1_name')
    operator1_link = get_setting('operator1_link')
    operator2_name = get_setting('operator2_name')
    operator2_link = get_setting('operator2_link')
    
    # Проверяем, есть ли хоть один оператор
    if not operator1_link and not operator2_link:
        await message.answer("❌ Операторы еще не настроены администратором")
        return
    
    keyboard = get_operators_keyboard()
    
    if keyboard is None:
        await message.answer("❌ Нет доступных операторов")
        return
    
    await message.answer(
        "👨‍💻 <b>Выберите оператора для связи:</b>\n\n"
        "Нажмите на кнопку ниже, чтобы написать оператору:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    # Лог
    user = message.from_user
    if LOG_CHANNEL_ID:
        await message.bot.send_message(
            LOG_CHANNEL_ID,
            f"👤 Пользователь {user.first_name} (@{user.username}) [ID: {user.id}] запросил оператора"
        )

# ==================== САЙТ ====================
@router.message(F.text == "🌐 Сайт")
async def get_site_link(message: Message):
    """Выдача ссылки на сайт"""
    site_link = get_setting('site_link')
    
    if not site_link:
        await message.answer("❌ Ссылка на сайт еще не настроена администратором")
        return
    
    await message.answer(
        "🌐 <b>Наш сайт:</b>\n\n"
        f"{site_link}",
        parse_mode="HTML",
        reply_markup=get_link_keyboard("site", site_link)
    )

# ==================== РЕЗЕРВНЫЙ ДОСТУП ====================
@router.message(F.text == "🔐 Резервный доступ")
async def get_reserve_link(message: Message):
    """Выдача резервной ссылки"""
    user_id = message.from_user.id
    
    # Проверяем кд (24 часа обычно)
    can, seconds = can_get_link(user_id, 'reserve')
    
    if not can:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        await message.answer(
            f"⏳ Вы уже получали резервную ссылку!\n\n"
            f"Следующую ссылку можно получить через {hours}ч {minutes}мин"
        )
        return
    
    # Получаем ссылку из настроек
    reserve_link = get_setting('reserve_link')
    
    if not reserve_link:
        await message.answer("❌ Резервная ссылка еще не настроена администратором")
        return
    
    # Обновляем статистику и логируем
    update_link_usage(user_id, 'reserve')
    
    await message.answer(
        "🔐 <b>Резервный доступ:</b>\n\n"
        f"{reserve_link}\n\n"
        "⚠️ Используйте только если основные ссылки не работают!\n"
        "Ссылка действительна 24 часа.",
        parse_mode="HTML",
        reply_markup=get_link_keyboard("reserve", reserve_link)
    )
    
    # Лог в канал
    if LOG_CHANNEL_ID:
        user = message.from_user
        await message.bot.send_message(
            LOG_CHANNEL_ID,
            f"🔗 Пользователь {user.first_name} (@{user.username}) [ID: {user.id}] получил РЕЗЕРВНУЮ ссылку"
        )

# ==================== ИНФОРМАЦИЯ ====================
@router.message(F.text == "ℹ️ Информация")
async def get_info(message: Message):
    """Показать информационное сообщение"""
    info_text = get_setting('info_text')
    
    if not info_text:
        info_text = "ℹ️ <b>Информация о боте</b>\n\n"
        info_text += "Этот бот предоставляет доступ к ресурсам.\n"
        info_text += "Используйте кнопки меню для навигации."
    
    await message.answer(
        info_text,
        parse_mode="HTML"
    )

# ==================== КНОПКА ЗАКРЫТЬ ====================
@router.callback_query(F.data == "close")
async def close_callback(callback: CallbackQuery):
    """Закрыть инлайн кнопку"""
    await callback.message.delete()
    await callback.answer()

# ==================== ОБРАБОТКА ВСЕХ ОСТАЛЬНЫХ СООБЩЕНИЙ ====================
@router.message()
async def handle_unknown(message: Message):
    """Обработка неизвестных сообщений"""
    # Игнорируем, если команда
    if message.text and message.text.startswith('/'):
        return
    
    await message.answer(
        "❓ Я не понимаю эту команду.\n\n"
        "Используйте кнопки меню для навигации."
    )