import asyncio

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery
)

from aiogram.filters import Command

from config import (
    OWNER_ID,
    BROADCAST_DELAY
)

from menu import confirm_broadcast_keyboard

from db import (
    is_admin,
    add_admin,
    remove_admin,
    get_user_by_username,
    set_setting,
    get_all_users,
    get_stats,
    ban_user,
    unban_user
)

router = Router()

broadcast_message = None


def has_access(user_id):

    if user_id == OWNER_ID:
        return True

    if is_admin(user_id):
        return True

    return False


@router.message(Command("help"))
async def help_command(message: Message):

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    text = """
<b>📌 Команды администратора</b>

/stats
/send

/setlink
/setttl
/setoperator

/add
/del

/ban
/unban
"""

    await message.answer(text)


@router.message(Command("stats"))
async def stats_command(message: Message):

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    users, banned, links = get_stats()

    text = f"""
<b>📊 Статистика</b>

👤 Пользователей: {users}

🚫 Заблокировано: {banned}

🔗 Выдано ссылок: {links}
"""

    await message.answer(text)


@router.message(Command("setttl"))
async def setttl_command(message: Message):

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Пример:\n/setttl 900"
        )

        return

    ttl = args[1]

    set_setting(
        "ttl",
        ttl
    )

    await message.answer(
        f"✅ TTL обновлён: {ttl}"
    )


@router.message(Command("setoperator"))
async def setoperator_command(message: Message):

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 3:

        await message.answer(
            "Пример:\n/setoperator 1 @username"
        )

        return

    num = args[1]
    username = args[2]

    if num not in ["1", "2"]:

        await message.answer(
            "Доступно только 1 или 2"
        )

        return

    set_setting(
        f"operator{num}",
        username
    )

    await message.answer(
        "✅ Оператор обновлён."
    )


@router.message(Command("setlink"))
async def setlink_command(message: Message):

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 3:

        await message.answer(
            "Пример:\n/setlink chat -100..."
        )

        return

    key = args[1]
    value = args[2]

    allowed = [
        "chat",
        "channel",
        "reserve"
    ]

    if key not in allowed:

        await message.answer(
            "Доступно:\nchat\nchannel\nreserve"
        )

        return

    set_setting(
        key,
        value
    )

    await message.answer(
        f"✅ {key} обновлён."
    )


@router.message(Command("add"))
async def add_admin_command(message: Message):

    if message.chat.type != "private":
        return

    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Пример:\n/add @username"
        )

        return

    target = args[1]

    if target.startswith("@"):

        user = get_user_by_username(target)

        if not user:

            await message.answer(
                "❌ Пользователь не найден."
            )

            return

        add_admin(
            user[1],
            user[2]
        )

        await message.answer(
            "✅ Админ добавлен."
        )

        return

    try:

        user_id = int(target)

        add_admin(
            user_id,
            ""
        )

        await message.answer(
            "✅ Админ добавлен."
        )

    except:

        await message.answer(
            "❌ Ошибка."
        )


@router.message(Command("del"))
async def remove_admin_command(message: Message):

    if message.chat.type != "private":
        return

    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Пример:\n/del @username"
        )

        return

    target = args[1]

    if target.startswith("@"):

        user = get_user_by_username(target)

        if not user:

            await message.answer(
                "❌ Пользователь не найден."
            )

            return

        remove_admin(user[1])

        await message.answer(
            "✅ Админ удалён."
        )

        return

    try:

        user_id = int(target)

        remove_admin(user_id)

        await message.answer(
            "✅ Админ удалён."
        )

    except:

        await message.answer(
            "❌ Ошибка."
        )


@router.message(Command("ban"))
async def ban_command(message: Message):

    if not has_access(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        return

    try:

        user_id = int(args[1])

        ban_user(user_id)

        await message.answer(
            "✅ Пользователь заблокирован."
        )

    except:

        await message.answer(
            "❌ Ошибка."
        )


@router.message(Command("unban"))
async def unban_command(message: Message):

    if not has_access(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        return

    try:

        user_id = int(args[1])

        unban_user(user_id)

        await message.answer(
            "✅ Пользователь разблокирован."
        )

    except:

        await message.answer(
            "❌ Ошибка."
        )


@router.message(Command("send"))
async def send_command(message: Message):

    global broadcast_message

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    broadcast_message = None

    await message.answer(
        "📨 Перешлите сообщение для рассылки."
    )


@router.message(F.forward_from_chat | F.forward_from)
async def broadcast_message_handler(message: Message):

    global broadcast_message

    if message.chat.type != "private":
        return

    if not has_access(message.from_user.id):
        return

    broadcast_message = message

    users = get_all_users()

    await message.answer(
        f"📨 Подтвердить рассылку?\n\n"
        f"Получателей: {len(users)}",
        reply_markup=confirm_broadcast_keyboard()
    )


@router.callback_query(F.data == "broadcast_no")
async def cancel_broadcast(callback: CallbackQuery):

    global broadcast_message

    broadcast_message = None

    await callback.message.edit_text(
        "❌ Рассылка отменена."
    )

    await callback.answer()


@router.callback_query(F.data == "broadcast_yes")
async def start_broadcast(callback: CallbackQuery, bot):

    global broadcast_message

    if not broadcast_message:

        await callback.answer(
            "Нет сообщения."
        )

        return

    users = get_all_users()

    success = 0

    await callback.message.edit_text(
        "📨 Рассылка началась..."
    )

    for user in users:

        user_id = user[0]

        try:

            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=broadcast_message.chat.id,
                message_id=broadcast_message.message_id
            )

            success += 1

            await asyncio.sleep(
                BROADCAST_DELAY
            )

        except:
            pass

    await callback.message.answer(
        f"✅ Рассылка завершена\n\n"
        f"Отправлено: {success}"
    )

    broadcast_message = None

    await callback.answer()