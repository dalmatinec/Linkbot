import logging
from datetime import datetime
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.dispatcher.flags import get_flag

from db import register_user, update_activity, is_banned
from config import LOG_CHANNEL_ID, OWNER_ID
import asyncio

class RegisterMiddleware(BaseMiddleware):
    """Middleware для регистрации пользователей и обновления активности"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        
        # Получаем пользователя из разных типов событий
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user:
            # Регистрируем или обновляем пользователя
            register_user(
                user_id=user.id,
                username=user.username or "",
                first_name=user.first_name or ""
            )
            
            # Проверяем бан
            if is_banned(user.id) and user.id != OWNER_ID:
                # Забаненным только отвечаем, что они забанены
                if isinstance(event, Message):
                    await event.answer("🚫 Вы забанены в этом боте.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Вы забанены", show_alert=True)
                return
            
            # Обновляем активность
            update_activity(user.id)
        
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования действий пользователей в канал"""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем команды и сообщения
        if isinstance(event, Message) and event.text:
            user = event.from_user
            if user:
                log_text = f"📝 Действие от {user.first_name} (@{user.username}) [ID: {user.id}]: {event.text[:100]}"
                await self._send_log(log_text)
        
        result = await handler(event, data)
        
        # Логируем нажатия на кнопки
        if isinstance(event, CallbackQuery):
            user = event.from_user
            if user:
                log_text = f"🔘 Нажатие от {user.first_name} (@{user.username}) [ID: {user.id}]: {event.data}"
                await self._send_log(log_text)
        
        return result
    
    async def _send_log(self, text: str):
        """Отправка лога в канал"""
        try:
            if LOG_CHANNEL_ID:
                await self.bot.send_message(LOG_CHANNEL_ID, text)
        except Exception as e:
            logging.error(f"Не удалось отправить лог: {e}")


class BanCheckMiddleware(BaseMiddleware):
    """Middleware для проверки бана перед обработкой"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user and user.id != OWNER_ID:
            if is_banned(user.id):
                # Пропускаем только команду /start
                if isinstance(event, Message) and event.text == "/start":
                    return await handler(event, data)
                # Остальное игнорируем
                return
        
        return await handler(event, data)