# handlers_group.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import get_database
from keyboards import (
    get_posts_list_keyboard,
    get_post_detail_keyboard,
    get_groups_list_keyboard,
    get_interval_keyboard,
    get_confirm_keyboard,
    get_back_keyboard
)

logger = logging.getLogger(__name__)
router = Router()
db = get_database()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class CreatePostStates(StatesGroup):
    waiting_for_groups = State()
    waiting_for_interval = State()
    waiting_confirmation = State()


@router.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    posts = db.get_all_posts()
    
    if not posts:
        await message.answer("📭 Нет созданных рассылок.")
        return
    
    text = "📋 Список рассылок:\n\n"
    for post in posts:
        groups_count = db.get_post_groups_count(post["id"])
        text += f"{post['id']}. {post['title']} (групп: {groups_count})\n"
    
    await message.answer(text, reply_markup=get_posts_list_keyboard(posts))


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    if not message.reply_to_message:
        await message.answer("❌ Используйте /new ответом на сообщение, которое хотите разослать.")
        return
    
    reply = message.reply_to_message
    
    if reply.text:
        title = reply.text[:50] + "..." if len(reply.text) > 50 else reply.text
    elif reply.photo:
        title = "[Фото]"
    elif reply.video:
        title = "[Видео]"
    elif reply.document:
        title = "[Документ]"
    elif reply.voice:
        title = "[Голосовое]"
    else:
        title = "Без названия"
    
    await state.update_data(
        source_chat_id=reply.chat.id,
        message_id=reply.message_id,
        title=title,
        post_type="forward"
    )
    
    await state.set_state(CreatePostStates.waiting_for_groups)
    
    groups = db.get_all_groups()
    if not groups:
        await message.answer("❌ Нет доступных групп. Добавьте бота в группы.")
        await state.clear()
        return
    
    for group in groups:
        group["is_selected"] = False
    
    await message.answer(
        "📢 Выберите группы для рассылки:",
        reply_markup=get_groups_list_keyboard(groups, 0, "select")
    )


