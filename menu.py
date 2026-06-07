from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                text="💬 Основной чат",
                callback_data="chat"
            )
        ],

        [
            InlineKeyboardButton(
                text="📺 Канал",
                callback_data="channel"
            )
        ],

        [
            InlineKeyboardButton(
                text="🤍 Оператор SIS",
                callback_data="operator1"
            ),

            InlineKeyboardButton(
                text="💚 Оператор BRO",
                callback_data="operator2"
            )
        ],

        [
            InlineKeyboardButton(
                text="🌐 Сайт",
                callback_data="site"
            )
        ],

        [
            InlineKeyboardButton(
                text="🔐 Резервный доступ",
                callback_data="reserve"
            )
        ],

        [
            InlineKeyboardButton(
                text="ℹ️ Информация",
                callback_data="info"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


def back_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="main_menu"
                )
            ]
        ]
    )


def admin_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="admin_stats"
            ),

            InlineKeyboardButton(
                text="📨 Рассылка",
                callback_data="admin_broadcast"
            )
        ],

        [
            InlineKeyboardButton(
                text="👤 Админы",
                callback_data="admin_admins"
            ),

            InlineKeyboardButton(
                text="🚫 Баны",
                callback_data="admin_bans"
            )
        ],

        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="admin_settings"
            ),

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

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


def admin_back():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Админ панель",
                    callback_data="admin_menu"
                )
            ]
        ]
    )


def broadcast_confirm():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data="broadcast_yes"
                ),

                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="broadcast_no"
                )
            ]
        ]
    )


def open_bot_keyboard(bot_username):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Открыть бота",
                    url=f"https://t.me/{bot_username}"
                )
            ]
        ]
    )