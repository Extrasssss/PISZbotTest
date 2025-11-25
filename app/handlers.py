import asyncio
import datetime
import hashlib
import os
import re
import time
from io import BytesIO

import Levenshtein
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pyodbc
from aiogram import Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

import app.keyboards as kb

import app.zakupki_info as zakupki
from app.email_service.report_service import (send_report_in_chat,
                                              send_report_to_email)
from app.inner_db import inner_db as idb
from app.inner_db.inner_db import applications_manager

router = Router()
dp = Dispatcher()


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


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


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👾Привет, {message.from_user.first_name}! Я бот для помощи стола заказов.",
        reply_markup=kb.main,
    )


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


@router.message(Command("tablica"))
async def tablica(message: Message):
    await message.answer("Таблица", reply_markup=kb.tablica)


@router.message(Command("quit"))
async def quit(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌Отправка отменена")


@router.callback_query(F.data == "add")
async def add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Add.new_request)
    await callback.answer("Новая заявка")
    await callback.message.edit_text(
        'Нажмите ⌨️"Ввести артикул", если книга есть в нашей базе,\nили 👋"Ввести название вручную", если книги у нас никогда не было',
        reply_markup=kb.req_q1,
    )


@router.callback_query(Add.new_request)
async def first(callback: CallbackQuery, state: FSMContext):
    if callback.data == "articool":
        await state.set_state(Add.article)
        await callback.message.edit_text("⌨️введите артикул")
    elif callback.data == "neverbook":
        await state.set_state(Add.neverbook)
        await callback.message.edit_text("✏️введите название")


@router.message(Add.neverbook)
async def n1(message: Message, state: FSMContext):
    await state.update_data(neverbook=message.text)
    await state.set_state(Add.neverbook_number)
    await message.answer("☎️Введите номер телефона")


