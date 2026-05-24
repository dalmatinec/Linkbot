import time

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile
)

from aiogram.filters import CommandStart, Command

from config import (
    LOG_GROUP_ID,
    RESERVE_BOT,
    DEFAULT_TTL,
    SPAM_DELAY,
    LINK_COOLDOWN,
    SITE_LINK,
    OPERATOR_1,
    OPERATOR_2
)

from menu import main_menu

from db import (
    add_user,
    get_user,
    update_link_time,
    update_message_time,
    increment_links,
    is_banned,
    get_setting
)

router = Router()


WELCOME_TEXT = f"""
✨ Добро пожаловать в Lady Shop.

Выберите нужный раздел ниже.

🔒 Все ссылки выдаются временно
для безопасности пользователей.

🤖 Сохраняйте резервного бота:

{RESERVE_BOT}

⚠️ В случае блокировки основного бота используйте резерв.
"""


LINK_TEXT = """
🔗 Ваша временная ссылка готова

⏳ Ссылка действительна 15 минут

⚠️ Не передавайте ссылку третьим лицам
"""


SITE_TEXT = f"""
🌐 Сохраните наш сайт-визитку в закладки.

Там всегда находятся актуальные ссылки и информация.

👇 Сайт:
{SITE_LINK}
"""


OPERATORS_TEXT = f"""
🤍 Операторы никогда не пишут первыми в ЛС

⚠️ Остерегайтесь фейков и швыров.

Проверяйте username внимательно.

👇 Оператор сис:
{OPERATOR_1}

👇 Оператор бро:
{OPERATOR_2}
"""


async def send_log(bot, text):

    try:
        await bot.send_message(
            LOG_GROUP_ID,
            text
        )

    except:
        pass


def get_chat_id(name):

    value = get_setting(name)

    if value:
        return int(value)

    return None


async def create_invite(bot, chat_id):

    invite = await bot.create_chat_invite_link(
        chat_id=chat_id,
        expire_date=int(time.time()) + DEFAULT_TTL
    )

    return invite.invite_link


def is_spam(user):

    now = int(time.time())

    last_message_time = user[6]

    if now - last_message_time < SPAM_DELAY:
        return True

    return False


def check_cooldown(user):

    now = int(time.time())

    last_link_time = user[5]

    remaining = LINK_COOLDOWN - (
        now - last_link_time
    )

    if remaining > 0:
        return remaining

    return 0


@router.message(CommandStart())
async def start_handler(message: Message, bot):

    user_id = message.from_user.id

    if is_banned(user_id):
        return

    add_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name
    )

    photo = FSInputFile("welcome.jpg")

    await message.answer_photo(
        photo=photo,
        caption=WELCOME_TEXT,
        reply_markup=main_menu()
    )

    await send_log(
        bot,
        f"🆕 Новый пользователь:\n\nID: {user_id}"
    )


@router.message(Command("link"))
async def link_handler(message: Message, bot):

    if message.chat.type == "private":
        return

    user_id = message.from_user.id

    if is_banned(user_id):
        return

    add_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name
    )

    user = get_user(user_id)

    if is_spam(user):
        return

    cooldown = check_cooldown(user)

    if cooldown > 0:

        minutes = cooldown // 60

        await message.reply(
            f"⏳ Новую ссылку можно получить через {minutes} мин."
        )

        return

    chat_id = get_chat_id("chat")

    if not chat_id:

        await message.reply(
            "❌ Ссылка не настроена."
        )

        return

    try:

        link = await create_invite(
            bot,
            chat_id
        )

        update_link_time(
            user_id,
            int(time.time())
        )

        update_message_time(
            user_id,
            int(time.time())
        )

        increment_links()

        photo = FSInputFile("chat.jpg")

        await message.reply_photo(
            photo=photo,
            caption=f"{LINK_TEXT}\n\n👇 Вход:\n{link}"
        )

        await send_log(
            bot,
            f"🔗 Пользователь получил ссылку:\n\nID: {user_id}"
        )

    except Exception as e:

        await message.reply(
            "❌ Ошибка создания ссылки."
        )

        await send_log(
            bot,
            f"❌ Ошибка invite:\n{e}"
        )


@router.callback_query(F.data == "site")
async def site_callback(callback: CallbackQuery):

    await callback.message.answer(
        SITE_TEXT
    )

    await callback.answer()


@router.callback_query(F.data == "operator1")
@router.callback_query(F.data == "operator2")
async def operator_callback(callback: CallbackQuery):

    await callback.message.answer(
        OPERATORS_TEXT
    )

    await callback.answer()


@router.callback_query(
    F.data.in_(["chat", "channel", "reserve"])
)
async def link_callbacks(callback: CallbackQuery, bot):

    user_id = callback.from_user.id

    if is_banned(user_id):
        return

    user = get_user(user_id)

    if is_spam(user):

        await callback.answer(
            "Подождите немного.",
            show_alert=True
        )

        return

    cooldown = check_cooldown(user)

    if cooldown > 0:

        minutes = cooldown // 60

        await callback.answer(
            f"Новая ссылка будет доступна через {minutes} мин.",
            show_alert=True
        )

        return

    chat_id = get_chat_id(callback.data)

    if not chat_id:

        await callback.answer(
            "Ссылка не настроена.",
            show_alert=True
        )

        return

    try:

        link = await create_invite(
            bot,
            chat_id
        )

        update_link_time(
            user_id,
            int(time.time())
        )

        update_message_time(
            user_id,
            int(time.time())
        )

        increment_links()

        photo = FSInputFile("chat.jpg")

        await callback.message.answer_photo(
            photo=photo,
            caption=f"{LINK_TEXT}\n\n👇 Вход:\n{link}"
        )

        await callback.answer()

        await send_log(
            bot,
            f"🔗 Пользователь получил ссылку:\n\nID: {user_id}"
        )

    except Exception as e:

        await callback.answer(
            "Ошибка создания ссылки.",
            show_alert=True
        )

        await send_log(
            bot,
            f"❌ Invite error:\n{e}"
        )