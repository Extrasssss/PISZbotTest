from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import re

import app.keyboards as kb
# import app.validators as vd
import app.zakupki_info as zakupki

router = Router()


class Add(StatesGroup):
    date = State()
    article = State()
    title = State()
    number = State()
    name = State()
    publisher = State()
    purchiser = State()
    comment = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f'Привет, {message.from_user.first_name}! Я бот для помощи стола заказов.',
                         reply_markup=kb.main)


@router.message(Command('tablica'))
async def tablica(message: Message):
    await message.answer('Таблица', reply_markup=kb.tablica)


@router.message(Command('zakupki'))
async def get_help(message: Message):
    await message.answer('Кто что заказывает',
                         reply_markup=kb.inline_purchisers)


@router.callback_query(F.data == 'sashas')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.sashas)


@router.callback_query(F.data == 'sashap')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.sashap)


@router.callback_query(F.data == 'tanya')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.tanya)


@router.callback_query(F.data == 'dusya')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.dusya)


@router.callback_query(F.data == 'ev')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.ev)


@router.callback_query(F.data == 'kirill')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text(zakupki.kirill)


@router.callback_query(F.data == 'add')
async def add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Add.date)
    await callback.answer('Новая заявка', show_alert=True)
    await callback.message.edit_text('введите дату в формате ДД.ММ.ГГГГ')


@router.callback_query(F.data == 'edit')
async def edit(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text('Нет доступных заявок для редактирования')


@router.callback_query(F.data == 'delete')
async def delete(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_text('Нет доступных заявок для удаления')


@router.message(Add.date)
async def second(message: Message, state: FSMContext):
    r = re.compile('(0[1-9]|[12][0-9]|3[01])[.](0[1-9]|1[012])[.](19|20)\d\d')
    if r.search(str(message)):
        await state.update_data(date=message.text)
        await state.set_state(Add.article)
        await message.answer('введите артикул')
    else:
        await message.answer('Неправильная дата')


@router.message(Add.article)
async def third(message: Message, state: FSMContext):
    await state.update_data(article=message.text)
    await state.set_state(Add.title)
    await message.answer('введите название')


@router.message(Add.title)
async def fourth(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(Add.number)
    await message.answer('введите номер телефона')


@router.message(Add.number)
async def fifth(message: Message, state: FSMContext):
    r = re.compile('(\+7|8)\D*\d{3}\D*\d{3}\D*\d{2}\D*\d{2}')
    if r.search(str(message)):
        await state.update_data(number=message.text)
        await state.set_state(Add.name)
        await message.answer('введите Имя')
    else:
        await message.answer('неправильный номер. Номер должен начинаться с +7 или 8 и иметь 10 цифр после')


@router.message(Add.name)
async def sixth(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Add.publisher)
    await message.answer('введите издательство')


@router.message(Add.publisher)
async def seventh(message: Message, state: FSMContext):
    await state.update_data(publisher=message.text)
    await state.set_state(Add.purchiser)
    await message.answer('введите закупщика',
                         reply_markup=await kb.reply_purchisers())


@router.message(Add.purchiser)
async def eighth(message: Message, state: FSMContext):
    await state.update_data(purchiser=message.text)
    await state.set_state(Add.comment)
    await message.answer('комментарий')


@router.message(Add.comment)
async def nineth(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()
    await message.answer(f'Заявка принята.\nДата: {data["date"]}\nАртикул: {data["article"]}\nНазвание: {data["title"]}\nКонтакты: {data["number"]}\nИмя: {data["name"]}\nИздательство: {data["publisher"]}\nЗакупщик: {data["purchiser"]}\nКомментарий:{data["comment"]}')
