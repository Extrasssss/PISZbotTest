
import datetime

import pymssql
from aiogram.types import (
    Message,
)

from app.search_system.ss_utils import SearchSession



current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ОСНОВНЫЕ ФУНКЦИИ ПОИСКА
# ======================

async def search_in_database(
    message: Message, db_connection: pymssql.Connection, search_term: str
):
    """Общая функция поиска в базе данных по коду или тексту"""
    loading_msg = None
    try:
        # Отправляем сообщение "загрузка"
        from app.search_system.ss_utils import send_loading_message
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

    except pymssql.Error as e:
        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(
                loading_msg, "❌ Ошибка при работе с базой данных"
            )
        else:
            await message.answer("❌ Ошибка при работе с базой данных")
        print(f"Database error: {e}")
    except Exception as e:
        if loading_msg:
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(
                loading_msg, "❌ Произошла непредвиденная ошибка"
            )
        else:
            await message.answer("❌ Произошла непредвиденная ошибка")
        print(f"Unexpected error: {e}")


async def search_by_code(
    message: Message,
    db_connection: pymssql.Connection,
    code: str,
    loading_msg: Message = None,
):
    """Поиск по коду товара"""
    try:
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
        [volume],
        [filepath]
        FROM [torgnew].[dbo].[nomen_bot]
        WHERE [code] = %s
        """
        cursor.execute(query, code)
        rows = cursor.fetchall()

        if not rows:
            if loading_msg:
                from app.search_system.ss_utils import edit_loading_message
                await edit_loading_message(
                    loading_msg, f"Товар с кодом '{code}' не найден"
                )
            else:
                await message.answer(f"Товар с кодом '{code}' не найден")
            return

        # Сохраняем сессию поиска с новым ID
        from app.search_system.ss_utils import generate_session_id
        session_id = generate_session_id(message.from_user.id, code)
        session = SearchSession(
            search_type="code",
            search_term=code,
            matched_codes={code},
            total_count=len(rows),  # Добавляем total_count
            items_per_page=5,
        )
        from app.search_system.ss_utils import add_search_session
        add_search_session(session_id, session, message.from_user.id)

        from app.search_system.ss_results import send_search_results
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
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(loading_msg,
                                       "❌ Ошибка при поиске по коду")
        else:
            await message.answer("❌ Ошибка при поиске по коду")
        print(f"Search by code error: {e}")


async def search_by_text(
    message: Message,
    db_connection: pymssql.Connection,
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
                from app.search_system.ss_utils import edit_loading_message
                await edit_loading_message(loading_msg,
                                           "❌ Введите текст для поиска")
            else:
                await message.answer("❌ Введите текст для поиска")
            return

        cursor = db_connection.cursor(as_dict=True)

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
            nomen_name = product['nomen_name_safe'] or ""
            author_name = product['author_name_safe'] or ""

            # Создаем полный текст для поиска
            full_text = f"{nomen_name} {author_name}".strip()

            if not full_text:
                continue

            # Вычисляем оценку релевантности
            from app.search_system.ss_utils import calculate_match_score
            match_score = calculate_match_score(full_text, search_words)

            # ПОВЫШАЕМ ПОРОГ для отсечения слабых совпадений
            if match_score > 0.4:
                scored_products.append(
                    {
                        "code": product['code'],
                        "nomen_name": nomen_name,
                        "author_name": author_name,
                        "score": match_score,
                        "full_text": full_text,
                    }
                )

        if not scored_products:
            if loading_msg:
                from app.search_system.ss_utils import edit_loading_message
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
        from app.search_system.ss_utils import generate_session_id
        session_id = generate_session_id(message.from_user.id, search_text)
        session = SearchSession(
            search_type="text",
            search_term=search_text,
            matched_codes=matched_codes,
            search_words=search_words,
            total_count=len(scored_products),  # Добавляем total_count
            items_per_page=5,
        )
        from app.search_system.ss_utils import add_search_session
        add_search_session(session_id, session, message.from_user.id)

        # Получаем данные для текущей страницы
        from app.search_system.ss_results import get_search_results_page
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
            from app.search_system.ss_utils import edit_loading_message
            await edit_loading_message(loading_msg,
                                       "❌ Ошибка при текстовом поиске")
        else:
            await message.answer("❌ Ошибка при текстовом поиске")
        print(f"Text search error: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