@router.callback_query(
    CreatePostStates.waiting_for_groups,
    F.data.startswith("select_")
)
async def toggle_group_for_post(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    data_parts = callback.data.split("_")
    chat_id = int(data_parts[2])
    
    state_data = await state.get_data()
    selected_groups = state_data.get("selected_groups", [])
    
    if chat_id in selected_groups:
        selected_groups.remove(chat_id)
    else:
        selected_groups.append(chat_id)
    
    await state.update_data(selected_groups=selected_groups)
    
    groups = db.get_all_groups()
    for group in groups:
        group["is_selected"] = group["chat_id"] in selected_groups
    
    await callback.message.edit_text(
        "📢 Выберите группы для рассылки:",
        reply_markup=get_groups_list_keyboard(groups, 0, "select")
    )
    await callback.answer()


@router.callback_query(
    CreatePostStates.waiting_for_groups,
    F.data.startswith("done_create_groups_0")
)
async def done_groups_selection(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    state_data = await state.get_data()
    selected_groups = state_data.get("selected_groups", [])
    
    if not selected_groups:
        await callback.answer("❌ Выберите хотя бы одну группу.", show_alert=True)
        return
    
    await state.set_state(CreatePostStates.waiting_for_interval)
    
    await callback.message.edit_text(
        "🕒 Выберите интервал рассылки:",
        reply_markup=get_interval_keyboard(0, "create")
    )
    await callback.answer()


@router.callback_query(
    CreatePostStates.waiting_for_interval,
    F.data.startswith("create_interval_0_")
)
async def process_interval_for_post(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    interval = int(callback.data.split("_")[3])
    await state.update_data(interval=interval)
    
    await state.set_state(CreatePostStates.waiting_confirmation)
    
    state_data = await state.get_data()
    selected_groups = state_data.get("selected_groups", [])
    title = state_data.get("title", "Без названия")
    
    groups_text = []
    for chat_id in selected_groups:
        group = db.get_group(chat_id)
        if group:
            groups_text.append(f"• {group['title']}")
    
    text = (
        f"📝 Проверьте данные рассылки:\n\n"
        f"📌 Название: {title}\n"
        f"📤 Тип: forward\n"
        f"🕒 Интервал: {interval} минут\n"
        f"📢 Групп: {len(selected_groups)}\n\n"
        f"Список групп:\n" + "\n".join(groups_text) + "\n\n"
        f"Подтвердить создание?"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_confirm_keyboard("create", 0)
    )
    await callback.answer()


@router.callback_query(
    CreatePostStates.waiting_confirmation,
    F.data.startswith("confirm_create_0_")
)
async def confirm_create_post(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    state_data = await state.get_data()
    post_type = state_data.get("post_type", "forward")
    interval = state_data.get("interval")
    selected_groups = state_data.get("selected_groups", [])
    source_chat_id = state_data.get("source_chat_id")
    message_id = state_data.get("message_id")
    title = state_data.get("title", "Без названия")
    
    post_id = db.create_post(title, post_type, source_chat_id, message_id, interval)
    
    for chat_id in selected_groups:
        db.add_group_to_post(post_id, chat_id)
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Рассылка #{post_id} создана!\n\n"
        f"📌 Название: {title}\n"
        f"📤 Тип: forward\n"
        f"🕒 Интервал: {interval} минут\n"
        f"📢 Групп: {len(selected_groups)}",
        reply_markup=get_back_keyboard("back_to_list")
    )
    await callback.answer()


@router.callback_query(
    CreatePostStates.waiting_for_groups,
    F.data.startswith("cancel_create_0")
)
@router.callback_query(
    CreatePostStates.waiting_for_interval,
    F.data.startswith("cancel_create_0")
)
@router.callback_query(
    CreatePostStates.waiting_confirmation,
    F.data.startswith("cancel_create_0")
)
async def cancel_create_post(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await state.clear()
    await callback.message.edit_text("❌ Создание рассылки отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("post_"))
async def show_post_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[1])
    
    post_info = db.get_post_info(post_id)
    if not post_info:
        await callback.message.edit_text("❌ Рассылка не найдена.")
        await callback.answer()
        return
    
    groups = db.get_post_groups(post_id)
    groups_text = "\n".join([f"• {g['title']}" for g in groups]) if groups else "Нет групп"
    
    text = (
        f"📨 Рассылка #{post_id}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📌 Название: {post_info['title']}\n"
        f"📤 Тип: {post_info['type']}\n"
        f"⏱ Интервал: {post_info['interval']} минут\n"
        f"📊 Групп: {post_info['groups_count']}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📢 Список групп:\n{groups_text}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_post_detail_keyboard(post_id))
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    posts = db.get_all_posts()
    
    if not posts:
        await callback.message.edit_text("📭 Нет созданных рассылок.")
        return
    
    text = "📋 Список рассылок:\n\n"
    for post in posts:
        groups_count = db.get_post_groups_count(post["id"])
        text += f"{post['id']}. {post['title']} (групп: {groups_count})\n"
    
    await callback.message.edit_text(text, reply_markup=get_posts_list_keyboard(posts))
    await callback.answer()


@router.callback_query(F.data.startswith("add_group_"))
async def add_group_to_post(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    
    if not db.post_exists(post_id):
        await callback.message.edit_text("❌ Рассылка не найдена.")
        await callback.answer()
        return
    
    groups = db.get_groups_with_status(post_id)
    
    if not groups:
        await callback.message.edit_text("❌ Нет доступных групп.")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"📢 Выберите группы для добавления к рассылке #{post_id}:",
        reply_markup=get_groups_list_keyboard(groups, post_id, "add")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_group_"))
async def remove_group_from_post(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    
    if not db.post_exists(post_id):
        await callback.message.edit_text("❌ Рассылка не найдена.")
        await callback.answer()
        return
    
    groups = db.get_post_groups(post_id)
    
    if not groups:
        await callback.message.edit_text("❌ У этой рассылки нет групп.")
        await callback.answer()
        return
    
    for group in groups:
        group["is_selected"] = True
    
    await callback.message.edit_text(
        f"📢 Выберите группы для удаления из рассылки #{post_id}:",
        reply_markup=get_groups_list_keyboard(groups, post_id, "remove")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_") | F.data.startswith("remove_"))
async def toggle_group(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    data_parts = callback.data.split("_")
    action = data_parts[0]
    post_id = int(data_parts[1])
    chat_id = int(data_parts[2])
    
    if action == "add":
        db.add_group_to_post(post_id, chat_id)
    elif action == "remove":
        db.remove_group_from_post(post_id, chat_id)
    
    if action == "add":
        groups = db.get_groups_with_status(post_id)
    else:
        groups = db.get_post_groups(post_id)
        for group in groups:
            group["is_selected"] = True
    
    await callback.message.edit_text(
        f"✅ Группа {'добавлена' if action == 'add' else 'удалена'}!",
        reply_markup=get_groups_list_keyboard(groups, post_id, action)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("done_edit_groups_"))
async def done_groups(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[3])
    
    await callback.message.edit_text(
        "✅ Список групп обновлен!",
        reply_markup=get_back_keyboard(f"post_{post_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("change_interval_"))
async def change_interval(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    
    if not db.post_exists(post_id):
        await callback.message.edit_text("❌ Рассылка не найдена.")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"🕒 Выберите новый интервал для рассылки #{post_id}:",
        reply_markup=get_interval_keyboard(post_id, "edit")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_interval_"))
async def set_interval(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    data_parts = callback.data.split("_")
    post_id = int(data_parts[2])
    interval = int(data_parts[3])
    
    db.update_post_interval(post_id, interval)
    
    await callback.message.edit_text(
        f"✅ Интервал обновлен на {interval} минут!",
        reply_markup=get_back_keyboard(f"post_{post_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_post_"))
async def delete_post(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    
    if not db.post_exists(post_id):
        await callback.message.edit_text("❌ Рассылка не найдена.")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить рассылку #{post_id}?\n"
        f"Это действие невозможно отменить.",
        reply_markup=get_confirm_keyboard("delete", post_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_post(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    
    db.delete_post(post_id)
    
    await callback.message.edit_text(
        f"✅ Рассылка #{post_id} удалена!",
        reply_markup=get_back_keyboard("back_to_list")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_delete_"))
async def cancel_delete_post(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_edit_"))
async def cancel_edit_interval(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    post_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "❌ Изменение интервала отменено.",
        reply_markup=get_back_keyboard(f"post_{post_id}")
    )
    await callback.answer()


@router.message(F.new_chat_members)
async def bot_added_to_group(message: Message):
    for member in message.new_chat_members:
        if member.id == (await message.bot.me()).id:
            chat_id = message.chat.id
            title = message.chat.title or "Без названия"
            
            db.add_group(chat_id, title)
            await message.answer(f"✅ Бот добавлен в группу: {title}")


@router.message(F.left_chat_member)
async def bot_removed_from_group(message: Message):
    if message.left_chat_member.id == (await message.bot.me()).id:
        chat_id = message.chat.id
        
        group = db.get_group(chat_id)
        if group:
            title = group["title"]
            db.delete_group(chat_id)
            logger.info(f"Бот удален из группы: {title}")