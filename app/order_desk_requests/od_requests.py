import asyncio
import datetime
import re

from aiogram import Bot
from datetime import timedelta

import pymssql
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import app.keyboards as kb

import app.zakupki_info as zakupki
from app.inner_db import inner_db as idb
from app.states import Add
from app import router


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ДОБАВЛЕНИЕ ЗАЯВКИ - ОСНОВНОЙ ПОТОК (С АРТИКУЛОМ)
# ======================

@router.callback_query(Add.new_request)
async def first(callback: CallbackQuery, state: FSMContext):
    if callback.data == "articool":
        await state.set_state(Add.article)
        await callback.message.edit_text("⌨️Введите артикул")
    elif callback.data == "neverbook":
        await state.set_state(Add.neverbook)
        await callback.message.edit_text("✏️Введите название")


@router.message(Add.article)
async def third(message: Message,
                state: FSMContext,
                db_connection: pymssql.Connection):
    code = message.text.strip()
    try:
        #   Проверяем валидность кода
        if not code.isdigit():
            await message.answer("❗Код товара должен содержать только цифры🔢")
            return

        # Выполняем запрос к базе данных
        cursor = db_connection.cursor(as_dict=True)
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
        WHERE [code] = %s
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

        response += f"   • Артикул: `{row['code']}`\n"
        response += f"   • Название: {row['nomen_name']}\n"
        response += f"   • Издательство: {row['Publisher_name']}\n"
        response += f"   • Год издания: {row['YearPublishing']}\n"

        if row['IsInoagent'] == 1:
            response = f"❌НАСТОЯЩИЙ МАТЕРИАЛ (ИНФОРМАЦИЯ)❌\n❌ПРОИЗВЕДЕН ИНОСТРАННЫМ АГЕНТОМ,❌\n❌ЛИБО КАСАЕТСЯ ДЕЯТЕЛЬНОСТИ ИНОСТРАННОГО АГЕНТА❌\n❗❗❗КНИГА НЕ ДОСТУПНА ДЛЯ ПРОДАЖИ❗❗❗\n Введите другой артикул:"
            await message.answer(response)
            return

        if row['Publisher_name'] in zakupki.dima:
            response += f"   • Закупщик: Дима Николюк\n"
        if row['Publisher_name'] in zakupki.sashap:
            response += f"   • Закупщик: Саша Плотникова\n"
        if row['Publisher_name'] in zakupki.dusya:
            response += f"   • Закупщик: Дуся Никитина\n"
        if row['Publisher_name'] in zakupki.tanya:
            response += f"   • Закупщик: Таня Постоногова\n"
        if row['Publisher_name'] in zakupki.yulya:
            response += f"   • Закупщик: Юля Харитонова\n"
        if row['Publisher_name'] in zakupki.ev:
            response += f"   • Закупщик: Елена Владимировна\n"
        if row['Publisher_name'] in zakupki.kirill:
            response += f"   • Закупщик: Кирилл Прыскин\n"

        await state.update_data(article=response,
                                current_year=row['YearPublishing'])
        await state.set_state(Add.approve)
        data = await state.get_data()
        await message.answer(
            f'вы искали эту позицию?\n{data["article"]}',
            reply_markup=kb.choise
        )

    except pymssql.Error as e:
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
            await state.set_state(Add.article)
            await callback.message.edit_text("⌨️Введите артикул:")

        elif callback.data == "yes":
            year_publishing = data.get("current_year")

            if year_publishing and year_publishing < 2020:
                await callback.message.edit_text(
                    f"📅 Внимание! Год издания {year_publishing}.\n"
                    f"Возможно у книги закончился тираж.\n"
                    f"Всё равно добавить эту позицию?",
                    reply_markup=kb.year_confirm_kb,
                )
            else:
                await add_book_to_list(state, data)
                await clear_article_data(state)
                await callback.message.edit_text(
                    "✅ Позиция добавлена!\nДобавить еще одну позицию?",
                    reply_markup=kb.continue_kb,  # Новая клавиатура для продолжения
                )

        elif callback.data == "yes_old_year":
            await add_book_to_list(state, data, is_old_year=True)
            await clear_article_data(state)
            await callback.message.edit_text(
                "✅ Позиция добавлена!\nДобавить еще одну позицию?",
                reply_markup=kb.continue_kb,  # Новая клавиатура для продолжения
            )

        elif callback.data == "no_old_year":
            await clear_article_data(state)
            await state.set_state(Add.article)
            await callback.message.edit_text("⌨️Введите артикул:")

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
            await callback.message.edit_text("⌨️Введите артикул:")

        elif callback.data == "continue_no":
            # Завершаем добавление и переходим к следующему шагу
            await state.set_state(Add.number)
            await callback.message.edit_text("☎️Введите номер телефона заказчика")
            await callback.answer()

        await callback.answer()

    except Exception as e:
        await callback.message.answer("❌ Ошибка при обработке")
        print(f"Error in handle_continue_confirmation: {e}")
        await callback.answer()


