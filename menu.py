# menu.py

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import (
    SITE_URL,
    OPERATOR_SIS,
    OPERATOR_BRO
)


def start_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Основной чат",
                    callback_data="chat_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📺 Канал",
                    callback_data="channel_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🤍 Оператор SIS",
                    url=OPERATOR_SIS
                )
            ],
            [
                InlineKeyboardButton(
                    text="💚 Оператор BRO",
                    url=OPERATOR_BRO
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Сайт",
                    url=SITE_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔐 Резервный доступ",
                    callback_data="reserve_link"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Правила и поддержка",
                    callback_data="rules_support"
                )
            ]
        ]
    )


def support_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 Правила",
                    callback_data="show_rules"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать в поддержку",
                    callback_data="support"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_start"
                )
            ]
        ]
    )


def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📨 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Админы",
                    callback_data="admin_admins"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Баны",
                    callback_data="admin_bans"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="admin_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Логи",
                    callback_data="admin_logs"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📥 Экспорт",
                    callback_data="admin_export"
                )
            ]
        ]
    )


def admins_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить админа",
                    callback_data="add_admin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➖ Удалить админа",
                    callback_data="remove_admin"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список админов",
                    callback_data="admins_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_admin"
                )
            ]
        ]
    )


def bans_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Забанить",
                    callback_data="ban_user"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Разбанить",
                    callback_data="unban_user"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_admin"
                )
            ]
        ]
    )


def settings_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Основной чат",
                    callback_data="set_chat"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📺 Канал",
                    callback_data="set_channel"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔐 Резерв",
                    callback_data="set_reserve"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📷 Стартовое фото",
                    callback_data="set_photo"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 Стартовый текст",
                    callback_data="set_start_text"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Правила",
                    callback_data="set_rules"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏱ Таймеры",
                    callback_data="set_timers"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_admin"
                )
            ]
        ]
    )


def timers_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Таймер чата",
                    callback_data="chat_timer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📺 Таймер канала",
                    callback_data="channel_timer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔐 Таймер резерва",
                    callback_data="reserve_timer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Антиспам поддержки",
                    callback_data="support_timer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📨 Задержка рассылки",
                    callback_data="broadcast_delay"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_settings"
                )
            ]
        ]
    )


def broadcast_confirm_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data="broadcast_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="broadcast_cancel"
                )
            ]
        ]
    )


def cancel_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_action"
                )
            ]
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_start"
                )
            ]
        ]
    )


def bot_link_menu(bot_username):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Открыть бота",
                    url=f"https://t.me/{bot_username}"
                )
            ]
        ]
    )