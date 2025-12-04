import datetime
import os

import pymssql
from aiogram import Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from app import router
import app.keyboards as kb
import app.zakupki_info as zakupki
from app.inner_db import inner_db as idb
from app.states import Add
from app.email_service.rs_handlers import show_reports_menu
from app.search_system.search_system import search_in_database


dp = Dispatcher()


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ОСНОВНЫЕ КОМАНДЫ И ГЛАВНОЕ МЕНЮ
# ======================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👾Привет, {message.from_user.first_name}! Я бот для помощи стола заказов.",
        reply_markup=kb.main,
    )


@router.message(Command("quit"))
async def quit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌Отправка отменена")


@router.message(Command("reports"))
async def handle_reports_command(message: Message):
    """Команда для доступа к отчетам"""

    class MockCallback:
        def __init__(self, message):
            self.message = message

        async def answer(self, *args, **kwargs):
            pass

    mock_callback = MockCallback(message)
    await show_reports_menu(mock_callback)


@router.message(Command("d"))
async def search_dubbles_command(message: Message, db_connection: pymssql.Connection):
    """Обработчик команды /d для поиска дублей"""
    try:
        # Списки для сравнения
        LIST_1 = zakupki.dima
        LIST_2 = zakupki.dusya
        LIST_3 = zakupki.sashap
        LIST_4 = zakupki.kirill
        LIST_5 = zakupki.tanya
        LIST_6 = zakupki.ev
        LIST_7 = zakupki.yulya

        # Отправляем сообщение о начале поиска
        processing_msg = await message.answer("🔍 Ищу данные в базе...")

        # Выполняем запрос к базе данных
        cursor = db_connection.cursor(as_dict=True)
        query = """
        SELECT DISTINCT [Publisher_name]
        FROM [torgnew].[dbo].[nomen_bot]
        WHERE [code] IS NOT NULL
        ORDER BY [Publisher_name] ASC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        # Извлекаем значения из базы
        db_values = [row[0] for row in rows if row[0] is not None]

        if not db_values:
            await processing_msg.edit_text(
                "📭 В базе данных не найдено значений Publisher_name"
            )
            return

        # Значения которых нет ни в одном списке
        all_check_values = LIST_1 + LIST_2 + LIST_3 + LIST_4 + LIST_5 + LIST_6 + LIST_7
        completely_missing = [
            val for val in db_values if val not in all_check_values]

        # Формируем содержимое файла
        file_content = "РЕЗУЛЬТАТ СРАВНЕНИЯ БАЗЫ ДАННЫХ СО СПИСКАМИ\n"
        file_content += "=" * 50 + "\n\n"

        # Результаты сравнения
        file_content += "РЕЗУЛЬТАТЫ СРАВНЕНИЯ:\n\n"

        file_content += f"Отсутствуют во всех списках ({len(completely_missing)}):\n"
        for i, val in enumerate(completely_missing, 1):
            file_content += f"  {i}. {val}\n"
        file_content += "\n"

        # Создаем и отправляем файл
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparison_{timestamp}.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_content)

        file_to_send = FSInputFile(
            filename, filename="сравнение_издательств.txt")

        await message.answer_document(
            document=file_to_send,
            caption=f"📄 Результат сравнения\n"
            f"📊 Найдено: {len(db_values)} значений\n"
            f"🕒 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

        # Удаляем временный файл и сообщение о обработке
        os.remove(filename)
        await processing_msg.delete()

    except Exception as e:
        error_msg = f"❌ Ошибка: {e}"
        await message.answer(error_msg)


@router.message(Command("search"))
async def handle_search_command(message: Message, db_connection: pymssql.Connection):
    """Обработчик команды /search"""
    if len(message.text.split()) > 1:
        search_term = message.text.split(maxsplit=1)[1]
        await search_in_database(message, db_connection, search_term)
    else:
        await message.answer(
            "Введите поисковый запрос после команды /search\nНапример: /search Пушкин"
        )


@router.message(Command("history"))
async def handle_history_command(message: Message):
    class MockCallback:
        def __init__(self, message):
            self.message = message

        async def answer(self, *args, **kwargs):
            pass

    mock_callback = MockCallback(message)
    await idb.show_applications_history(mock_callback, page=0)


# ======================
# КОЛЛБЭКИ ГЛАВНОГО МЕНЮ И НАВИГАЦИИ
# ======================

@router.callback_query(lambda c: c.data == "main_menu")
async def callback_main_menu(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        f"👾 Привет, {callback_query.from_user.first_name}! Возвращаю в главное меню.",
        reply_markup=kb.main,
    )
    await callback_query.answer()


@router.callback_query(F.data == "add")
async def add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Add.new_request)
    await callback.answer("Новая заявка")
    await callback.message.edit_text(
        'Нажмите ⌨️"Ввести артикул", если книга есть в нашей базе,\nили 👋"Ввести название вручную", если книги у нас никогда не было',
        reply_markup=kb.req_q1,
    )


@router.callback_query(F.data == "reports_menu")
async def handle_reports_menu_callback(callback_query: CallbackQuery):
    """Обработчик кнопки Отчёты"""
    await show_reports_menu(callback_query)


@router.callback_query(F.data == "baza")  # Добавить выброс исключения на буквы
async def handle_search_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Add.baza_state1)
    await callback.message.edit_text(
        "🔍 Поиск товара по артикулу или названию\n\n"
        "Введите артикул или название товара:\n"
    )
    await callback.answer()
    await state.clear()