@router.callback_query(Add.cont_q)
async def fourth(callback: CallbackQuery, state: FSMContext):
    if callback.data == "yes":
        await state.set_state(Add.article)
        # Вызываем следующую функцию, передавая необходимые параметры
        await callback.message.answer("⌨️Введите артикул:")
        await callback.answer()
    elif callback.data == "no":
        await state.set_state(Add.number)
        await callback.message.answer("☎️Введите номер телефона заказчика")
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
        await message.answer("🙋Введите Имя заказчика🙋‍♂️")
        return True
    elif re.match(pattern2, phone):
        # Номер в формате 89990008899 - конвертируем в +79990008899
        formatted_phone = "+7" + phone[1:]
        await state.update_data(number=formatted_phone)
        await message.answer(f"✅ Номер сохранен: {formatted_phone}")
        await state.set_state(Add.name)
        await message.answer("🙋Введите Имя заказчика🙋‍♂️")
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


@router.callback_query(Add.senders)
async def seven(callback: CallbackQuery, state: FSMContext):
    if callback.data == "TZ":
        sender = "🐕ТЗ"
    elif callback.data == "IM":
        sender = "🐈ИМ"
    await state.update_data(sender=sender)
    await state.set_state(Add.employee)
    await callback.message.edit_text("🐵Введите своё имя")


@router.message(Add.employee)
async def precom(message: Message, state: FSMContext):
    await state.update_data(employee=message.text)
    await state.set_state(Add.comment)
    await message.answer("🏷️Комментарий", reply_markup=kb.skip)


@router.message(Add.comment)
async def nineth(message: Message, state: FSMContext):
    await complete_application(message, state, message.text)


@router.callback_query(F.data == "skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Комментарий пропущен")
    await complete_application(callback.message, state, "")


# ======================
# ДОБАВЛЕНИЕ ЗАЯВКИ - ПОТОК "НИКОГДА НЕ БЫЛО КНИГИ"
# ======================

@router.message(Add.neverbook)
async def n1(message: Message, state: FSMContext):
    await state.update_data(neverbook=message.text)
    await state.set_state(Add.neverbook_number)
    await message.answer("☎️Введите номер телефона заказчика")


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
        await message.answer("🙋Введите Имя заказчика🙋‍♂️")
        return True
    elif re.match(pattern2, phone):
        # Номер в формате 89990008899 - конвертируем в +79990008899
        formatted_phone = "+7" + phone[1:]
        await state.update_data(number=formatted_phone)
        await message.answer(f"✅ Номер сохранен: {formatted_phone}")
        await state.set_state(Add.neverbook_name)
        await message.answer("🙋Введите Имя заказчика🙋‍♂️")
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


