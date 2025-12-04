import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.inner_db import inner_db as idb
from app import router


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ИСТОРИЯ И РЕДАКТИРОВАНИЕ ЗАЯВОК
# ======================


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
