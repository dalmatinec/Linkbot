from datetime import datetime, timedelta
import csv
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery
)

from aiogram.fsm.context import FSMContext

from config import (
    OWNER_ID,
    ADMIN_GROUP_ID
)

from texts import (
    DEFAULT_START_TEXT,
    DEFAULT_RULES_TEXT,
    SUPPORT_TEXT,
    LINK_COMMAND_TEXT,
    BANNED_TEXT
)

from menu import (
    start_menu,
    support_menu,
    admin_menu,
    admins_menu,
    bans_menu,
    settings_menu,
    timers_menu,
    broadcast_confirm_menu,
    cancel_menu,
    back_menu,
    bot_link_menu
)

from states import (
    BroadcastStates,
    SupportStates,
    AdminStates,
    BanStates,
    SettingsStates
)

from db import (
    add_user,
    update_activity,
    get_user,
    is_banned,

    get_setting,
    set_setting,

    add_link_log,
    increase_link_counter,

    add_support_ticket,
    get_last_ticket_time,

    is_admin,
    get_admins,
    add_admin,
    remove_admin,

    ban_user,
    unban_user,

    get_full_statistics,
    get_admin_logs,
    export_users,

    add_admin_log
)

router = Router()

support_map = {}


async def check_user(user_id):
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

    if await check_user(user.id):
        await message.answer(
            BANNED_TEXT
        )
        return

    text = get_setting(
        "start_text"
    )

    if not text:
        text = DEFAULT_START_TEXT

    photo = get_setting(
        "start_photo"
    )

    try:

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

    except:

        await message.answer(
            text,
            reply_markup=start_menu()
        )


@router.message(Command("help"))
async def help_command(message: Message):

    text = (
        "📚 Команды\n\n"
        "/start - главное меню\n"
        "/help - помощь\n"
        "/link - ссылка на бота\n"
    )

    if is_admin(
        message.from_user.id
    ):
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
async def back_start(
    callback: CallbackQuery
):

    text = get_setting(
        "start_text"
    )

    if not text:
        text = DEFAULT_START_TEXT

    photo = get_setting(
        "start_photo"
    )

    try:

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

    except:

        pass

    await callback.answer()


@router.callback_query(
    F.data == "rules_support"
)
async def rules_support(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "Выберите раздел.",
        reply_markup=support_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "show_rules"
)
async def show_rules(
    callback: CallbackQuery
):

    rules = get_setting(
        "rules_text"
    )

    if not rules:
        rules = DEFAULT_RULES_TEXT

    await callback.message.edit_text(
        rules,
        reply_markup=support_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "support"
)
async def support_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SupportStates.waiting_message
    )

    await callback.message.answer(
        SUPPORT_TEXT
    )

    await callback.answer()


@router.message(
    SupportStates.waiting_message
)
async def support_message(
    message: Message,
    state: FSMContext
):

    cooldown = int(
        get_setting(
            "support_cooldown"
        ) or 60
    )

    last_ticket = get_last_ticket_time(
        message.from_user.id
    )

    if last_ticket:

        last_time = datetime.fromisoformat(
            last_ticket
        )

        passed = (
            datetime.now()
            - last_time
        ).total_seconds()

        if passed < cooldown:

            wait = int(
                cooldown - passed
            )

            await message.answer(
                f"⏳ Подождите {wait} сек."
            )

            return

    add_support_ticket(
        message.from_user.id
    )

    user = message.from_user

    text = (
        "📩 ОБРАЩЕНИЕ\n\n"
        f"👤 {user.first_name}\n"
        f"🆔 {user.id}\n"
        f"📎 @{user.username or '-'}\n\n"
        f"💬 {message.text}"
    )

    sent = await message.bot.send_message(
        ADMIN_GROUP_ID,
        text
    )

    support_map[
        sent.message_id
    ] = user.id

    await message.answer(
        "✅ Сообщение отправлено."
    )

    await state.clear()

@router.message()
async def support_admin_reply(
    message: Message
):

    if message.chat.id != ADMIN_GROUP_ID:
        return

    if not message.reply_to_message:
        return

    reply_id = (
        message.reply_to_message.message_id
    )

    if reply_id not in support_map:
        return

    user_id = support_map[reply_id]

    try:

        await message.bot.send_message(
            user_id,
            f"💬 Ответ поддержки:\n\n{message.text}"
        )

        await message.reply(
            "✅ Ответ отправлен."
        )

    except:

        await message.reply(
            "❌ Пользователь недоступен."
        )


@router.message(Command("admin"))
async def admin_command(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):
        return

    await message.answer(
        "⚙️ Админ панель",
        reply_markup=admin_menu()
    )


