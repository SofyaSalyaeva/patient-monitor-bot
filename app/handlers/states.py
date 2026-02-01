from aiogram.fsm.state import State, StatesGroup


class MedicationStates(StatesGroup):
    WAITING_NAMES = State()
    WAITING_TIMES = State()


class SurveyStates(StatesGroup):
    WAITING_DETAILS = State()


class DetailedSurveyState(StatesGroup):
    WAITING_TEXT = State()
