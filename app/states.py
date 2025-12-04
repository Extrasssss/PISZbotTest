from aiogram.fsm.state import State, StatesGroup


class ReportStates(StatesGroup):
    waiting_email = State()


class Add(StatesGroup):
    article = State()
    title = State()
    number = State()
    name = State()
    publisher = State()
    purchiser = State()
    comment = State()
    cont_q = State()
    approve = State()
    senders = State()
    neverbook = State()
    neverbook_number = State()
    neverbook_name = State()
    neverbook_senders = State()
    neverbook_comment = State()
    old_year_confirm = State()
    employee = State()
    neverbook_employee = State()
    new_request = State()
    baza_state1 = State()  # В поисковике
    baza_state2 = State()  # В заявке