@router.message(Add.article)
async def third(message: Message,
                state: FSMContext,
                db_connection: pyodbc.Connection):
    code = message.text.strip()
    try:
        #   Проверяем валидность кода
        if not code.isdigit():
            await message.answer("❗Код товара должен содержать только цифры🔢")
            return

        # Выполняем запрос к базе данных
        cursor = db_connection.cursor()
        query = """
        SELECT [remain],
        [code],
        [nomen_name],
        [binding_name],
        [sklad_name],
        [price],
        [author_name],
        [IsInoagent],
        [YearPublishing],
        [Publisher_name],
        [format_],
        [volume]
        FROM [torgnew].[dbo].[nomen_bot]
        WHERE [code] = ?
        """  # add [filepath]
        cursor.execute(query, code)
        rows = cursor.fetchall()

        if not rows:
            await message.answer(
                f"❌Товар с кодом '{code}' не найден\n Введите другой артикул:"
            )
            return

        # Формируем ответ
        response = ""

        row = rows[0]

        response += f"   • Артикул: `{row.code}`\n"
        response += f"   • Название: {row.nomen_name}\n"
        response += f"   • Издательство: {row.Publisher_name}\n"
        response += f"   • Год издания: {row.YearPublishing}\n"

        if row.IsInoagent == 1:
            response = f"❌НАСТОЯЩИЙ МАТЕРИАЛ (ИНФОРМАЦИЯ)❌\n❌ПРОИЗВЕДЕН ИНОСТРАННЫМ АГЕНТОМ,❌\n❌ЛИБО КАСАЕТСЯ ДЕЯТЕЛЬНОСТИ ИНОСТРАННОГО АГЕНТА❌\n❗❗❗КНИГА НЕ ДОСТУПНА ДЛЯ ПРОДАЖИ❗❗❗\n Введите другой артикул:"
            await message.answer(response)
            return

        if row.Publisher_name in zakupki.dima:
            response += f"   • Закупщик: Дима Николюк\n"
        if row.Publisher_name in zakupki.sashap:
            response += f"   • Закупщик: Саша Плотникова\n"
        if row.Publisher_name in zakupki.dusya:
            response += f"   • Закупщик: Дуся Никитина\n"
        if row.Publisher_name in zakupki.tanya:
            response += f"   • Закупщик: Таня Постоногова\n"
        if row.Publisher_name in zakupki.yulya:
            response += f"   • Закупщик: Юля Харитонова\n"
        if row.Publisher_name in zakupki.ev:
            response += f"   • Закупщик: Елена Владимировна\n"
        if row.Publisher_name in zakupki.kirill:
            response += f"   • Закупщик: Кирилл Прыскин\n"

        await state.update_data(article=response,
                                current_year=row.YearPublishing)
        await state.set_state(Add.approve)
        data = await state.get_data()
        await message.answer(
            f'вы искали эту позицию?\n{data["article"]}',
            reply_markup=kb.choise
        )

    except pyodbc.Error as e:
        await message.answer("❌ Ошибка при работе с базой данных")
        print(f"Database error: {e}")
    except Exception as e:
        await message.answer("❌ Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


@router.callback_query(F.data.in_(["yes",
                                   "no",
                                   "yes_old_year",
                                   "no_old_year"]))
async def handle_article_confirmation(callback: CallbackQuery,
                                      state: FSMContext):
    """Обработка подтверждения конкретного товара"""
    try:
        data = await state.get_data()

        if callback.data == "no":
            await clear_article_data(state)
            await callback.message.answer("⌨️Введите артикул:")

        elif callback.data == "yes":
            year_publishing = data.get("current_year")

            if year_publishing and year_publishing < 2020:
                await callback.message.answer(
                    f"📅 Внимание! Год издания {year_publishing}.\n"
                    f"Возможно у книги закончился тираж.\n"
                    f"Всё равно добавить эту позицию?",
                    reply_markup=kb.year_confirm_kb,
                )
            else:
                await add_book_to_list(state, data)
                await clear_article_data(state)
                await callback.message.answer(
                    "✅ Позиция добавлена!\nДобавить еще одну позицию?",
                    reply_markup=kb.continue_kb,  # Новая клавиатура для продолжения
                )

        elif callback.data == "yes_old_year":
            await add_book_to_list(state, data, is_old_year=True)
            await clear_article_data(state)
            await callback.message.answer(
                "✅ Позиция добавлена!\nДобавить еще одну позицию?",
                reply_markup=kb.continue_kb,  # Новая клавиатура для продолжения
            )

        elif callback.data == "no_old_year":
            await clear_article_data(state)
            await callback.message.answer("⌨️Введите артикул:")

        await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Ошибка при обработке")
        print(f"Error in handle_article_confirmation: {e}")
        await callback.answer()


@router.callback_query(F.data.in_(["continue_yes", "continue_no"]))
async def handle_continue_confirmation(callback: CallbackQuery,
                                       state: FSMContext):
    """Обработка подтверждения продолжения добавления товаров"""
    try:
        if callback.data == "continue_yes":
            # Начинаем новый цикл добавления
            await state.set_state(Add.article)
            await callback.message.answer("⌨️Введите артикул:")

        elif callback.data == "continue_no":
            # Завершаем добавление и переходим к следующему шагу
            await state.set_state(Add.number)
            await callback.message.answer("☎️Введите номер телефона")
            await callback.answer()

        await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Ошибка при обработке")
        print(f"Error in handle_continue_confirmation: {e}")
        await callback.answer()


async def clear_article_data(state):
    """Очищает данные о текущем товаре"""
    await state.update_data(current_year=None, article=None)


async def add_book_to_list(state, data, is_old_year=False):
    """Добавляет книгу в список"""
    article_text = data.get("article", "")
    year_publishing = data.get("current_year")

    if is_old_year and year_publishing:
        marked_article = f"🚨 СТАРОЕ ИЗДАНИЕ ({year_publishing}г.)\n{article_text}"
    else:
        marked_article = f"\n{article_text}"

    books = data.get("books", [])
    books.append(marked_article)
    await state.update_data(books=books)


@router.callback_query(Add.cont_q)
async def fourth(callback: CallbackQuery, state: FSMContext):
    if callback.data == "yes":
        await state.set_state(Add.article)
        # Вызываем следующую функцию, передавая необходимые параметры
        await callback.message.answer("⌨️Введите артикул:")
        await callback.answer()
    elif callback.data == "no":
        await state.set_state(Add.number)
        await callback.message.answer("☎️Введите номер телефона")
        await callback.answer()


@router.message(Add.number)
async def fifth(message: Message, state: FSMContext):
    phone = message.text.strip()

    # Проверяем точный формат без автоматических исправлений
    pattern1 = r"^\+7\d{10}$"  # +79990009900
    pattern2 = r"^8\d{10}$"  # 89990008899

    if re.match(pattern1, phone):
        # Номер в формате +79990009900 - сохраняем как есть
        await state.update_data(number=phone)
        await message.answer(f"✅ Номер сохранен: {phone}")
        await state.set_state(Add.name)
        await message.answer("введите Имя")
        return True
    elif re.match(pattern2, phone):
        # Номер в формате 89990008899 - конвертируем в +79990008899
        formatted_phone = "+7" + phone[1:]
        await state.update_data(number=formatted_phone)
        await message.answer(f"✅ Номер сохранен: {formatted_phone}")
        await state.set_state(Add.name)
        await message.answer("введите Имя")
        return True
    else:
        # Анализируем ошибку
        digits_only = re.sub(r"\D", "", phone)

        if len(digits_only) < 11:
            await message.answer(
                "❌ Слишком короткий номер телефона\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Должно быть ровно 11 цифр\n"
                "• Формат: +79990009900 или 89990008899\n\n"
                "📝 Введите номер еще раз:"
            )
        elif len(digits_only) > 11:
            await message.answer(
                "❌ Слишком длинный номер телефона\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Должно быть ровно 11 цифр\n"
                "• Уберите лишние цифры\n\n"
                "📝 Введите номер еще раз:"
            )
        else:
            await message.answer(
                "❌ Неверный формат номера\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Начинаться с +7 или 8\n"
                "• Затем 10 цифр\n"
                "• Без пробелов и других символов\n\n"
                "✅ Примеры:\n"
                "• +79990009900\n"
                "• 89990008899\n\n"
                "📝 Введите номер еще раз:"
            )
        return False


@router.message(Add.neverbook_number)
async def n2(message: Message, state: FSMContext):
    phone = message.text.strip()

    # Проверяем точный формат без автоматических исправлений
    pattern1 = r"^\+7\d{10}$"  # +79990009900
    pattern2 = r"^8\d{10}$"  # 89990008899

    if re.match(pattern1, phone):
        # Номер в формате +79990009900 - сохраняем как есть
        await state.update_data(number=phone)
        await message.answer(f"✅ Номер сохранен: {phone}")
        await state.set_state(Add.neverbook_name)
        await message.answer("введите Имя заказчика")
        return True
    elif re.match(pattern2, phone):
        # Номер в формате 89990008899 - конвертируем в +79990008899
        formatted_phone = "+7" + phone[1:]
        await state.update_data(number=formatted_phone)
        await message.answer(f"✅ Номер сохранен: {formatted_phone}")
        await state.set_state(Add.neverbook_name)
        await message.answer("🙋введите Имя заказчика🙋‍♂️")
        return True
    else:
        # Анализируем ошибку
        digits_only = re.sub(r"\D", "", phone)

        if len(digits_only) < 11:
            await message.answer(
                "❌ Слишком короткий номер телефона\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Должно быть ровно 11 цифр\n"
                "• Формат: +79990009900 или 89990008899\n\n"
                "📝 Введите номер еще раз:"
            )
        elif len(digits_only) > 11:
            await message.answer(
                "❌ Слишком длинный номер телефона\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Должно быть ровно 11 цифр\n"
                "• Уберите лишние цифры\n\n"
                "📝 Введите номер еще раз:"
            )
        else:
            await message.answer(
                "❌ Неверный формат номера\n\n"
                "🔍 Проверьте номер и введите заново ПРАВИЛЬНЫЙ номер:\n"
                "• Начинаться с +7 или 8\n"
                "• Затем 10 цифр\n"
                "• Без пробелов и других символов\n\n"
                "✅ Примеры:\n"
                "• +79990009900\n"
                "• 89990008899\n\n"
                "📝 Введите номер еще раз:"
            )
        return False


@router.message(Add.name)
async def sixth(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Add.senders)
    await message.answer(
        "❔Выберите отдел, который ожидает обработку заявки",
        reply_markup=kb.senders
    )


@router.message(Add.neverbook_name)
async def n3(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Add.neverbook_senders)
    await message.answer(
        "❔Выберите отдел, который ожидает обработку заявки",
        reply_markup=kb.senders
    )


@router.callback_query(Add.senders)
async def seven(callback: CallbackQuery, state: FSMContext):
    if callback.data == "TZ":
        sender = "🐕ТЗ"
    elif callback.data == "IM":
        sender = "🐈ИМ"
    await state.update_data(sender=sender)
    await state.set_state(Add.employee)
    await callback.message.answer("🐵Введите своё имя")


@router.callback_query(Add.neverbook_senders)
async def n4(callback: CallbackQuery, state: FSMContext):
    if callback.data == "TZ":
        sender = "🐕ТЗ"
    elif callback.data == "IM":
        sender = "🐈ИМ"
    await state.update_data(sender=sender)
    await state.set_state(Add.neverbook_employee)
    await callback.message.answer("🐵Введите своё имя")


@router.message(Add.employee)
async def precom(message: Message, state: FSMContext):
    await state.update_data(employee=message.text)
    await state.set_state(Add.comment)
    await message.answer("🏷️Комментарий")


@router.message(Add.neverbook_employee)
async def prencom(message: Message, state: FSMContext):
    await state.update_data(employee=message.text)
    await state.set_state(Add.neverbook_comment)
    await message.answer("🏷️Комментарий")


@router.message(Add.comment)
async def nineth(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    status = "Создана"
    p_comment = ""
    await state.update_data(status=status,
                            p_comment=p_comment)
    data = await state.get_data()
    books = data.get("books")
    rebooks = format_final_result(books)
    application_text = f'Заявка принята.\n   • Дата: {r_time}\n\n{rebooks}\n\n  • Контакты: {data["number"]}\n  • Имя: {data["name"]}\n  • Отдел: {data["sender"]}\n  • Сотрудник, внесший заявку:{data["employee"]}\n  • Комментарий: {data["comment"]}\n\n  • Комментарий от закупщика: {data["p_comment"]}\n\n • Статус заявки: {data["status"]}'

    # Сохраняем заявку в историю
    application_id = idb.applications_manager.save_application(
        application_text=application_text,
        comment=data["comment"],
        status=data["status"],
    )

    # Отправляем ответ пользователю
    await message.answer(application_text)

    # Добавляем кнопку для просмотра истории
    if application_id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Показать историю заявок",
                        callback_data="history:0"
                    )
                ]
            ]
        )
        await message.answer(
            f"✅ Заявка сохранена (ID: {application_id})", reply_markup=keyboard
        )

    await state.clear()