@router.callback_query(
    F.data == "admin_stats"
)
async def admin_stats(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    stats = get_full_statistics()

    text = f"""
📊 СТАТИСТИКА

👥 Всего пользователей:
{stats['total_users']}

🆕 Сегодня:
{stats['new_today']}

📅 За неделю:
{stats['new_week']}

🗓 За месяц:
{stats['new_month']}

👤 Активные сегодня:
{stats['active_today']}

🔗 Всего ссылок:
{stats['total_links']}

💬 Чат:
{stats['chat_links']}

📺 Канал:
{stats['channel_links']}

🔐 Резерв:
{stats['reserve_links']}

🚫 Забанено:
{stats['banned']}

⛔ Заблокировали:
{stats['blocked']}

👨‍💼 Администраторы:
{stats['admins']}
"""

    await callback.message.edit_text(
        text,
        reply_markup=admin_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "admin_admins"
)
async def admin_admins(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "👨‍💼 Управление администраторами",
        reply_markup=admins_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "admins_list"
)
async def admins_list(
    callback: CallbackQuery
):

    admins = get_admins()

    text = "👨‍💼 Администраторы\n\n"

    for admin in admins:

        text += (
            f"🆔 {admin[0]}\n"
            f"👤 {admin[1]}\n"
            f"🎖 {admin[2]}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=admins_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "add_admin"
)
async def add_admin_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if callback.from_user.id != OWNER_ID:
        await callback.answer(
            "Только владелец.",
            show_alert=True
        )
        return

    await state.set_state(
        AdminStates.waiting_admin_id
    )

    await callback.message.answer(
        "Введите ID пользователя:"
    )

    await callback.answer()


@router.message(
    AdminStates.waiting_admin_id
)
async def add_admin_finish(
    message: Message,
    state: FSMContext
):

    try:

        admin_id = int(
            message.text
        )

    except:

        await message.answer(
            "Введите ID числом."
        )
        return

    add_admin(
        admin_id,
        "admin"
    )

    add_admin_log(
        message.from_user.id,
        "add_admin",
        str(admin_id)
    )

    await message.answer(
        "✅ Администратор добавлен."
    )

    await state.clear()


@router.callback_query(
    F.data == "remove_admin"
)
async def remove_admin_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if callback.from_user.id != OWNER_ID:
        return

    await state.set_state(
        AdminStates.waiting_remove_admin
    )

    await callback.message.answer(
        "Введите ID администратора:"
    )

    await callback.answer()


@router.message(
    AdminStates.waiting_remove_admin
)
async def remove_admin_finish(
    message: Message,
    state: FSMContext
):

    try:

        admin_id = int(
            message.text
        )

    except:

        return

    remove_admin(
        admin_id
    )

    add_admin_log(
        message.from_user.id,
        "remove_admin",
        str(admin_id)
    )

    await message.answer(
        "✅ Администратор удалён."
    )

    await state.clear()


@router.callback_query(
    F.data == "admin_bans"
)
async def admin_bans(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "🚫 Управление банами",
        reply_markup=bans_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "ban_user"
)
async def ban_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        BanStates.waiting_ban_id
    )

    await callback.message.answer(
        "Введите ID пользователя:"
    )

    await callback.answer()


@router.message(
    BanStates.waiting_ban_id
)
async def ban_finish(
    message: Message,
    state: FSMContext
):

    try:

        user_id = int(
            message.text
        )

    except:

        return

    ban_user(
        user_id
    )

    add_admin_log(
        message.from_user.id,
        "ban",
        str(user_id)
    )

    await message.answer(
        "✅ Пользователь забанен."
    )

    await state.clear()


@router.callback_query(
    F.data == "unban_user"
)
async def unban_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        BanStates.waiting_unban_id
    )

    await callback.message.answer(
        "Введите ID пользователя:"
    )

    await callback.answer()


@router.message(
    BanStates.waiting_unban_id
)
async def unban_finish(
    message: Message,
    state: FSMContext
):

    try:
        user_id = int(
            message.text
        )

    except:

        await message.answer(
            "Введите корректный ID."
        )
        return

    unban_user(user_id)

    add_admin_log(
        message.from_user.id,
        "unban",
        str(user_id)
    )

    await message.answer(
        "✅ Пользователь разбанен."
    )

    await state.clear()


@router.callback_query(
    F.data == "admin_settings"
)
async def admin_settings(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "⚙️ Настройки",
        reply_markup=settings_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "back_admin"
)
async def back_admin(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "⚙️ Админ панель",
        reply_markup=admin_menu()
    )

    await callback.answer()


