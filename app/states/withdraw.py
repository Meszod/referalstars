from aiogram.fsm.state import State, StatesGroup


class WithdrawStates(StatesGroup):
    amount = State()
