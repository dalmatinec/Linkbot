WELCOME_TEXT = (
    "👋 Добро пожаловать в <b>Lady Shop</b>!\n\n"
    "Мы рады видеть вас в нашем магазине. 🌸\n"
    "Выберите нужный раздел ниже 👇"
)

RULES_TEXT = (
    "📜 <b>Правила сообщества Lady Shop</b>\n\n"
    "1. Уважайте других участников\n"
    "2. Запрещён спам и реклама\n"
    "3. Не публикуйте посторонние ссылки\n"
    "4. Общайтесь по теме магазина\n"
    "5. За нарушения — бан без предупреждения\n\n"
    "Спасибо, что соблюдаете правила! 🌸"
)

SUPPORT_PROMPT = (
    "💬 <b>Техническая поддержка</b>\n\n"
    "Напишите ваш вопрос или проблему — мы ответим как можно скорее. 👇"
)

SUPPORT_DELIVERED = (
    "✅ Ваше сообщение доставлено операторам.\n"
    "Ожидайте ответа в этом чате."
)

FLOOD_BAN_MSG = (
    "🚫 Вы временно заблокированы за флуд.\n"
    "Повторите попытку через 5 минут."
)

NOT_SUBSCRIBED = (
    "📢 Для использования бота необходимо подписаться на наш канал.\n\n"
    "После подписки нажмите <b>✅ Проверить</b>."
)

BANNED_MSG = "🚫 Вы заблокированы и не можете использовать этого бота."

ACCESS_DENIED = "⛔ У вас нет доступа к этой команде."

NO_LINK = "⚠️ Ссылка пока не установлена. Попробуйте позже."


def LINK_MSG(btn_name: str, url: str, minutes: int) -> str:
    return (
        f"🔗 <b>{btn_name}</b>\n\n"
        f"Ваша персональная ссылка:\n{url}\n\n"
        f"⏱ Ссылка действительна <b>{minutes} мин</b>.\n"
        f"Повторный запрос будет доступен через {minutes} мин."
    )


def LINK_WAIT(seconds: int) -> str:
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        time_str = f"{minutes} мин {secs} сек" if secs else f"{minutes} мин"
    else:
        time_str = f"{secs} сек"
    return (
        f"⏳ Вы уже получали эту ссылку недавно.\n\n"
        f"Повторный запрос будет доступен через <b>{time_str}</b>."
    )


def SUPPORT_FORM_USER(uid: int, username: str, name: str, text: str) -> str:
    uname = f"@{username}" if username else "нет"
    return (
        f"📩 <b>Новое обращение в поддержку</b>\n\n"
        f"👤 Пользователь: <a href='tg://user?id={uid}'>{name}</a>\n"
        f"🔗 Username: {uname}\n"
        f"🆔 ID: <code>{uid}</code>\n\n"
        f"💬 <b>Сообщение:</b>\n{text}"
    )


def SUPPORT_FORM_REPLY(admin_name: str, text: str) -> str:
    return (
        f"📬 <b>Ответ от поддержки</b>\n\n"
        f"👩‍💼 Саппорт: {admin_name}\n\n"
        f"💬 {text}"
    )


def BROADCAST_CONFIRM(count: int) -> str:
    return (
        f"📨 <b>Подтверждение рассылки</b>\n\n"
        f"Сообщение будет отправлено <b>{count}</b> пользователям.\n\n"
        f"Продолжить?"
    )


def BROADCAST_DONE(success: int, failed: int) -> str:
    return (
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📤 Отправлено: <b>{success}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>"
    )


def DAILY_REPORT(stats: dict) -> str:
    return (
        f"📊 <b>Ежедневный отчёт Lady Shop</b>\n"
        f"📅 Дата: {stats.get('date', '—')}\n\n"
        f"👥 Новых пользователей: <b>{stats.get('new_users', 0)}</b>\n"
        f"🌸 Ссылок на чат: <b>{stats.get('links_chat', 0)}</b>\n"
        f"📢 Ссылок на канал: <b>{stats.get('links_channel', 0)}</b>\n"
        f"🔄 Ссылок на резерв: <b>{stats.get('links_reserve', 0)}</b>"
    )