@router.callback_query(
    F.data == "set_chat"
)
async def set_chat_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_chat_id
    )

    await callback.message.answer(
        "Отправьте ID чата."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_chat_id
)
async def set_chat_finish(
    message: Message,
    state: FSMContext
):

    set_setting(
        "chat_id",
        message.text
    )

    add_admin_log(
        message.from_user.id,
        "set_chat",
        message.text
    )

    await message.answer(
        "✅ Основной чат обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_channel"
)
async def set_channel_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_channel_id
    )

    await callback.message.answer(
        "Отправьте ID канала."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_channel_id
)
async def set_channel_finish(
    message: Message,
    state: FSMContext
):

    set_setting(
        "channel_id",
        message.text
    )

    add_admin_log(
        message.from_user.id,
        "set_channel",
        message.text
    )

    await message.answer(
        "✅ Канал обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_reserve"
)
async def set_reserve_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_reserve_id
    )

    await callback.message.answer(
        "Отправьте ID резерва."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_reserve_id
)
async def set_reserve_finish(
    message: Message,
    state: FSMContext
):

    set_setting(
        "reserve_id",
        message.text
    )

    add_admin_log(
        message.from_user.id,
        "set_reserve",
        message.text
    )

    await message.answer(
        "✅ Резерв обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_start_text"
)
async def set_start_text_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_start_text
    )

    await callback.message.answer(
        "Отправьте новый стартовый текст."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_start_text
)
async def set_start_text_finish(
    message: Message,
    state: FSMContext
):

    set_setting(
        "start_text",
        message.html_text
    )

    add_admin_log(
        message.from_user.id,
        "set_start_text"
    )

    await message.answer(
        "✅ Стартовый текст обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_rules"
)
async def set_rules_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_rules_text
    )

    await callback.message.answer(
        "Отправьте новый текст правил."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_rules_text
)
async def set_rules_finish(
    message: Message,
    state: FSMContext
):

    set_setting(
        "rules_text",
        message.html_text
    )

    add_admin_log(
        message.from_user.id,
        "set_rules"
    )

    await message.answer(
        "✅ Правила обновлены."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_photo"
)
async def set_photo_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_start_photo
    )

    await callback.message.answer(
        "Отправьте изображение."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_start_photo,
    F.photo
)
async def set_photo_finish(
    message: Message,
    state: FSMContext
):

    photo_id = message.photo[-1].file_id

    set_setting(
        "start_photo",
        photo_id
    )

    add_admin_log(
        message.from_user.id,
        "set_photo"
    )

    await message.answer(
        "✅ Фото обновлено."
    )

    await state.clear()

@router.callback_query(
    F.data == "set_timers"
)
async def set_timers(
    callback: CallbackQuery
):

    await callback.message.edit_text(
        "⏱ Управление таймерами",
        reply_markup=timers_menu()
    )

    await callback.answer()

@router.callback_query(
    F.data == "chat_timer"
)
async def chat_timer_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_chat_cooldown
    )

    await callback.message.answer(
        "Введите время в минутах."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_chat_cooldown
)
async def chat_timer_finish(
    message: Message,
    state: FSMContext
):

    try:
        value = int(message.text)

    except:

        await message.answer(
            "Введите число."
        )
        return

    set_setting(
        "chat_cooldown",
        value
    )

    add_admin_log(
        message.from_user.id,
        "chat_cooldown",
        str(value)
    )

    await message.answer(
        "✅ Таймер обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "channel_timer"
)
async def channel_timer_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_channel_cooldown
    )

    await callback.message.answer(
        "Введите время в минутах."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_channel_cooldown
)
async def channel_timer_finish(
    message: Message,
    state: FSMContext
):

    try:
        value = int(message.text)

    except:

        await message.answer(
            "Введите число."
        )
        return

    set_setting(
        "channel_cooldown",
        value
    )

    add_admin_log(
        message.from_user.id,
        "channel_cooldown",
        str(value)
    )

    await message.answer(
        "✅ Таймер обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "reserve_timer"
)
async def reserve_timer_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_reserve_cooldown
    )

    await callback.message.answer(
        "Введите время в минутах."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_reserve_cooldown
)
async def reserve_timer_finish(
    message: Message,
    state: FSMContext
):

    try:
        value = int(message.text)

    except:

        return

    set_setting(
        "reserve_cooldown",
        value
    )

    add_admin_log(
        message.from_user.id,
        "reserve_cooldown",
        str(value)
    )

    await message.answer(
        "✅ Таймер обновлён."
    )

    await state.clear()

@router.callback_query(
    F.data == "support_timer"
)
async def support_timer_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_support_cooldown
    )

    await callback.message.answer(
        "Введите задержку в секундах."
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_support_cooldown
)
async def support_timer_finish(
    message: Message,
    state: FSMContext
):

    try:
        value = int(message.text)

    except:

        return

    set_setting(
        "support_cooldown",
        value
    )

    add_admin_log(
        message.from_user.id,
        "support_cooldown",
        str(value)
    )

    await message.answer(
        "✅ Значение сохранено."
    )

    await state.clear()

