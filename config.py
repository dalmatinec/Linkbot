# ===== Общие настройки =====
# Секреты (токены, ключи) берутся из файла .env, чтобы не попасть в git.
# Скопируйте .env.example в .env и заполните.
import os

from dotenv import load_dotenv

load_dotenv()

# --- Гостевой бот (aiogram) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")   # username бота без @

# Кто имеет право вызывать бота: id юзербот-аккаунта (и ваш), через запятую в .env.
# Чужие упоминания бот игнорирует, чтобы его не дёргали все подряд.
ALLOWED_CALLERS = {int(x) for x in os.getenv("ALLOWED_CALLERS", "").replace(" ", "").split(",") if x}

# Рекламные посты. Бот выдаёт их по кругу, отдельно для каждой группы.
# text поддерживает HTML: <b>, <i>, <a href="...">
POSTS = [
    {
        "title": "Веб-дизайн",
        "text": "<b>Сайты и лендинги под ключ</b>\n\nДизайн, вёрстка, запуск за 7 дней.",
        "preview_url": None,  # ссылка для большого превью или None
        "buttons": [
            ("Портфолио", "https://example.com/portfolio"),
            ("Написать нам", "https://t.me/your_manager"),
        ],
    },
    {
        "title": "Telegram-боты",
        "text": "<b>Боты для бизнеса</b>\n\nЗаявки, оплаты, рассылки, CRM.",
        "preview_url": None,
        "buttons": [
            ("Заказать бота", "https://t.me/your_manager"),
        ],
    },
]

# --- Юзербот (Telethon) ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Группы, где админы согласились: @username или числовой id
CHATS = [
    "@group_one",
    -1001234567890,
]

INTERVAL_MIN = 60                # раз во сколько минут проходить по всем группам
PAUSE_BETWEEN_CHATS = (20, 60)   # случайная пауза между группами, сек
DELETE_TRIGGER = False           # удалять своё сообщение "@bot" после ответа бота
DELETE_AFTER_SEC = 20
