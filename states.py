# states.py

from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_forward = State()
    waiting_confirm = State()


class SupportStates(StatesGroup):
    waiting_message = State()


class AdminStates(StatesGroup):
    waiting_admin_id = State()
    waiting_remove_admin = State()


class BanStates(StatesGroup):
    waiting_ban_id = State()
    waiting_unban_id = State()


class SettingsStates(StatesGroup):
    waiting_chat_id = State()
    waiting_channel_id = State()
    waiting_reserve_id = State()

    waiting_chat_cooldown = State()
    waiting_channel_cooldown = State()
    waiting_reserve_cooldown = State()

    waiting_support_cooldown = State()

    waiting_broadcast_delay = State()

    waiting_start_text = State()
    waiting_rules_text = State()

    waiting_start_photo = State()