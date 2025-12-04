import datetime

import pymssql
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)

from app.search_system.search_system import search_in_database, search_by_code
from app.search_system.ss_utils import handle_pagination_callback
from app import router


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ПОИСК ПО БАЗЕ - ВХОДНЫЕ ХЕНДЛЕРЫ
# ======================


@router.message(F.text.regexp(r"^\d{1,10}$"))
async def search_by_code_direct(message: Message,
                                db_connection: pymssql.Connection):
    """Обработчик прямого ввода кода товара (только цифры)"""
    code = message.text.strip()
    await search_in_database(message, db_connection, code)


@router.message(F.text.startswith("код:"))
async def search_by_code_prefix(message: Message,
                                db_connection: pymssql.Connection):
    """Обработчик ввода кода с префиксом 'код:'"""
    try:
        code = message.text.split(":", 1)[1].strip()
        if code:
            await search_in_database(message, db_connection, code)
        else:
            await message.answer("Пожалуйста, укажите код товара после 'код:'")
    except IndexError:
        await message.answer("Формат: код: <номер_кода>")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message, db_connection: pymssql.Connection):
    """Обработчик текстовых сообщений (не команд)"""
    search_term = message.text.strip()
    if search_term:
        await search_in_database(message, db_connection, search_term)
    else:
        await message.answer("Введите код товара или текст для поиска")


# ======================
# ПОИСК ПО БАЗЕ - ОБРАБОТЧИКИ РЕЗУЛЬТАТОВ
# ======================

@router.callback_query(F.data.startswith("search_by_code:"))
async def handle_search_by_code(callback: CallbackQuery, state: FSMContext):
    """Обработчик поиска по конкретному коду книги"""
    try:
        # Разбираем callback data
        # Формат: search_by_code:CODE:session_id:page
        parts = callback.data.split(":")
        if len(parts) >= 2:
            code = parts[1]

            # Отвечаем на callback чтобы убрать "часики"
            await callback.answer(f"🔍 Ищу товар с кодом {code}...")

            # Получаем данные из состояния
            data = await state.get_data()
            session_id = data.get("search_session_id", "default")

            # Сохраняем код для поиска в состояние
            await state.update_data(
                search_code=code,
                search_session_id=session_id,
                search_page=1,
                search_type="code"
            )

            # Вызываем функцию поиска по коду
            await search_by_code(callback.message, state, code)

    except Exception as e:
        await callback.answer("❌ Ошибка при поиске")
        print(f"Search by code error: {e}")


@router.callback_query(F.data.startswith("page_"))
async def handle_page_callback(
    callback: CallbackQuery, db_connection: pymssql.Connection
):
    """Обработчик переключения страниц"""
    await handle_pagination_callback(callback, db_connection)


@router.callback_query(F.data == "new_search")
async def handle_new_search_callback(callback: CallbackQuery):
    """Обработчик кнопки нового поиска"""
    await callback.message.answer("Введите текст для нового поиска:")
    await callback.answer()


@router.callback_query(F.data == "current_page")
async def handle_current_page_callback(callback: CallbackQuery):
    """Обработчик кнопки текущей страницы"""
    await callback.answer("Текущая страница")
