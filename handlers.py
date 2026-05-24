import time

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile
)

from aiogram.filters import (
    CommandStart,
    Command
)

from config import (
    LOG_GROUP_ID,
    RESERVE_BOT,
    DEFAULT_TTL,
    SPAM_DELAY,
    LINK_COOLDOWN,
    SITE_LINK
)

from menu import (
    main_menu,
    back_to_menu_keyboard
)

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
<b>Добро пожаловать в Lady Shop</b> ✨

Выберите нужный раздел ниже.

🔒 Все ссылки временные
для безопасности пользователей.

🤖 Сохраняйте резервного бота:

{RESERVE_BOT}
"""


LINK_TEXT = """
<b>🔗 Ваша ссылка готова</b>

⏳ Ссылка действует 15 минут

⚠️ Не передавайте ссылку другим людям
"""


SITE_TEXT = f"""
🌐 Сохраните сайт-визитку.

Там всегда находятся актуальные ссылки.

👇 Сайт:
{SITE_LINK}
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
        f"🆕 Новый пользователь\n\nID: {user_id}"
    )


@router.message(Command("menu"))
async def menu_command(message: Message):

    photo = FSInputFile("welcome.jpg")

    await message.answer_photo(
        photo=photo,
        caption=WELCOME_TEXT,
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):

    photo = FSInputFile("welcome.jpg")

    await callback.message.answer_photo(
        photo=photo,
        caption=WELCOME_TEXT,
        reply_markup=main_menu()
    )

    await callback.answer()


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

        await message.answer(
            f"⏳ Новая ссылка будет доступна через {minutes} мин."
        )

        return

    chat_id = get_chat_id("chat")

    if not chat_id:

        await message.answer(
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

        await message.answer_photo(
            photo=photo,
            caption=f"{LINK_TEXT}\n\n👇 Вход:\n{link}"
        )

        await send_log(
            bot,
            f"🔗 Получена ссылка\n\nID: {user_id}"
        )

    except Exception as e:

        await message.answer(
            "❌ Ошибка создания ссылки."
        )

        await send_log(
            bot,
            f"❌ Invite error\n\n{e}"
        )


@router.callback_query(F.data == "site")
async def site_callback(callback: CallbackQuery):

    await callback.message.answer(
        SITE_TEXT,
        disable_web_page_preview=True,
        reply_markup=back_to_menu_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "operator1")
async def operator1_callback(callback: CallbackQuery):

    operator1 = get_setting("operator1")

    if not operator1:
        operator1 = "@none"

    text = f"""
🤍 Операторы никогда не пишут первыми

⚠️ Остерегайтесь фейков и швыров

👇 Оператор сис

{operator1}
"""

    await callback.message.answer(
        text,
        disable_web_page_preview=True,
        reply_markup=back_to_menu_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "operator2")
async def operator2_callback(callback: CallbackQuery):

    operator2 = get_setting("operator2")

    if not operator2:
        operator2 = "@none"

    text = f"""
🤍 Операторы никогда не пишут первыми

⚠️ Остерегайтесь фейков и швыров

👇 Оператор бро

{operator2}
"""

    await callback.message.answer(
        text,
        disable_web_page_preview=True,
        reply_markup=back_to_menu_keyboard()
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
            f"Новая ссылка через {minutes} мин.",
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
            caption=f"{LINK_TEXT}\n\n👇 Вход:\n{link}",
            reply_markup=back_to_menu_keyboard()
        )

        await callback.answer()

        await send_log(
            bot,
            f"🔗 Получена ссылка\n\nID: {user_id}"
        )

    except Exception as e:

        await callback.answer(
            "Ошибка создания ссылки.",
            show_alert=True
        )

        await send_log(
            bot,
            f"❌ Invite error\n\n{e}"
        )