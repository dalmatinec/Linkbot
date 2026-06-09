handlers.py (часть 1)

from aiogram import Router, F
from aiogram.types import (
Message,
CallbackQuery
)
from aiogram.filters import Command

from db import (
add_user,
update_activity,
get_user,
is_banned,
get_setting,
is_admin
)

from menu import (
start_menu,
support_menu,
bot_link_menu
)

from texts import (
DEFAULT_START_TEXT,
BANNED_TEXT,
LINK_COMMAND_TEXT
)

from datetime import datetime, timedelta

from db import (
    get_setting,
    add_link_log,
    increase_link_counter,
    update_activity
)

router = Router()

async def check_ban(user_id: int):
return is_banned(user_id)

@router.message(Command("start"))
async def start_command(message: Message):
user = message.from_user

add_user(
    user.id,
    user.username,
    user.first_name
)

update_activity(user.id)

if await check_ban(user.id):
    await message.answer(BANNED_TEXT)
    return

text = get_setting("start_text")

if not text:
    text = DEFAULT_START_TEXT

photo = get_setting("start_photo")

if photo:
    await message.answer_photo(
        photo=photo,
        caption=text,
        reply_markup=start_menu()
    )
else:
    await message.answer(
        text,
        reply_markup=start_menu()
    )

@router.message(Command("help"))
async def help_command(message: Message):
text = (
"📚 Доступные команды\n\n"
"/start - главное меню\n"
"/help - помощь\n"
)

if is_admin(message.from_user.id):
    text += "\n/admin - админ панель"

await message.answer(text)

@router.message(Command("link"))
async def link_command(message: Message):
if message.chat.type == "private":
return

me = await message.bot.get_me()

await message.reply(
    LINK_COMMAND_TEXT,
    reply_markup=bot_link_menu(
        me.username
    )
)

@router.callback_query(
F.data == "back_start"
)
async def back_start(callback: CallbackQuery):
text = get_setting("start_text")

if not text:
    text = DEFAULT_START_TEXT

photo = get_setting("start_photo")

if photo:
    await callback.message.delete()

    await callback.message.answer_photo(
        photo=photo,
        caption=text,
        reply_markup=start_menu()
    )
else:
    await callback.message.edit_text(
        text,
        reply_markup=start_menu()
    )

await callback.answer()

@router.callback_query(
F.data == "rules_support"
)
async def rules_support(callback: CallbackQuery):
await callback.message.edit_text(
"Выберите нужный раздел.",
reply_markup=support_menu()
)

await callback.answer()

@router.callback_query(
F.data == "show_rules"
)
async def show_rules(callback: CallbackQuery):
rules = get_setting("rules_text")

if not rules:
    rules = "Правила пока не настроены."

await callback.message.edit_text(
    rules,
    reply_markup=support_menu()
)

await callback.answer()

def get_cached_link(user_id, category):
    user_id = str(user_id)

    if user_id not in user_links_cache:
        return None

    if category not in user_links_cache[user_id]:
        return None

    data = user_links_cache[user_id][category]

    expires = datetime.fromisoformat(
        data["expires"]
    )

    if datetime.now() >= expires:
        return None

    return data


def save_cached_link(
    user_id,
    category,
    link,
    expires
):
    user_id = str(user_id)

    if user_id not in user_links_cache:
        user_links_cache[user_id] = {}

    user_links_cache[user_id][category] = {
        "link": link,
        "expires": expires.isoformat()
    }

#Получение ссылок
async def process_link(
    callback: CallbackQuery,
    category: str
):
    update_activity(
        callback.from_user.id
    )

    cached = get_cached_link(
        callback.from_user.id,
        category
    )

    if cached:
        await callback.message.answer(
            f"🔗 Ваша ссылка:\n\n{cached['link']}"
        )

        await callback.answer()

        return

#Получение настроек
if category == "chat":
        target = get_setting("chat_id")
        cooldown = int(
            get_setting("chat_cooldown")
        )

    elif category == "channel":
        target = get_setting("channel_id")
        cooldown = int(
            get_setting("channel_cooldown")
        )

    else:
        target = get_setting("reserve_id")
        cooldown = int(
            get_setting("reserve_cooldown")
        )

#проверка
if not target:
        await callback.answer(
            "Ссылка не настроена.",
            show_alert=True
        )
        return

#создание ссылки
try:
        invite = await callback.bot.create_chat_invite_link(
            chat_id=int(target),
            expire_date=datetime.now()
            + timedelta(minutes=cooldown),

            member_limit=1
        )

    except Exception:
        await callback.answer(
            "Ошибка создания ссылки.",
            show_alert=True
        )
        return

#сохраняем
save_cached_link(
        callback.from_user.id,
        category,
        invite.invite_link,
        datetime.now()
        + timedelta(minutes=cooldown)
    )

    add_link_log(
        callback.from_user.id,
        category
    )

    increase_link_counter(
        callback.from_user.id,
        category
    )

#отправка
await callback.message.answer(
        f"""
🔗 Временная ссылка:

{invite.invite_link}

⏳ Действует {cooldown} минут.
"""
    )

    await callback.answer()

#основнойЧат
@router.callback_query(
    F.data == "chat_link"
)
async def chat_link(
    callback: CallbackQuery
):
    await process_link(
        callback,
        "chat"
    )

#канал
@router.callback_query(
    F.data == "channel_link"
)
async def channel_link(
    callback: CallbackQuery
):
    await process_link(
        callback,
        "channel"
    )

#резерв
@router.callback_query(
    F.data == "reserve_link"
)
async def reserve_link(
    callback: CallbackQuery
):
    await process_link(
        callback,
        "reserve"
    )



