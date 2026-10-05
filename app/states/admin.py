from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    search_user = State()
    adjust_amount = State()
    broadcast_message = State()
    broadcast_confirm = State()
    channel_add = State()
    setting_value = State()
