from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

main = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✏️Добавить заявку", callback_data="add")],
        [InlineKeyboardButton(text="📋 Показать историю",
                              callback_data="history:0")],
        [InlineKeyboardButton(text="📊 Отчёты", callback_data="reports_menu")],
        [InlineKeyboardButton(
            text="🔍Проверить наличие книги", callback_data="baza")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Что вы хотите сделать?",
)


choise = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅да", callback_data="yes")],
        [InlineKeyboardButton(text="❌нет", callback_data="no")],
    ]
)


year_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, добавить",
                              callback_data="yes_old_year")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="no_old_year")],
    ]
)


continue_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="continue_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="continue_no"),
        ]
    ]
)


senders = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🐕ТЗ", callback_data="TZ")],
        [InlineKeyboardButton(text="🐈ИМ", callback_data="IM")],
    ]
)

req_q1 = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⌨️Ввести артикул",
                              callback_data="articool")],
        [
            InlineKeyboardButton(
                text="✏️Ввести название вручную", callback_data="neverbook"
            )
        ],
    ]
)

skip = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip")],
    ]
)

n_skip = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="n_skip")],
    ]
)