@router.message(Add.neverbook_comment)
async def n5(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    status = "Создана"
    p_comment = ""
    await state.update_data(status=status,
                            p_comment=p_comment)
    data = await state.get_data()
    application_text = f'Заявка принята.\n   • Дата: {r_time}\n\n📚Книга:\n   • {data["neverbook"]}\n\n  • Контакты: {data["number"]}\n  • Имя: {data["name"]}\n  • Отдел: {data["sender"]}\n  • Сотрудник, внесший заявку: {data["employee"]}\n  • Комментарий: {data["comment"]}\n\n  • Комментарий от закупщика: {data["p_comment"]}\n\n • Статус заявки: {data["status"]}'

    # Сохраняем заявку в историю
    application_id = idb.applications_manager.save_application(
        application_text=application_text,
        comment=data["comment"],
        status=data["status"],
    )

    # Отправляем ответ пользователю
    await message.answer(application_text)

    # Добавляем кнопку для просмотра истории
    if application_id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Показать историю заявок",
                        callback_data="history:0"
                    )
                ]
            ]
        )
        await message.answer(
            f"✅ Заявка сохранена (ID: {application_id})", reply_markup=keyboard
        )

    await state.clear()


# Обработчики истории, редактирования и удаления
@router.message(Command("history"))
async def handle_history_command(message: Message):
    class MockCallback:
        def __init__(self, message):
            self.message = message

        async def answer(self, *args, **kwargs):
            pass

    mock_callback = MockCallback(message)
    await idb.show_applications_history(mock_callback, page=0)


@router.callback_query(F.data.startswith("history:"))
async def handle_history_callback(callback_query: CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    await idb.show_applications_history(callback_query, page)


@router.callback_query(F.data.startswith("edit_page:"))
async def handle_edit_page_callback(callback_query: CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    await idb.show_edit_page(callback_query, page)


@router.callback_query(F.data.startswith("delete_page:"))
async def handle_delete_page_callback(callback_query: CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    await idb.show_delete_page(callback_query, page)


@router.callback_query(F.data.startswith("confirm_delete:"))
async def handle_confirm_delete_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    application_id = int(callback_query.data.split(":")[1])
    await idb.show_delete_confirmation(callback_query, state, application_id)


@router.callback_query(F.data.startswith("edit_application:"))
async def handle_edit_application_callback(callback_query: CallbackQuery):
    application_id = int(callback_query.data.split(":")[1])
    await idb.show_edit_options(callback_query, application_id)


@router.callback_query(F.data.startswith("edit_comment:"))
async def handle_edit_comment_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    application_id = int(callback_query.data.split(":")[1])
    await idb.start_edit_comment(callback_query, state, application_id)


@router.callback_query(F.data.startswith("edit_status:"))
async def handle_edit_status_callback(callback_query: CallbackQuery,
                                      state: FSMContext):
    application_id = int(callback_query.data.split(":")[1])
    await idb.start_edit_status(callback_query, state, application_id)


@router.callback_query(F.data.startswith("edit_contacts:"))
async def handle_edit_contacts_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    application_id = int(callback_query.data.split(":")[1])
    await idb.start_edit_contacts(callback_query, state, application_id)


@router.callback_query(F.data.startswith("edit_name:"))
async def handle_edit_name_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    application_id = int(callback_query.data.split(":")[1])
    await idb.start_edit_name(callback_query, state, application_id)


@router.callback_query(F.data.startswith("edit_purchaser_comment:"))
async def handle_edit_purchaser_comment_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    application_id = int(callback_query.data.split(":")[1])
    await idb.start_edit_purchaser_comment(callback_query, state, application_id)

# Обработчики состояний редактирования
@router.message(idb.EditStates.waiting_edit_comment)
async def handle_edit_comment_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового комментария"""
    try:
        data = await state.get_data()
        application_id = data.get("edit_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        new_comment = message.text.strip()

        if not new_comment:
            await message.answer("❌ Комментарий не может быть пустым")
            return

        # Обновляем в базе
        success = idb.applications_manager.update_comment(
            application_id, new_comment)

        if success:
            await message.answer(f"✅ Комментарий обновлен")

            # Показываем обновленную заявку
            application = idb.applications_manager.get_application_by_id(
                application_id)
            if application:
                response = f"🆔 ID: {application['id']}\n"
                response += application["application_text"]
                await message.answer(response)
        else:
            await message.answer("❌ Ошибка при обновлении комментария")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@router.message(idb.EditStates.waiting_edit_status)
async def handle_edit_status_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового статуса"""
    try:
        data = await state.get_data()
        application_id = data.get("edit_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        new_status = message.text.strip()

        if not new_status:
            await message.answer("❌ Статус не может быть пустым")
            return

        # Обновляем в базе
        success = idb.applications_manager.update_status(
            application_id, new_status)

        if success:
            await message.answer(f"✅ Статус обновлен на: {new_status}")

            # Показываем обновленную заявку
            application = idb.applications_manager.get_application_by_id(
                application_id)
            if application:
                response = f"🆔 ID: {application['id']}\n"
                response += application["application_text"]
                await message.answer(response)
        else:
            await message.answer("❌ Ошибка при обновлении статуса")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()

@router.message(idb.EditStates.waiting_edit_contacts)
async def handle_edit_contacts_input(message: Message, state: FSMContext):
    """Обрабатывает ввод новых контактов"""
    try:
        data = await state.get_data()
        application_id = data.get("edit_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        new_contacts = message.text.strip()

        if not new_contacts:
            await message.answer("❌ Контакты не могут быть пустыми")
            return

        # Обновляем в базе
        success = idb.applications_manager.update_contacts(
            application_id, new_contacts)

        if success:
            await message.answer(f"✅ Контакты обновлены")

            # Показываем обновленную заявку
            application = idb.applications_manager.get_application_by_id(
                application_id)
            if application:
                response = f"🆔 ID: {application['id']}\n"
                response += application["application_text"]
                await message.answer(response)
        else:
            await message.answer("❌ Ошибка при обновлении контактов")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@router.message(idb.EditStates.waiting_edit_name)
async def handle_edit_name_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового имени"""
    try:
        data = await state.get_data()
        application_id = data.get("edit_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        new_name = message.text.strip()

        if not new_name:
            await message.answer("❌ Имя не может быть пустым")
            return

        # Обновляем в базе
        success = idb.applications_manager.update_name(
            application_id, new_name)

        if success:
            await message.answer(f"✅ Имя обновлено")

            # Показываем обновленную заявку
            application = idb.applications_manager.get_application_by_id(
                application_id)
            if application:
                response = f"🆔 ID: {application['id']}\n"
                response += application["application_text"]
                await message.answer(response)
        else:
            await message.answer("❌ Ошибка при обновлении имени")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@router.message(idb.EditStates.waiting_edit_purchaser_comment)
async def handle_edit_purchaser_comment_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового комментария закупщика"""
    try:
        data = await state.get_data()
        application_id = data.get("edit_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        new_purchaser_comment = message.text.strip()

        # Комментарий закупщика может быть пустым, поэтому не проверяем на пустоту

        # Обновляем в базе
        success = idb.applications_manager.update_purchaser_comment(
            application_id, new_purchaser_comment)

        if success:
            await message.answer(f"✅ Комментарий закупщика обновлен")

            # Показываем обновленную заявку
            application = idb.applications_manager.get_application_by_id(
                application_id)
            if application:
                response = f"🆔 ID: {application['id']}\n"
                response += application["application_text"]
                await message.answer(response)
        else:
            await message.answer("❌ Ошибка при обновлении комментария закупщика")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


# Обработчик состояния удаления
@router.message(idb.DeleteStates.waiting_delete_confirmation)
async def handle_delete_confirmation(message: Message, state: FSMContext):
    """Обрабатывает второе подтверждение удаления"""
    try:
        data = await state.get_data()
        application_id = data.get("delete_application_id")

        if not application_id:
            await message.answer("❌ Ошибка: не найден ID заявки")
            await state.clear()
            return

        # Проверяем, что пользователь ввел правильный ID
        if not message.text.isdigit() or int(message.text) != application_id:
            await message.answer(
                f"❌ Неверный ID. Для подтверждения удаления введите: `{application_id}`\n\n"
                "Удаление отменено."
            )
            await state.clear()
            return

        # Удаляем заявку
        success = idb.applications_manager.delete_application(application_id)

        if success:
            await message.answer(
                f"✅ Заявка ID: {application_id} успешно удалена"
                )
        else:
            await message.answer(
                f"❌ Ошибка при удалении заявки ID: {application_id}"
                )

        await state.clear()

        # Показываем обновленную историю
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Показать историю", callback_data="history:0"
                    )
                ]
            ]
        )
        await message.answer("📋 История обновлена", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


def format_final_result(texts):
    """Форматирует список текстов в читаемый вид"""
    if not texts:
        return "Нет текстов"

    formatted = []
    for i, text in enumerate(texts, 1):
        formatted.append(f"📚Книга{i}. {text}")

    return "\n".join(formatted)


async def show_reports_menu(callback_query: CallbackQuery):
    """Показывает меню отчетов"""
    try:
        applications = applications_manager.get_all_applications()

        if not applications:
            await callback_query.message.answer("📝 Нет заявок для формирования отчета")
            await callback_query.answer()
            return

        response = "📊 Отчёты по заявкам\n\n"
        response += f"📦 Всего заявок в базе: {len(applications)}\n\n"
        response += "Выберите способ получения отчета:"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Получить в чате",
                        callback_data="report_in_chat"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📧 Получить на почту",
                        callback_data="report_by_email"
                    )
                ],
                [InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="history:0")],
            ]
        )

        await callback_query.message.edit_text(response, reply_markup=keyboard)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "reports_menu")
