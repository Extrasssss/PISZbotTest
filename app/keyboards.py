from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Добавить заявку', callback_data='add')],
    [InlineKeyboardButton(text='Редактировать заявку', callback_data='edit'),
     InlineKeyboardButton(text='Удалить заявку', callback_data='delete')]
],
                            resize_keyboard=True,
                            input_field_placeholder='Что вы хотите сделать?')


purchisers = ['Саша Соколов',
              'Саша Плотникова', 'Таня Постоногова',
              'Дуся Никитина', 'Елена Владимировна',
              'Кирилл Прыскин', 'Не знаю']


async def reply_purchisers():
    keyboard = ReplyKeyboardBuilder()
    for purchiser in purchisers:
        keyboard.add(KeyboardButton(text=purchiser))
    return keyboard.adjust(2).as_markup()


inline_purchisers = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Саша Соколов', callback_data='sashas')],
    [InlineKeyboardButton(text='Саша Плотникова', callback_data='sashap')],
    [InlineKeyboardButton(text='Таня Постоногова', callback_data='tanya')],
    [InlineKeyboardButton(text='Дуся Никитина', callback_data='dusya')],
    [InlineKeyboardButton(text='Елена Владимировна', callback_data='ev')],
    [InlineKeyboardButton(text='Кирилл Прыскин', callback_data='kirill')],
],
                            resize_keyboard=True)

tablica = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='актуальная таблица стола заказов',
                          url='https://docs.google.com/spreadsheets/d/1OFLFBRBzfKHQrAkncowUMh1B3PFMD9XXIXFvusDA6l8/edit?gid=808253135#gid=808253135')]
])