@router.callback_query(
    F.data == "broadcast_delay"
)
async def broadcast_delay_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(
        SettingsStates.waiting_broadcast_delay
    )

    await callback.message.answer(
        "Введите задержку.\n\nПример:\n0.5"
    )

    await callback.answer()


@router.message(
    SettingsStates.waiting_broadcast_delay
)
async def broadcast_delay_finish(
    message: Message,
    state: FSMContext
):

    try:
        value = float(
            message.text
        )

    except:

        await message.answer(
            "Введите число."
        )
        return

    set_setting(
        "broadcast_delay",
        value
    )

    add_admin_log(
        message.from_user.id,
        "broadcast_delay",
        str(value)
    )

    await message.answer(
        "✅ Значение обновлено."
    )

    await state.clear()

@router.callback_query(
    F.data == "admin_logs"
)
async def admin_logs(
    callback: CallbackQuery
):

    logs = get_admin_logs()

    if not logs:

        await callback.message.edit_text(
            "Логи отсутствуют.",
            reply_markup=admin_menu()
        )

        return

    text = "📋 Последние действия\n\n"

    for log in logs[:20]:

        text += (
            f"#{log[0]}\n"
            f"👤 {log[1]}\n"
            f"⚙️ {log[2]}\n"
            f"🎯 {log[3]}\n\n"
        )

    await callback.message.edit_text(
        text[:4000],
        reply_markup=admin_menu()
    )

    await callback.answer()

@router.callback_query(
    F.data == "admin_export"
)
async def admin_export(
    callback: CallbackQuery
):

    users = export_users()

    file_name = "users_export.csv"

    with open(
        file_name,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "user_id",
                "username",
                "first_name",
                "joined_at"
            ]
        )

        for user in users:
            writer.writerow(user)

    from aiogram.types import FSInputFile

    await callback.message.answer_document(
        FSInputFile(file_name)
    )

    await callback.answer()


@router.callback_query(
    F.data == "admin_broadcast"
)
async def broadcast_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await state.set_state(
        BroadcastStates.waiting_forward
    )

    await callback.message.answer(
        "📨 Перешлите сообщение для рассылки.",
        reply_markup=cancel_menu()
    )

    await callback.answer()


@router.message(
    BroadcastStates.waiting_forward
)
async def broadcast_receive(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        broadcast_chat=message.chat.id,
        broadcast_message=message.message_id
    )

    await state.set_state(
        BroadcastStates.waiting_confirm
    )

    await message.answer(
        "Подтвердить рассылку?",
        reply_markup=broadcast_confirm_menu()
    )


@router.callback_query(
    F.data == "broadcast_cancel"
)
async def broadcast_cancel(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "❌ Рассылка отменена."
    )

    await callback.answer()


@router.callback_query(
    F.data == "cancel_action"
)
async def cancel_action(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.clear()

    await callback.message.edit_text(
        "❌ Действие отменено."
    )

    await callback.answer()


@router.callback_query(
    F.data == "broadcast_confirm"
)
async def broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext
):

    data = await state.get_data()

    source_chat = data.get(
        "broadcast_chat"
    )

    source_message = data.get(
        "broadcast_message"
    )

    users = get_all_users()

    delay = float(
        get_setting(
            "broadcast_delay"
        ) or 0.5
    )

    success = 0
    failed = 0

    status = await callback.message.answer(
        "📨 Рассылка началась..."
    )


for user in users:

        user_id = user[0]

        try:

            await callback.bot.forward_message(
                chat_id=user_id,
                from_chat_id=source_chat,
                message_id=source_message
            )

            success += 1

        except Exception:

            failed += 1

        await asyncio.sleep(delay)

add_broadcast(
        callback.from_user.id,
        success,
        failed
    )
    add_admin_log(
        callback.from_user.id,
        "broadcast",
        f"{success}/{failed}"
    )

    await status.edit_text(
        f"""
📨 РАССЫЛКА ЗАВЕРШЕНА

✅ Доставлено:
{success}

❌ Ошибок:
{failed}

📊 Всего:
{success + failed}
"""
    )

    await state.clear()

    await callback.answer()


@router.my_chat_member()
async def bot_block_handler(event):

    try:

        if (
            event.new_chat_member.status
            == "kicked"
        ):

            add_user_block(
                event.from_user.id
            )

    except:

        pass


try:

    await message.bot.send_message(
        LOG_CHANNEL_ID,
        f"""
👤 НОВЫЙ ПОЛЬЗОВАТЕЛЬ

🆔 {user.id}

👤 {user.first_name}

📎 @{user.username or '-'}
"""
    )

except:
    pass

