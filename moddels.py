from aiogram.fsm.state import State, StatesGroup

class BroadcastStates(StatesGroup):
    """Состояния для рассылки"""
    waiting_for_message = State()  # Ожидание сообщения для рассылки
    confirm = State()               # Подтверждение отправки

class EditSettingStates(StatesGroup):
    """Состояния для редактирования настроек"""
    selecting_setting = State()     # Выбор настройки
    waiting_for_value = State()     # Ожидание нового значения