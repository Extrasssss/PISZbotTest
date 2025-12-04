
import datetime

import re


from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


from app.email_service.report_service import (send_report_in_chat,
                                              send_report_to_email)
from app.inner_db.inner_db import applications_manager
from app.states import ReportStates
from app import router


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ОТЧЕТЫ
# ======================


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
                    text="⬅️ История заявок", callback_data="history:0")],
                [InlineKeyboardButton(
                        text="  В главное меню",
                        callback_data="main_menu")]
            ]
        )

        await callback_query.message.edit_text(response, reply_markup=keyboard)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


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