async def handle_reports_menu_callback(callback_query: CallbackQuery):
    """Обработчик кнопки Отчёты"""
    await show_reports_menu(callback_query)


@router.callback_query(F.data == "report_in_chat")
async def handle_report_in_chat_callback(callback_query: CallbackQuery):
    """Обработчик кнопки Получить в чате"""
    try:
        await callback_query.message.answer("📊 Формирую отчет...")
        # Передаем message из callback_query
        await send_report_in_chat(callback_query.message)
        await callback_query.answer()
    except Exception as e:
        await callback_query.message.answer(f"❌ Ошибка: {e}")
        await callback_query.answer()


@router.callback_query(F.data == "report_by_email")
async def handle_report_by_email_callback(
    callback_query: CallbackQuery, state: FSMContext
):
    """Обработчик кнопки Получить на почту"""
    try:
        await state.set_state(ReportStates.waiting_email)
        await callback_query.message.answer(
            "📧 Введите email адрес для отправки отчета:\n\n"
            "Пример: example@company.com"
        )
        await callback_query.answer()
    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(ReportStates.waiting_email)
async def handle_email_input(message: Message, state: FSMContext):
    """Обрабатывает ввод email для отправки отчета"""
    try:
        email = message.text.strip()

        # Простая валидация email
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            await message.answer(
                "❌ Неверный формат email. Пожалуйста, введите корректный email:\n\n"
                "Пример: example@company.com"
            )
            return

        await message.answer("📊 Формирую отчет и отправляю на email...")

        # Отправляем отчет на email
        success, result_message = await send_report_to_email(
            email=email,
            user_id=message.from_user.id,
            user_name=message.from_user.full_name,
        )

        if success:
            await message.answer(f"✅ {result_message}")
        else:
            await message.answer(f"❌ {result_message}")

        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке email: {e}")
        await state.clear()


async def send_loading_message(message: Message) -> Message:
    """Отправляет сообщение 'загрузка' и возвращает объект сообщения"""
    loading_msg = await message.answer("⏳ Загрузка...")
    return loading_msg


async def edit_loading_message(
    loading_msg: Message, final_text: str, reply_markup=None
):
    """Редактирует сообщение 'загрузка' на финальный текст"""
    try:
        await loading_msg.edit_text(final_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error editing loading message: {e}")


@router.callback_query(F.data == "baza")  # Добавить выброс исключения на буквы
async def handle_search_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Add.baza_state1)
    await callback.message.edit_text(
        "🔍 Поиск товара по артикулу или названию\n\n"
        "Введите артикул или название товара:\n"
    )
    await callback.answer()
    await state.clear()


@router.message(F.text.regexp(r"^\d{1,10}$"))
async def search_by_code_direct(message: Message,
                                db_connection: pyodbc.Connection):
    """Обработчик прямого ввода кода товара (только цифры)"""
    code = message.text.strip()
    await search_in_database(message, db_connection, code)


@router.message(F.text.startswith("код:"))
async def search_by_code_prefix(message: Message,
                                db_connection: pyodbc.Connection):
    """Обработчик ввода кода с префиксом 'код:'"""
    try:
        code = message.text.split(":", 1)[1].strip()
        if code:
            await search_in_database(message, db_connection, code)
        else:
            await message.answer("Пожалуйста, укажите код товара после 'код:'")
    except IndexError:
        await message.answer("Формат: код: <номер_кода>")


class SearchSession:
    def __init__(
        self,
        search_type: str,
        search_term: str,
        matched_codes: set = None,
        search_words: list = None,
        items_per_page: int = 5,
        total_count: int = 0,
    ):
        self.search_type = search_type  # 'code' или 'text'
        self.search_term = search_term
        self.matched_codes = matched_codes or set()
        self.search_words = search_words or []
        self.items_per_page = items_per_page
        self.total_count = total_count  # Добавляем total_count
        self.total_pages = (
            (total_count + items_per_page - 1) // items_per_page
            if items_per_page > 0
            else 1
        )  # Вычисляем total_pages
        self.created_time = time.time()
        self.user_id = None


def generate_session_id(user_id: int, search_term: str) -> str:
    """Генерация уникального ID сессии на основе пользователя и запроса"""
    unique_string = f"{user_id}_{search_term}_{time.time()}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:16]


def add_search_session(session_id: str, session: SearchSession, user_id: int):
    """Добавление сессии поиска"""
    session.user_id = user_id
    user_search_sessions[session_id] = session


def get_search_session(session_id: str) -> SearchSession:
    """Получение сессии поиска"""
    return user_search_sessions.get(session_id)


def get_user_sessions(user_id: int) -> dict:
    """Получение всех сессий пользователя"""
    return {
        session_id: session
        for session_id, session in user_search_sessions.items()
        if session.user_id == user_id
    }


