# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any
from config import INTERVALS


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для стартового сообщения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="stats")
    return builder.as_markup()


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура админа в группе"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список рассылок", callback_data="list_posts")
    builder.button(text="➕ Создать рассылку", callback_data="create_post")
    builder.adjust(1)
    return builder.as_markup()


def get_posts_list_keyboard(posts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура со списком рассылок"""
    builder = InlineKeyboardBuilder()

    for post in posts:
        post_id = post["id"]
        title = post["title"]
        builder.button(text=f"{post_id}. {title}", callback_data=f"post_{post_id}")

    builder.adjust(1)
    return builder.as_markup()


def get_post_detail_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для детального просмотра рассылки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить группу", callback_data=f"add_group_{post_id}")
    builder.button(text="➖ Удалить группу", callback_data=f"remove_group_{post_id}")
    builder.button(text="🕒 Изменить интервал", callback_data=f"change_interval_{post_id}")
    builder.button(text="🗑 Удалить рассылку", callback_data=f"delete_post_{post_id}")
    builder.button(text="◀ Назад", callback_data="back_to_list")
    builder.adjust(1)
    return builder.as_markup()


def get_groups_list_keyboard(groups: List[Dict[str, Any]], post_id: int, action: str) -> InlineKeyboardMarkup:
    """Клавиатура со списком групп для добавления/удаления/выбора"""
    builder = InlineKeyboardBuilder()

    for group in groups:
        chat_id = group["chat_id"]
        title = group["title"]
        is_selected = group.get("is_selected", False)

        if is_selected:
            text = f"☑️ {title}"
        else:
            text = f"⬜ {title}"

        builder.button(text=text, callback_data=f"{action}_{post_id}_{chat_id}")

    # Разные callback_data для разных действий
    if action == "select":
        builder.button(text="✅ Готово", callback_data=f"done_create_groups_{post_id}")
    else:
        builder.button(text="✅ Готово", callback_data=f"done_edit_groups_{post_id}")
    
    builder.button(text="◀ Назад", callback_data=f"post_{post_id}" if post_id != 0 else "back_to_list")
    builder.adjust(1)
    return builder.as_markup()


def get_interval_keyboard(post_id: int, action: str = "edit") -> InlineKeyboardMarkup:
    """Клавиатура для выбора интервала"""
    builder = InlineKeyboardBuilder()

    for interval_name, interval_minutes in INTERVALS.items():
        builder.button(
            text=interval_name,
            callback_data=f"{action}_interval_{post_id}_{interval_minutes}"
        )

    builder.button(text="◀ Назад", callback_data=f"post_{post_id}" if post_id != 0 else "back_to_list")
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_keyboard(action: str, post_id: int, data: str = "") -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действия"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_{action}_{post_id}_{data}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_{action}_{post_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=callback_data)
    return builder.as_markup()


def get_back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀ Назад", callback_data=callback_data)
    return builder.as_markup()


def confirmation_keyboard(mailing_type: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки в ЛС"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm_mailing_{mailing_type}")
    builder.button(text="❌ Отмена", callback_data="cancel_mailing")
    builder.adjust(2)
    return builder.as_markup()