import datetime
import os

import pymssql
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)


from app.images import get_book_image_path, create_format_comparison_image


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ФУНКЦИИ ОТОБРАЖЕНИЯ РЕЗУЛЬТАТОВ ПОИСКА
# ======================

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
            code = row['code']
            if code not in products:
                products[code] = []
            products[code].append(row)

        total_pages = (total_count + items_per_page - 1) // items_per_page

        response = f"🔍 Результаты поиска: '{search_text}'\n"
        response += f"📊 Найдено товаров: {total_count}\n"
        response += f"📄 Страница {page} из {total_pages}\n"
        response += f"🎯 (отсортировано по релевантности)\n\n"

        search_buttons = []

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
            response += f"   • Название: {first_row['nomen_name'] or 'Не указано'}\n"
            response += f"   • Автор: {first_row['author_name'] or 'Не указан'}\n"
            response += (
                f"   • Издательство: {first_row['Publisher_name'] or 'Не указано'}\n"
            )
            response += f"   • Год издания: {first_row['YearPublishing'] or 'Не указан'}\n"
            response += f"   • Цена: {first_row['price'] or 'Не указана'} руб.\n"

            search_buttons.append([
                InlineKeyboardButton(
                    text=f"🔍 Поиск по коду {code}",
                    callback_data=f"search_by_code:{code}:{session_id}:{page}"
                )
            ])

            for i, row in enumerate(product_rows, 1):
                # Форматируем количество - убираем .000 и оставляем только целую часть
                remain = row['remain']
                if remain is not None:
                    # Преобразуем в целое число, если это float с .000
                    if isinstance(remain, (int, float)):
                        # Проверяем, заканчивается ли на .000
                        if isinstance(remain, float) and remain.is_integer():
                            remain_formatted = str(int(remain))
                        else:
                            remain_formatted = str(remain)
                    else:
                        # Если это строка, пытаемся преобразовать
                        try:
                            remain_float = float(remain)
                            if remain_float.is_integer():
                                remain_formatted = str(int(remain_float))
                            else:
                                remain_formatted = str(remain_float)
                        except:
                            remain_formatted = str(remain)
                else:
                    remain_formatted = "0"

                response += f"     Склад: {row['sklad_name'] or 'Не указан'}\n"
                response += f"   • Количество: **{remain_formatted}** шт.\n"
                if i < len(product_rows):
                    response += "   ─────────────────\n"

            response += "\n" + "=" * 50 + "\n\n"

        # Создаем клавиатуру пагинации
        from app.search_system.ss_utils import create_pagination_keyboard
        keyboard = create_pagination_keyboard(session_id, page, total_pages)

        inline_keyboard = search_buttons + keyboard.inline_keyboard

        final_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(loading_msg,
                                       response,
                                       reply_markup=keyboard)
        else:
            await message.answer(response, reply_markup=keyboard)

    except Exception as e:
        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(
                loading_msg, "❌ Ошибка при формировании результатов поиска"
            )
        else:
            await message.answer("❌ Ошибка при формировании результатов поиска")
        print(f"Results formatting error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


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
            code = row['code']
            if code not in products:
                products[code] = []
            products[code].append(row)

        response = f"{title}\n\n"

        for code, product_rows in products.items():
            first_row = product_rows[0]
            response += f"   • Код: `{first_row['code']}`\n"
            response += f"   • Название: {first_row['nomen_name'] or 'Не указано'}\n"
            response += f"   • Автор: {first_row['author_name'] or 'Не указан'}\n"
            response += (
                f"   • Издательство: {first_row['Publisher_name'] or 'Не указано'}\n"
            )
            response += f"   • Год издания: {first_row['YearPublishing'] or 'Не указан'}\n"
            response += f"   • Обложка: {first_row['binding_name'] or 'Не указана'}\n"
            response += f"   • Формат: {first_row['format_'] or 'Не указан'}\n"
            response += f"   • Объем: {first_row['volume'] or 'Не указан'} стр.\n"
            response += f"   • Цена: {first_row['price'] or 'Не указана'}\n\n"

            for i, row in enumerate(product_rows, 1):
                # Форматируем количество - убираем .000 и оставляем только целую часть
                remain = row['remain']
                if remain is not None:
                    # Преобразуем в целое число, если это float с .000
                    if isinstance(remain, (int, float)):
                        # Проверяем, заканчивается ли на .000
                        if isinstance(remain, float) and remain.is_integer():
                            remain_formatted = str(int(remain))
                        else:
                            remain_formatted = str(remain)
                    else:
                        # Если это строка, пытаемся преобразовать
                        try:
                            remain_float = float(remain)
                            if remain_float.is_integer():
                                remain_formatted = str(int(remain_float))
                            else:
                                remain_formatted = str(remain_float)
                        except:
                            remain_formatted = str(remain)
                else:
                    remain_formatted = "0"

                response += f"   📦 Склад: {row['sklad_name'] or 'Не указан'}\n"
                response += f"   • Количество: **{remain_formatted}** шт.\n"
                if i < len(product_rows):
                    response += "   ─────────────────\n"

            response += "\n" + "=" * 50 + "\n\n"

        if row['IsInoagent'] == 1:
            response = f"❌НАСТОЯЩИЙ МАТЕРИАЛ (ИНФОРМАЦИЯ)❌\n❌ПРОИЗВЕДЕН ИНОСТРАННЫМ АГЕНТОМ,❌\n❌ЛИБО КАСАЕТСЯ ДЕЯТЕЛЬНОСТИ ИНОСТРАННОГО АГЕНТА❌\n❗❗❗КНИГА НЕ ДОСТУПНА ДЛЯ ПРОДАЖИ❗❗❗\n Введите другой артикул:"
            await message.answer(response)
            return

        # Остальной код без изменений...
        media_files = []

        if first_row['filepath']:
            book_image_path = get_book_image_path(first_row['filepath'])
            if book_image_path and os.path.exists(book_image_path):
                try:
                    book_photo = FSInputFile(book_image_path)
                    media_files.append(book_photo)
                except Exception as e:
                    print(f"Error loading book image: {e}")

        # Добавляем изображение сравнения форматов если есть формат
        if first_row['format_']:
            format_image_buffer = create_format_comparison_image(
                first_row['format_'])
            if format_image_buffer:
                format_photo = BufferedInputFile(
                    format_image_buffer.getvalue(),
                    filename="format_comparison.png"
                )
                media_files.append(format_photo)

        # Создаем клавиатуру пагинации (если есть несколько страниц)
        from app.search_system.ss_utils import get_search_session
        session = get_search_session(session_id)
        keyboard = None
        if session and session.total_pages > 1:
            from app.search_system.ss_utils import create_pagination_keyboard
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
                        await message.answer(reply_markup=keyboard)
                else:
                    await message.answer_media_group(media=media_group)
                    if keyboard:
                        await message.answer(reply_markup=keyboard)
        else:
            # Если нет изображений, отправляем только текст
            if loading_msg:
                from app.search_system.ss_utils import edit_loading_message
                await edit_loading_message(loading_msg,
                                           response,
                                           reply_markup=keyboard)
            else:
                await message.answer(response, reply_markup=keyboard)

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

    except Exception as e:
        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(
                loading_msg, "❌ Ошибка при отправке результатов"
            )
        else:
            await message.answer("❌ Ошибка при отправке результатов")
        print(f"Send results error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")


async def get_search_results_page(
    message: Message,
    db_connection: pymssql.Connection,
    session_id: str,
    page: int = 1,
    pre_scored_products: list = None,
    loading_msg: Message = None,
):
    """Получение результатов поиска для конкретной страницы с сортировкой по релевантности"""
    from app.search_system.ss_utils import get_search_session
    session = get_search_session(session_id)
    if not session:
        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(loading_msg, "❌ Сессия поиска устарела")
        else:
            await message.answer("❌ Сессия поиска устарела")
        return

    cursor = db_connection.cursor(as_dict=True)
    items_per_page = session.items_per_page
    offset = (page - 1) * items_per_page

    if pre_scored_products:
        # Используем предварительно отсортированные товары
        sorted_products = pre_scored_products
    else:
        # Получаем и сортируем товары заново
        codes_placeholder = ",".join(["%s" for _ in session.matched_codes])

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
            from app.search_system.ss_utils import calculate_match_score
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
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(loading_msg, "❌ Нет данных для отображения")
        else:
            await message.answer("❌ Нет данных для отображения")
        return

    # Упрощенный запрос без сложного ORDER BY
    codes_placeholder = ",".join(["%s" for _ in page_codes])

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

    cursor.execute(data_query, tuple(page_codes))
    rows = cursor.fetchall()

    # Сортируем результаты в Python согласно нашему порядку
    code_to_row = {row['code']: row for row in rows}
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