def cleanup_old_sessions(hours: int = 1):
    """Очистка устаревших сессий поиска"""
    current_time = time.time()
    sessions_to_remove = []
    expiration_time = hours * 3600  # В секундах

    for session_id, session in user_search_sessions.items():
        if current_time - session.created_time > expiration_time:
            sessions_to_remove.append(session_id)

    for session_id in sessions_to_remove:
        del user_search_sessions[session_id]

    if sessions_to_remove:
        print(f"Очищено {len(sessions_to_remove)} устаревших сессий поиска")


async def start_periodic_cleanup():
    """Запуск периодической очистки сессий каждый час"""
    while True:
        await asyncio.sleep(3600)  # Ждем 1 час
        cleanup_old_sessions(1)
        print("Периодическая очистка сессий выполнена")


# Основные функции поиска (остаются без изменений, только обновляются вызовы)
async def search_in_database(
    message: Message, db_connection: pyodbc.Connection, search_term: str
):
    """Общая функция поиска в базе данных по коду или тексту"""
    loading_msg = None
    try:
        # Отправляем сообщение "загрузка"
        loading_msg = await send_loading_message(message)

        # Проверяем, является ли поисковый запрос числом
        if search_term.isdigit():
            await search_by_code(message,
                                 db_connection,
                                 search_term,
                                 loading_msg)
        else:
            await search_by_text(
                message,
                db_connection,
                search_term,
                page=1,
                loading_msg=loading_msg
            )

    except pyodbc.Error as e:
        if loading_msg:
            await edit_loading_message(
                loading_msg, "❌ Ошибка при работе с базой данных"
            )
        else:
            await message.answer("❌ Ошибка при работе с базой данных")
        print(f"Database error: {e}")
    except Exception as e:
        if loading_msg:
            await edit_loading_message(
                loading_msg, "❌ Произошла непредвиденная ошибка"
            )
        else:
            await message.answer("❌ Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


async def search_by_code(
    message: Message,
    db_connection: pyodbc.Connection,
    code: str,
    loading_msg: Message = None,
):
    """Поиск по коду товара"""
    try:
        cursor = db_connection.cursor()
        query = """
        SELECT [remain],
        [code],
        [nomen_name],
        [binding_name],
        [sklad_name],
        [price],
        [author_name],
        [IsInoagent],
        [YearPublishing],
        [Publisher_name],
        [format_],
        [volume],
        [filepath]
        FROM [torgnew].[dbo].[nomen_bot]
        WHERE [code] = ?
        """
        cursor.execute(query, code)
        rows = cursor.fetchall()

        if not rows:
            if loading_msg:
                await edit_loading_message(
                    loading_msg, f"Товар с кодом '{code}' не найден"
                )
            else:
                await message.answer(f"Товар с кодом '{code}' не найден")
            return

        # Сохраняем сессию поиска с новым ID
        session_id = generate_session_id(message.from_user.id, code)
        session = SearchSession(
            search_type="code",
            search_term=code,
            matched_codes={code},
            total_count=len(rows),  # Добавляем total_count
            items_per_page=5,
        )
        add_search_session(session_id, session, message.from_user.id)

        await send_search_results(
            message,
            rows,
            f"🔍 Результаты поиска по коду: {code}",
            session_id,
            page=1,
            loading_msg=loading_msg,
        )

    except Exception as e:
        if loading_msg:
            await edit_loading_message(loading_msg,
                                       "❌ Ошибка при поиске по коду")
        else:
            await message.answer("❌ Ошибка при поиске по коду")
        print(f"Search by code error: {e}")


async def search_by_text(
    message: Message,
    db_connection: pyodbc.Connection,
    search_text: str,
    page: int = 1,
    loading_msg: Message = None,
):
    """Поиск по тексту в названии и авторе с учетом опечаток и сортировкой по релевантности"""
    try:
        # Разбиваем поисковый запрос на слова
        search_words = [
            word.strip() for word in search_text.strip().split() if word.strip()
        ]
        if not search_words:
            if loading_msg:
                await edit_loading_message(loading_msg,
                                           "❌ Введите текст для поиска")
            else:
                await message.answer("❌ Введите текст для поиска")
            return

        cursor = db_connection.cursor()

        # Получаем все возможные товары для анализа
        all_products_query = """
        SELECT DISTINCT
        [code],
        [nomen_name],
        [author_name],
        COALESCE([nomen_name], '') as nomen_name_safe,
        COALESCE([author_name], '') as author_name_safe
        FROM [torgnew].[dbo].[nomen_bot]
        """
        cursor.execute(all_products_query)
        all_products = cursor.fetchall()

        # Собираем товары с оценкой релевантности
        scored_products = []

        for product in all_products:
            nomen_name = product.nomen_name_safe or ""
            author_name = product.author_name_safe or ""

            # Создаем полный текст для поиска
            full_text = f"{nomen_name} {author_name}".strip()

            if not full_text:
                continue

            # Вычисляем оценку релевантности
            match_score = calculate_match_score(full_text, search_words)

            # ПОВЫШАЕМ ПОРОГ для отсечения слабых совпадений
            if match_score > 0.4:
                scored_products.append(
                    {
                        "code": product.code,
                        "nomen_name": nomen_name,
                        "author_name": author_name,
                        "score": match_score,
                        "full_text": full_text,
                    }
                )

        if not scored_products:
            if loading_msg:
                await edit_loading_message(
                    loading_msg,
                    f"❌ По запросу '{search_text}' ничего не найдено"
                )
            else:
                await message.answer(
                    f"❌ По запросу '{search_text}' ничего не найдено")
            return

        # Сортируем по убыванию релевантности
        scored_products.sort(key=lambda x: x["score"], reverse=True)

        # Ограничиваем количество результатов (например, 50 самых релевантных)
        scored_products = scored_products[:50]

        # Берем только коды товаров
        matched_codes = {product["code"] for product in scored_products}

        # Сохраняем сессию поиска
        session_id = generate_session_id(message.from_user.id, search_text)
        session = SearchSession(
            search_type="text",
            search_term=search_text,
            matched_codes=matched_codes,
            search_words=search_words,
            total_count=len(scored_products),  # Добавляем total_count
            items_per_page=5,
        )
        add_search_session(session_id, session, message.from_user.id)

        # Получаем данные для текущей страницы
        await get_search_results_page(
            message,
            db_connection,
            session_id,
            page,
            scored_products,
            loading_msg
        )

    except Exception as e:
        if loading_msg:
            await edit_loading_message(loading_msg,
                                       "❌ Ошибка при текстовом поиске")
        else:
            await message.answer("❌ Ошибка при текстовом поиске")
        print(f"Text search error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


async def send_text_search_results(
    message: Message,
    rows: list,
    search_text: str,
    page: int,
    total_count: int,
    items_per_page: int,
    session_id: str,
    scored_products: list = None,
    loading_msg: Message = None,
):
    """Отправка результатов текстового поиска с пагинацией и указанием релевантности"""
    try:
        # Группируем результаты по коду товара
        products = {}
        for row in rows:
            code = row.code
            if code not in products:
                products[code] = []
            products[code].append(row)

        total_pages = (total_count + items_per_page - 1) // items_per_page

        response = f"🔍 Результаты поиска: '{search_text}'\n"
        response += f"📊 Найдено товаров: {total_count}\n"
        response += f"📄 Страница {page} из {total_pages}\n"
        response += f"🎯 (отсортировано по релевантности)\n\n"

        for i, (code, product_rows) in enumerate(products.items(), 1):
            first_row = product_rows[0]

            # Находим оценку релевантности для этого товара
            relevance_score = 0
            if scored_products:
                for scored_product in scored_products:
                    if scored_product["code"] == code:
                        relevance_score = scored_product["score"]
                        break

            # Создаем визуальный индикатор релевантности
            relevance_indicator = "🔴"
            if relevance_score > 0.7:
                relevance_indicator = "🟢"
            elif relevance_score > 0.4:
                relevance_indicator = "🟡"
            elif relevance_score > 0.2:
                relevance_indicator = "🟠"

            response += f"**{i + (page-1)*items_per_page}. {relevance_indicator} Код: `{code}`**\n"
            response += f"   • Название: {first_row.nomen_name or 'Не указано'}\n"
            response += f"   • Автор: {first_row.author_name or 'Не указан'}\n"
            response += (
                f"   • Издательство: {first_row.Publisher_name or 'Не указано'}\n"
            )
            response += f"   • Год издания: {first_row.YearPublishing or 'Не указан'}\n"
            response += f"   • Цена: {first_row.price or 'Не указана'} руб.\n"

            # Показываем склады для этого товара
            for j, row in enumerate(product_rows, 1):
                response += f"   📦 Склад{j}: {row.sklad_name or 'Не указан'}\n"
                response += f"   • Количество: **{row.remain or 0}** шт.\n"
                if j < len(product_rows):
                    response += "   ─────────────────\n"

            if i < len(products):
                response += "\n" + "=" * 50 + "\n\n"

        # Создаем клавиатуру пагинации
        keyboard = create_pagination_keyboard(session_id, page, total_pages)

        if loading_msg:
            await edit_loading_message(loading_msg,
                                       response,
                                       reply_markup=keyboard)
        else:
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        if loading_msg:
            await edit_loading_message(
                loading_msg, "❌ Ошибка при формировании результатов поиска"
            )
        else:
            await message.answer("❌ Ошибка при формировании результатов поиска")
        print(f"Results formatting error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


def create_pagination_keyboard(
    session_id: str, current_page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """Создание клавиатуры для пагинации"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    row = []

    # Кнопка "Назад"
    if current_page > 1:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"page_{session_id}_{current_page-1}"
            )
        )

    # Информация о странице
    row.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}", callback_data="current_page"
        )
    )

    # Кнопка "Вперед"
    if current_page < total_pages:
        row.append(
            InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"page_{session_id}_{current_page+1}"
            )
        )

    keyboard.inline_keyboard.append(row)

    # Кнопка для нового поиска
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="🔄 Новый поиск",
                              callback_data="new_search")]
    )

    return keyboard


async def send_search_results(
    message: Message,
    rows: list,
    title: str,
    session_id: str,
    page: int = 1,
    loading_msg: Message = None,
):
    """Отправка результатов поиска (общая функция для кода и текста)"""
    try:
        # Группируем результаты по коду товара
        products = {}
        for row in rows:
            code = row.code
            if code not in products:
                products[code] = []
            products[code].append(row)

        response = f"{title}\n\n"

        for code, product_rows in products.items():
            first_row = product_rows[0]
            response += f"   • Код: `{first_row.code}`\n"
            response += f"   • Название: {first_row.nomen_name or 'Не указано'}\n"
            response += f"   • Автор: {first_row.author_name or 'Не указан'}\n"
            response += (
                f"   • Издательство: {first_row.Publisher_name or 'Не указано'}\n"
            )
            response += f"   • Год издания: {first_row.YearPublishing or 'Не указан'}\n"
            response += f"   • Обложка: {first_row.binding_name or 'Не указана'}\n"
            response += f"   • Формат: {first_row.format_ or 'Не указан'}\n"
            response += f"   • Объем: {first_row.volume or 'Не указан'} стр.\n"
            response += f"   • Цена: {first_row.price or 'Не указана'}\n\n"

            for i, row in enumerate(product_rows, 1):
                response += f"   📦 Склад{i}: {row.sklad_name or 'Не указан'}\n"
                response += f"   • Количество{i}: **{row.remain or 0}** шт.\n"
                if i < len(product_rows):
                    response += "   ─────────────────\n"

            response += "\n" + "=" * 50 + "\n\n"

        if row.IsInoagent == 1:
            response = f"❌НАСТОЯЩИЙ МАТЕРИАЛ (ИНФОРМАЦИЯ)❌\n❌ПРОИЗВЕДЕН ИНОСТРАННЫМ АГЕНТОМ,❌\n❌ЛИБО КАСАЕТСЯ ДЕЯТЕЛЬНОСТИ ИНОСТРАННОГО АГЕНТА❌\n❗❗❗КНИГА НЕ ДОСТУПНА ДЛЯ ПРОДАЖИ❗❗❗\n Введите другой артикул:"
            await message.answer(response)
            return

        # Остальной код без изменений...
        media_files = []

        if first_row.filepath:
            book_image_path = get_book_image_path(first_row.filepath)
            if book_image_path and os.path.exists(book_image_path):
                try:
                    book_photo = FSInputFile(book_image_path)
                    media_files.append(book_photo)
                except Exception as e:
                    print(f"Error loading book image: {e}")

        # Добавляем изображение сравнения форматов если есть формат
        if first_row.format_:
            format_image_buffer = create_format_comparison_image(
                first_row.format_)
            if format_image_buffer:
                format_photo = BufferedInputFile(
                    format_image_buffer.getvalue(),
                    filename="format_comparison.png"
                )
                media_files.append(format_photo)

        # Создаем клавиатуру пагинации (если есть несколько страниц)
        session = get_search_session(session_id)
        keyboard = None
        if session and session.total_pages > 1:
            keyboard = create_pagination_keyboard(
                session_id, page, session.total_pages)

        # Отправляем сообщение с изображениями
        if media_files:
            if len(media_files) == 1:
                if loading_msg:
                    # Удаляем сообщение "загрузка" и отправляем фото
                    await loading_msg.delete()
                    await message.answer_photo(
                        photo=media_files[0], caption=response,
                        reply_markup=keyboard
                    )
                else:
                    await message.answer_photo(
                        photo=media_files[0],
                        caption=response,
                        reply_markup=keyboard
                    )
            else:
                media_group = []
                for i, media_file in enumerate(media_files):
                    if i == 0:
                        media_group.append(
                            InputMediaPhoto(media=media_file, caption=response)
                        )
                    else:
                        media_group.append(InputMediaPhoto(media=media_file))

                if loading_msg:
                    # Удаляем сообщение "загрузка" и отправляем медиагруппу
                    await loading_msg.delete()
                    await message.answer_media_group(media=media_group)
                    if keyboard:
                        await message.answer("Навигация:",
                                             reply_markup=keyboard)
                else:
                    await message.answer_media_group(media=media_group)
                    if keyboard:
                        await message.answer("Навигация:",
                                             reply_markup=keyboard)
        else:
            # Если нет изображений, отправляем только текст
            if loading_msg:
                await edit_loading_message(loading_msg,
                                           response,
                                           reply_markup=keyboard)
            else:
                await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        if loading_msg:
            await edit_loading_message(
                loading_msg, "❌ Ошибка при отправке результатов"
            )
        else:
            await message.answer("❌ Ошибка при отправке результатов")
        print(f"Send results error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


# Обработчик для кнопок пагинации
async def handle_pagination_callback(
    callback_query: CallbackQuery, db_connection: pyodbc.Connection
):
    """Обработка нажатий на кнопки пагинации"""
    loading_msg = None
    try:
        data = callback_query.data

        if data.startswith("page_"):
            parts = data.split("_")
            if len(parts) >= 3:
                session_id = parts[1]
                new_page = int(parts[2])

                # Отправляем сообщение "загрузка"
                loading_msg = await send_loading_message(
                    callback_query.message
                    )

                # Получаем сессию поиска
                session = get_search_session(session_id)
                if not session:
                    # Пытаемся найти последнюю сессию пользователя
                    user_sessions = get_user_sessions(
                        callback_query.from_user.id)
                    if user_sessions:
                        # Берем последнюю сессию пользователя
                        session_id, session = list(user_sessions.items())[-1]
                        print(
                            f"Используем последнюю сессию пользователя: {session_id}")
                    else:
                        if loading_msg:
                            await edit_loading_message(
                                loading_msg,
                                "❌ Сессия поиска устарела. Начните новый поиск.",
                            )
                        else:
                            await callback_query.answer(
                                "❌ Сессия поиска устарела. Начните новый поиск."
                            )
                        return

                # Удаляем старое сообщение (опционально)
                try:
                    await callback_query.message.delete()
                except:
                    pass  # Игнорируем ошибки удаления

                # Выполняем поиск с новой страницей
                if session.search_type == "code":
                    # Для поиска по коду просто показываем результаты
                    await get_search_results_page(
                        callback_query.message,
                        db_connection,
                        session_id,
                        new_page,
                        loading_msg=loading_msg,
                    )
                else:
                    # Для текстового поиска выполняем запрос с новой страницей
                    await search_by_text(
                        callback_query.message,
                        db_connection,
                        session.search_term,
                        new_page,
                        loading_msg,
                    )

                await callback_query.answer(f"Страница {new_page}")

    except Exception as e:
        if loading_msg:
            await edit_loading_message(
                loading_msg, "❌ Ошибка при переключении страницы"
            )
        else:
            await callback_query.answer("❌ Ошибка при переключении страницы")
        print(f"Pagination error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


def get_book_image_path(filepath: str) -> str:
    """Преобразует путь из базы данных в полный путь к файлу"""
    try:
        if not filepath or not isinstance(filepath, str):
            return None

        # Очищаем путь от лишних символов
        clean_path = filepath.strip().replace('"', "").replace("'", "")

        # Базовый путь к папке с изображениями (настройте под вашу структуру)
        base_image_path = "C:\\Path\\To\\Images\\"  # Замените на актуальный путь

        # Формируем полный путь
        full_path = os.path.join(base_image_path, clean_path)

        # Проверяем существование файла
        if os.path.exists(full_path):
            return full_path
        else:
            print(f"Image file not found: {full_path}")
            return None

    except Exception as e:
        print(f"Error getting book image path: {e}")
        return None


def create_format_comparison_image(book_format: str):
    """Создает изображение с наложением форматов (стандартный сверху)"""
    try:
        # Стандартный формат для сравнения
        STANDARD_FORMAT = "115x180"

        # Парсим форматы
        book_width, book_height = parse_format(book_format)
        standard_width, standard_height = parse_format(STANDARD_FORMAT)

        if book_width is None or book_height is None:
            return None

        # Создаем одну фигуру
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))

        # Масштабируем для лучшего отображения
        max_dim = max(book_width, book_height, standard_width, standard_height)
        scale = 300 / max_dim

        book_w_scaled = book_width * scale
        book_h_scaled = book_height * scale
        std_w_scaled = standard_width * scale
        std_h_scaled = standard_height * scale

        # Сначала рисуем книжный формат (как фон)
        rect_book = patches.Rectangle(
            (0, 0),
            book_w_scaled,
            book_h_scaled,
            linewidth=4,
            edgecolor="#A23B72",
            facecolor="#F18FBC",
            alpha=0.7,
        )
        ax.add_patch(rect_book)

        # Затем рисуем стандартный формат поверх книжного
        rect_std = patches.Rectangle(
            (0, 0),
            std_w_scaled,
            std_h_scaled,
            linewidth=4,
            edgecolor="#2E86AB",
            facecolor="#A9D6E5",
            alpha=0.8,
        )
        ax.add_patch(rect_std)

        # Настраиваем оси
        max_width = max(book_w_scaled, std_w_scaled)
        max_height = max(book_h_scaled, std_h_scaled)
        ax.set_xlim(0, max_width + 50)
        ax.set_ylim(0, max_height + 50)
        ax.set_aspect("equal")

        # Добавляем подписи размеров для стандартного формата (сверху)
        ax.text(
            std_w_scaled / 2,
            std_h_scaled + 15,
            f"{standard_width}×{standard_height} мм",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color="#2E86AB",
        )
        ax.text(
            std_w_scaled / 2,
            std_h_scaled + 5,
            "стандартный покет АСТ",
            ha="center",
            va="bottom",
            fontsize=12,
            color="#2E86AB",
            style="italic",
        )

        # Добавляем подписи размеров для книжного формата
        ax.text(
            book_w_scaled / 2,
            book_h_scaled + 30,
            f"{book_width}×{book_height} мм",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color="#A23B72",
        )
        ax.text(
            book_w_scaled / 2,
            book_h_scaled + 20,
            "ваша книга",
            ha="center",
            va="bottom",
            fontsize=12,
            color="#A23B72",
            style="italic",
        )

        # Убираем оси
        ax.set_xticks([])
        ax.set_yticks([])

        # Убираем рамку
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        plt.tight_layout()

        # Сохраняем в буфер
        buffer = BytesIO()
        plt.savefig(
            buffer,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
            pad_inches=0.1,
        )
        buffer.seek(0)
        plt.close()

        return buffer

    except Exception as e:
        print(f"Error creating format comparison image: {e}")
        plt.close()
        return None


def parse_format(format_str: str):
    """Парсит строку формата в ширину и высоту"""
    try:
        # Убираем пробелы и приводим к нижнему регистру
        format_str = format_str.strip().lower()

        # Разные варианты разделителей
        separators = ["x", "х", "*", "×", " "]

        for sep in separators:
            if sep in format_str:
                parts = format_str.split(sep)
                if len(parts) == 2:
                    # Извлекаем числа из строки
                    width = extract_number(parts[0])
                    height = extract_number(parts[1])
                    if width and height:
                        return width, height

        # Если не нашли разделитель, пробуем извлечь два числа подряд
        numbers = extract_all_numbers(format_str)
        if len(numbers) >= 2:
            return numbers[0], numbers[1]

        return None, None

    except Exception as e:
        print(f"Error parsing format {format_str}: {e}")
        return None, None


def extract_number(text: str):
    """Извлекает первое число из текста"""
    import re

    numbers = re.findall(r"\d+", text)
    return int(numbers[0]) if numbers else None


def extract_all_numbers(text: str):
    """Извлекает все числа из текста"""
    import re

    numbers = re.findall(r"\d+", text)
    return [int(num) for num in numbers]


@router.message(Command("d"))
async def search_dubbles_command(message: Message, db_connection: pyodbc.Connection):
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
        cursor = db_connection.cursor()
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
async def handle_search_command(message: Message, db_connection: pyodbc.Connection):
    """Обработчик команды /search"""
    if len(message.text.split()) > 1:
        search_term = message.text.split(maxsplit=1)[1]
        await search_in_database(message, db_connection, search_term)
    else:
        await message.answer(
            "Введите поисковый запрос после команды /search\nНапример: /search Пушкин"
        )


# Обработчик текстовых сообщений
@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message, db_connection: pyodbc.Connection):
    """Обработчик текстовых сообщений (не команд)"""
    search_term = message.text.strip()
    if search_term:
        await search_in_database(message, db_connection, search_term)
    else:
        await message.answer("Введите код товара или текст для поиска")


# Обработчики callback-запросов для пагинации
@router.callback_query(F.data.startswith("page_"))
async def handle_page_callback(
    callback: CallbackQuery, db_connection: pyodbc.Connection
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


def calculate_match_score(product_text: str, search_words: list) -> float:
    """
    Вычисляет оценку совпадения товара с поисковым запросом
    Возвращает значение от 0 до 1, где 1 - полное совпадение
    """
    if not product_text or not search_words:
        return 0.0

    product_text_lower = product_text.lower()
    total_score = 0.0
    matched_words = 0

    for search_word in search_words:
        search_word_lower = search_word.lower()
        max_word_score = 0.0

        # Разбиваем текст товара на слова
        product_words = product_text_lower.split()

        for product_word in product_words:
            if not product_word:
                continue

            # 1. Проверяем точное совпадение (максимальный балл)
            if search_word_lower == product_word:
                max_word_score = 1.0
                break  # Прерываем, так как нашли точное совпадение

            # 2. Проверяем вхождение слова (только если слова достаточно длинные)
            if len(search_word_lower) >= 4 and len(product_word) >= 4:
                if (
                    search_word_lower in product_word
                    or product_word in search_word_lower
                ):
                    overlap_ratio = len(search_word_lower) / max(
                        len(product_word), len(search_word_lower)
                    )
                    # Только для достаточно хороших совпадений
                    if overlap_ratio >= 0.7:
                        max_word_score = max(
                            max_word_score, 0.8 * overlap_ratio)
                        continue

            # 3. Проверяем схожесть по Левенштейну (только для слов достаточной длины)
            if len(search_word_lower) >= 3 and len(product_word) >= 3:
                distance = Levenshtein.distance(
                    search_word_lower, product_word)
                max_len = max(len(search_word_lower), len(product_word))

                if max_len > 0:
                    similarity = 1 - distance / max_len
                    # Повышаем порог схожести и учитываем только достаточно похожие слова
                    if similarity >= 0.8:  # Повышен порог с 0.6 до 0.8
                        max_word_score = max(
                            max_word_score, similarity * 0.6
                        )  # Понижен вес

            # 4. Дополнительные баллы за частичные совпадения букв (только для длинных слов)
            if len(search_word_lower) >= 5 and max_word_score < 0.3:
                # Считаем количество совпадающих букв в правильном порядке
                common_letters = 0
                search_idx = 0

                for (
                    char
                ) in product_word:  # Ищем только в текущем слове, а не во всем тексте
                    if (
                        search_idx < len(search_word_lower)
                        and char == search_word_lower[search_idx]
                    ):
                        common_letters += 1
                        search_idx += 1

                if len(search_word_lower) > 0:
                    letter_match_ratio = common_letters / \
                        len(search_word_lower)
                    # Повышаем порог для учета частичного совпадения
                    if letter_match_ratio >= 0.6:  # Повышен порог с 0.3 до 0.6
                        max_word_score = max(
                            max_word_score, letter_match_ratio * 0.4
                        )  # Понижен вес

        # Учитываем только слова с достаточным уровнем совпадения
        if max_word_score >= 0.3:  # Минимальный порог для учета слова
            total_score += max_word_score
            matched_words += 1

    # Если ни одно слово не совпало достаточно хорошо, возвращаем 0
    if matched_words == 0:
        return 0.0

    # Нормализуем оценку относительно количества поисковых слов
    base_score = total_score / len(search_words)

    # Дополнительный бонус за количество совпавших слов
    word_coverage = matched_words / len(search_words)

    # Итоговая оценка: 70% за качество совпадений + 30% за покрытие слов
    final_score = (base_score * 0.7) + (word_coverage * 0.3)

    return final_score


async def get_search_results_page(
    message: Message,
    db_connection: pyodbc.Connection,
    session_id: str,
    page: int = 1,
    pre_scored_products: list = None,
    loading_msg: Message = None,
):
    """Получение результатов поиска для конкретной страницы с сортировкой по релевантности"""
    session = get_search_session(session_id)
    if not session:
        if loading_msg:
            await edit_loading_message(loading_msg, "❌ Сессия поиска устарела")
        else:
            await message.answer("❌ Сессия поиска устарела")
        return

    cursor = db_connection.cursor()
    items_per_page = session.items_per_page
    offset = (page - 1) * items_per_page

    if pre_scored_products:
        # Используем предварительно отсортированные товары
        sorted_products = pre_scored_products
    else:
        # Получаем и сортируем товары заново
        codes_placeholder = ",".join(["?" for _ in session.matched_codes])

        # Сначала получаем базовые данные товаров
        base_query = f"""
        SELECT
        [code],
        COALESCE([nomen_name], '') as nomen_name,
        COALESCE([author_name], '') as author_name
        FROM [torgnew].[dbo].[nomen_bot]
        WHERE [code] IN ({codes_placeholder})
        """
        cursor.execute(base_query, list(session.matched_codes))
        base_products = cursor.fetchall()

        # Вычисляем оценки релевантности
        sorted_products = []
        for product in base_products:
            full_text = f"{product.nomen_name} {product.author_name}".strip()
            score = calculate_match_score(full_text, session.search_words)
            sorted_products.append(
                {
                    "code": product.code,
                    "nomen_name": product.nomen_name,
                    "author_name": product.author_name,
                    "score": score,
                    "full_text": full_text,
                }
            )

        # Сортируем по убыванию релевантности
        sorted_products.sort(key=lambda x: x["score"], reverse=True)

    # Получаем полные данные для товаров текущей страницы
    page_codes = [
        product["code"] for product in sorted_products[offset: offset + items_per_page]
    ]

    if not page_codes:
        if loading_msg:
            await edit_loading_message(loading_msg, "❌ Нет данных для отображения")
        else:
            await message.answer("❌ Нет данных для отображения")
        return

    # Упрощенный запрос без сложного ORDER BY
    codes_placeholder = ",".join(["?" for _ in page_codes])

    data_query = f"""
    SELECT [remain],
    [code],
    [nomen_name],
    [binding_name],
    [sklad_name],
    [price],
    [author_name],
    [IsInoagent],
    [YearPublishing],
    [Publisher_name],
    [format_],
    [volume],
    [filepath]
    FROM [torgnew].[dbo].[nomen_bot]
    WHERE [code] IN ({codes_placeholder})
    """

    cursor.execute(data_query, list(page_codes))
    rows = cursor.fetchall()

    # Сортируем результаты в Python согласно нашему порядку
    code_to_row = {row.code: row for row in rows}
    sorted_rows = []
    for code in page_codes:
        if code in code_to_row:
            sorted_rows.append(code_to_row[code])

    # Обновляем сессию с актуальным total_count
    session.total_count = len(sorted_products)
    session.total_pages = (
        session.total_count + session.items_per_page - 1
    ) // session.items_per_page

    await send_text_search_results(
        message,
        sorted_rows,
        session.search_term,
        page,
        session.total_count,
        items_per_page,
        session_id,
        sorted_products[offset: offset + items_per_page],
        loading_msg,
    )
