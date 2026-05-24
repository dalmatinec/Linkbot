from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                text="Наш чат 💬",
                callback_data="chat"
            ),

            InlineKeyboardButton(
                text="Канал 📺",
                callback_data="channel"
            )
        ],

        [
            InlineKeyboardButton(
                text="Наш сайт-визитка 🌐",
                callback_data="site"
            )
        ],

        [
            InlineKeyboardButton(
                text="Резервный чат 🔐",
                callback_data="reserve"
            )
        ],

        [
            InlineKeyboardButton(
                text="Оператор сис 🤍",
                callback_data="operator1"
            ),

            InlineKeyboardButton(
                text="Оператор бро 💚",
                callback_data="operator2"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


def back_to_menu_keyboard():

    keyboard = [
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="main_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


def confirm_broadcast_keyboard():

    keyboard = [
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

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )