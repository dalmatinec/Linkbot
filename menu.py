from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# ==================================
# USER MENU
# ==================================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="💬 Основной чат",
                    callback_data="chat"
                ),

                InlineKeyboardButton(
                    text="📺 Канал",
                    callback_data="channel"
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
                    text="ℹ️ Информация",
                    callback_data="info"
                )
            ]
        ]
    )


def back_to_menu_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="main_menu"
                )
            ]
        ]
    )


# ==================================
# ADMIN PANEL
# ==================================

def admin_panel_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

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
                    text="⚙️ Настройки",
                    callback_data="admin_settings"
                ),

                InlineKeyboardButton(
                    text="👥 Админы",
                    callback_data="admin_admins"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🚫 Баны",
                    callback_data="admin_bans"
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
    )


# ==================================
# SETTINGS
# ==================================

def admin_settings_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="💬 Чат",
                    callback_data="set_chat"
                ),

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
                    text="🤍 SIS",
                    callback_data="set_operator1"
                ),

                InlineKeyboardButton(
                    text="💚 BRO",
                    callback_data="set_operator2"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🌐 Сайт",
                    callback_data="set_site"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⏳ TTL",
                    callback_data="set_ttl"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_home"
                )
            ]
        ]
    )


# ==================================
# ADMINS
# ==================================

def admins_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="➕ Добавить",
                    callback_data="admin_add"
                ),

                InlineKeyboardButton(
                    text="➖ Удалить",
                    callback_data="admin_remove"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Список",
                    callback_data="admin_list"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_home"
                )
            ]
        ]
    )


# ==================================
# BANS
# ==================================

def bans_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔨 Забанить",
                    callback_data="ban_user"
                ),

                InlineKeyboardButton(
                    text="🔓 Разбанить",
                    callback_data="unban_user"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_home"
                )
            ]
        ]
    )


# ==================================
# BROADCAST
# ==================================

def broadcast_confirm_keyboard():

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