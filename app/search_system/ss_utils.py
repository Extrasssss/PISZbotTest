import asyncio
import datetime
import hashlib
import time

import Levenshtein
import pymssql
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


# ======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА
# ======================

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

# ======================
# ФУНКЦИИ ПАГИНАЦИИ И УТИЛИТЫ ПОИСКА
# ======================


async def handle_pagination_callback(
    callback_query: CallbackQuery, db_connection: pymssql.Connection
):
    """ИСПРАВЛЕННАЯ быстрая версия обработки пагинации"""
    # 🚀 Мгновенный ответ
    try:
        await callback_query.answer()
    except:
        return

    # 🚀 Быстрый парсинг
    try:
        if not callback_query.data.startswith("page_"):
            return

        _, session_id, page_str = callback_query.data.split("_", 2)
        new_page = int(page_str)
    except:
        return

    loading_msg = None
    try:
        # 🚀 Отправляем загрузку
        loading_msg = await send_loading_message(callback_query.message)

        # 🚀 Получаем сессию
        session = get_search_session(session_id)

        # 🚀 Fallback на последнюю сессию
        if not session:
            user_sessions = get_user_sessions(callback_query.from_user.id)
            if not user_sessions:
                await loading_msg.edit_text("❌ Сессия устарела")
                return
            session_id, session = next(iter(user_sessions.items()))

        # 🚀 Удаляем старое сообщение (с await)
        try:
            await callback_query.message.delete()
        except Exception as delete_error:
            print(f"⚠️ Delete error (ignored): {delete_error}")
            # Игнорируем ошибки удаления, продолжаем работу

        # 🚀 Выполняем поиск
        if session.search_type == "code":
            from app.search_system.ss_results import get_search_results_page
            await get_search_results_page(
                callback_query.message,
                db_connection,
                session_id,
                new_page,
                loading_msg=loading_msg,
            )
        else:
            from app.search_system.search_system import search_by_text
            await search_by_text(
                callback_query.message,
                db_connection,
                session.search_term,
                new_page,
                loading_msg,
            )

    except Exception as e:
        # 🚀 Минимальная обработка ошибок
        try:
            if loading_msg:
                await loading_msg.edit_text("❌ Ошибка переключения страницы")
        except:
            pass
        print(f"Quick pagination error: {e}")


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

    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="🏠 В главное меню",
                              callback_data="main_menu")]
    )

    return keyboard


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
