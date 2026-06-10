from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import WEBSITE_URL, OPERATOR_ORG, OPERATOR_HIM, SUBSCRIBE_CHANNEL


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌸 Наш чат", callback_data="chat"),
            InlineKeyboardButton(text="📢 Наш канал", callback_data="channel"),
        ],
        [
            InlineKeyboardButton(text="🔄 Резерв", callback_data="reserve"),
            InlineKeyboardButton(text="🌐 Website", url=WEBSITE_URL),
        ],
        [
            InlineKeyboardButton(text="👩‍💼 Операторы", callback_data="operators"),
        ],
        [
            InlineKeyboardButton(text="📞 Тех.поддержка", callback_data="support"),
            InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
        ],
    ])


def operators_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍💼 Operator ORG", url=f"https://t.me/{OPERATOR_ORG.lstrip('@')}"),
            InlineKeyboardButton(text="👩‍🔬 Operator Him", url=f"https://t.me/{OPERATOR_HIM.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_main"),
        ],
    ])


def support_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Связаться", callback_data="contact_support"),
            InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_main"),
        ],
    ])


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Ссылки", callback_data="admin_links"),
            InlineKeyboardButton(text="⏱ Таймер", callback_data="admin_timer"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👑 Админы", callback_data="admin_admins"),
        ],
    ])


def links_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌸 Чат", callback_data="edit_chat"),
            InlineKeyboardButton(text="📢 Канал", callback_data="edit_channel"),
            InlineKeyboardButton(text="🔄 Резерв", callback_data="edit_reserve"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_admin"),
        ],
    ])


def timer_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="15 мин", callback_data="timer_15"),
            InlineKeyboardButton(text="30 мин", callback_data="timer_30"),
            InlineKeyboardButton(text="60 мин", callback_data="timer_60"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_admin"),
        ],
    ])


def subscribe_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Подписаться",
                url=f"https://t.me/{SUBSCRIBE_CHANNEL.lstrip('@')}"
            ),
            InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub"),
        ],
    ])


def confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_send"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send"),
        ],
    ])


def user_action_menu(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_user:{user_id}"),
            InlineKeyboardButton(text="✅ Разбан", callback_data=f"unban_user:{user_id}"),
        ],
        [
            InlineKeyboardButton(text="👑 Админ", callback_data=f"make_admin:{user_id}"),
            InlineKeyboardButton(text="❌ Снять", callback_data=f"remove_admin:{user_id}"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="back_admin"),
        ],
    ])


def support_action_menu(user_id: int, msg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_from_support:{user_id}"),
        ],
    ])