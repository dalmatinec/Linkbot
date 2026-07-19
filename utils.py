# utils.py
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from config import INTERVALS

logger = logging.getLogger(__name__)


def format_post_title(post: Dict[str, Any]) -> str:
    """
    Форматирование названия поста для отображения в списке
    """
    title = post.get("title", "Без названия")
    if len(title) > 50:
        return title[:47] + "..."
    return title


def get_interval_name(minutes: int) -> str:
    """
    Получить название интервала по количеству минут
    """
    for name, value in INTERVALS.items():
        if value == minutes:
            return name
    return f"{minutes} минут"


def format_time(timestamp: int) -> str:
    """
    Форматирование Unix timestamp в читаемый вид
    """
    if not timestamp:
        return "Неизвестно"
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%d.%m.%Y %H:%M")


def chunks(lst: List, n: int):
    """
    Разбить список на части по n элементов
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def run_in_background(func, *args, **kwargs):
    """
    Запустить функцию в фоновом режиме
    """
    try:
        await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка в фоновой задаче: {e}")