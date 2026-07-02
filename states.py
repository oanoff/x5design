from aiogram.fsm.state import State, StatesGroup

class SurveyStates(StatesGroup):
    answering = State()