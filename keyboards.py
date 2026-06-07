from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура с кнопками меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="💬 Основной чат"),
        KeyboardButton(text="📺 Канал"),
        KeyboardButton(text="🤍 Оператор"),
        KeyboardButton(text="🌐 Сайт"),
        KeyboardButton(text="🔐 Резервный доступ"),
        KeyboardButton(text="ℹ️ Информация")
    )
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Админ-панель клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📨 Рассылка"),
        KeyboardButton(text="👤 Админы"),
        KeyboardButton(text="🚫 Баны"),
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="📋 Логи"),
        KeyboardButton(text="🔙 Выйти из админки")
    )
    builder.adjust(2, 2, 3)
    return builder.as_markup(resize_keyboard=True)

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка назад"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(resize_keyboard=True)

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения рассылки"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
    )
    return builder.as_markup()

def get_operators_keyboard() -> InlineKeyboardMarkup:
    """Инлайн клавиатура с двумя операторами (достаёт из БД динамически)"""
    from db import get_setting
    
    operator1_name = get_setting('operator1_name') or 'Оператор SIS'
    operator1_link = get_setting('operator1_link')
    operator2_name = get_setting('operator2_name') or 'Оператор BRO'
    operator2_link = get_setting('operator2_link')
    
    builder = InlineKeyboardBuilder()
    
    if operator1_link:
        builder.add(InlineKeyboardButton(text=operator1_name, url=operator1_link))
    if operator2_link:
        builder.add(InlineKeyboardButton(text=operator2_name, url=operator2_link))
    
    return builder.as_markup() if builder.buttons else None

def get_link_keyboard(link_type: str, link_url: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой перехода по ссылке"""
    builder = InlineKeyboardBuilder()
    
    if link_type == "chat":
        text = "💬 Перейти в чат"
    elif link_type == "channel":
        text = "📺 Перейти в канал"
    elif link_type == "reserve":
        text = "🔐 Получить резервный доступ"
    elif link_type == "site":
        text = "🌐 Перейти на сайт"
    else:
        text = "🔗 Перейти"
    
    builder.add(InlineKeyboardButton(text=text, url=link_url))
    builder.add(InlineKeyboardButton(text="❌ Закрыть", callback_data="close"))
    return builder.as_markup()

def get_admin_list_keyboard(admins: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком админов для удаления"""
    builder = InlineKeyboardBuilder()
    
    for admin in admins:
        if admin['role'] != 'owner':  # владельца нельзя удалить
            builder.add(InlineKeyboardButton(
                text=f"❌ {admin['username'] or admin['user_id']}",
                callback_data=f"del_admin_{admin['user_id']}"
            ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    builder.adjust(1)
    return builder.as_markup()

def get_users_list_keyboard(users: list, action: str) -> InlineKeyboardMarkup:
    """Клавиатура со списком пользователей для бана/разбана"""
    builder = InlineKeyboardBuilder()
    
    for user in users:
        status = "🔴" if user['banned'] else "🟢"
        builder.add(InlineKeyboardButton(
            text=f"{status} {user['first_name'][:20]} (@{user['username']})" if user['username'] else f"{status} {user['first_name'][:20]}",
            callback_data=f"{action}_{user['user_id']}"
        ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    builder.adjust(1)
    return builder.as_markup()

def get_settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    """Клавиатура с настройками для редактирования"""
    builder = InlineKeyboardBuilder()
    
    settings_labels = {
        'chat_link': '📝 Ссылка на чат',
        'channel_link': '📝 Ссылка на канал',
        'operator1_name': '📝 Имя оператора 1',
        'operator1_link': '📝 Ссылка на оператора 1',
        'operator2_name': '📝 Имя оператора 2',
        'operator2_link': '📝 Ссылка на оператора 2',
        'reserve_link': '📝 Резервная ссылка',
        'site_link': '📝 Ссылка на сайт',
        'info_text': '📝 Текст информации'
    }
    
    for key, label in settings_labels.items():
        if key in settings:
            # Показываем текущее значение (обрезанное)
            value = settings[key]
            display_value = value[:20] + "..." if len(value) > 20 else value
            builder.add(InlineKeyboardButton(
                text=f"{label}\nТекущее: {display_value or '(пусто)'}",
                callback_data=f"edit_setting_{key}"
            ))
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back"))
    builder.adjust(1)
    return builder.as_markup()