@router.message(Add.neverbook_name)
async def n3(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Add.neverbook_senders)
    await message.answer(
        "❔Выберите отдел, который ожидает обработку заявки",
        reply_markup=kb.senders
    )


@router.callback_query(Add.neverbook_senders)
async def n4(callback: CallbackQuery, state: FSMContext):
    if callback.data == "TZ":
        sender = "🐕ТЗ"
    elif callback.data == "IM":
        sender = "🐈ИМ"
    await state.update_data(sender=sender)
    await state.set_state(Add.neverbook_employee)
    await callback.message.edit_text("🐵Введите своё имя")


@router.message(Add.neverbook_employee)
async def prencom(message: Message, state: FSMContext):
    await state.update_data(employee=message.text)
    await state.set_state(Add.neverbook_comment)
    await message.answer("🏷️Комментарий", reply_markup=kb.n_skip)


@router.message(Add.neverbook_comment)
async def n_comment(message: Message, state: FSMContext):
    await n5(message, state, message.text)


@router.callback_query(F.data == "n_skip")
async def n_skip_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Комментарий пропущен")
    await n5(callback.message, state, "")


# ======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ЗАЯВОК
# ======================

async def complete_application(message: Message, state: FSMContext, bot: Bot, comment: str = ""):

    status = "Создана"
    p_comment = ""
    await state.update_data(status=status,
                            p_comment=p_comment,
                            comment=comment)
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
    await delete_bot_conversation(bot, message.chat.id, hours=2)
    # Добавляем кнопку для просмотра истории
    if application_id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Показать историю заявок",
                        callback_data="history:0"
                    ),
                    InlineKeyboardButton(
                        text="🏠 В главное меню",
                        callback_data="main_menu"
                    )
                ]
            ]
        )
        await message.answer(
            f"✅ Заявка сохранена (ID: {application_id})", reply_markup=keyboard
        )

    await state.clear()


async def n5(message: Message, state: FSMContext, bot: Bot, comment: str = ""):
    status = "Создана"
    p_comment = ""
    await state.update_data(status=status,
                            p_comment=p_comment,
                            comment=comment)
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
    await delete_bot_conversation(bot, message.chat.id, hours=2)
    # Добавляем кнопку для просмотра истории
    if application_id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Показать историю заявок",
                        callback_data="history:0"
                    ),
                    InlineKeyboardButton(
                        text="🏠 В главное меню",
                        callback_data="main_menu"
                    )
                ]
            ]
        )
        await message.answer(
            f"✅ Заявка сохранена (ID: {application_id})", reply_markup=keyboard
        )

    await state.clear()


async def delete_bot_conversation(bot: Bot, chat_id: int, hours: int = 2):
    """Удаляет сообщения бота и пользователя за указанный период"""
    try:
        time_threshold = datetime.datetime.now() - timedelta(hours=hours)
        messages_to_delete = []

        async for message in bot.get_chat_history(chat_id):
            message_time = message.date.replace(tzinfo=None)

            # Если сообщение старше порога - прерываем
            if message_time < time_threshold:
                break

            # Добавляем все сообщения (или можно фильтровать только от бота/пользователя)
            messages_to_delete.append(message.message_id)

        if messages_to_delete:
            print(f"Найдено {len(messages_to_delete)} сообщений для удаления")

            # Удаляем в обратном порядке (от старых к новым)
            for i in range(0, len(messages_to_delete), 100):
                chunk = messages_to_delete[i:i + 100]
                await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                await asyncio.sleep(0.1)

        else:
            print("Нет сообщений для удаления")

    except Exception as e:
        print(f"Ошибка при очистке диалога: {e}")


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


def format_final_result(texts):
    """Форматирует список текстов в читаемый вид"""
    if not texts:
        return "Нет текстов"

    formatted = []
    for i, text in enumerate(texts, 1):
        formatted.append(f"📚Книга{i}. {text}")

    return "\n".join(formatted)
