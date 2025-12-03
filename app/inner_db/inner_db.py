import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем текущее время
r_time = datetime.now().strftime("%d.%m.%Y %H:%M")


# Состояния для FSM
class EditStates(StatesGroup):
    waiting_edit_comment = State()
    waiting_edit_status = State()
    waiting_edit_contacts = State()
    waiting_edit_name = State()
    waiting_edit_purchaser_comment = State()


class DeleteStates(StatesGroup):
    waiting_delete_confirmation = State()


class SQLiteHistoryManager:
    """Класс для управления историей заявок в локальной SQLite базе"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DB_PATH
        self.connection = None

    def connect(self) -> bool:
        """Подключение к SQLite базе"""
        try:
            self.connection = sqlite3.connect(
                self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row

            # Создаем таблицу, если она не существует
            self._create_table_if_not_exists()

            logger.info(
                f"✅ Подключение к SQLite базе {self.db_path} установлено")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка подключения к SQLite: {e}")
            return False

    def _create_table_if_not_exists(self):
        """Создает таблицу для хранения истории заявок"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_text TEXT NOT NULL,
            comment TEXT NOT NULL,
            status TEXT NOT NULL,
            created_date TEXT NOT NULL,
            contacts TEXT,
            name TEXT,
            purchaser_comment TEXT
        )
        """

        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_query)

            # Добавляем новые колонки, если их нет (для существующих баз)
            self._add_missing_columns()

            self.connection.commit()
            logger.info("✅ Таблица applications создана или уже существует")
        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка создания таблицы: {e}")

    def _add_missing_columns(self):
        """Добавляет отсутствующие колонки в существующую таблицу"""
        try:
            cursor = self.connection.cursor()

            # Проверяем существование колонок и добавляем их если нужно
            columns_to_add = [
                ('contacts', 'TEXT'),
                ('name', 'TEXT'),
                ('purchaser_comment', 'TEXT')
            ]

            for column_name, column_type in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE applications ADD COLUMN {column_name} {column_type}")
                    logger.info(f"✅ Добавлена колонка {column_name}")
                except sqlite3.OperationalError:
                    # Колонка уже существует
                    pass

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка добавления колонок: {e}")

    def save_application(
        self,
        application_text: str,
        comment: str,
        status: str,
        contacts: str = "",
        name: str = "",
        purchaser_comment: str = ""
    ) -> Optional[int]:
        """Сохраняет заявку в базу истории"""
        if not self.connection:
            if not self.connect():
                return None

        try:
            insert_query = """
            INSERT INTO applications (
                application_text, comment, status, created_date,
                contacts, name, purchaser_comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            cursor = self.connection.cursor()
            cursor.execute(
                insert_query,
                (application_text, comment, status, r_time,
                 contacts, name, purchaser_comment)
            )

            new_id = cursor.lastrowid
            self.connection.commit()

            logger.info(f"✅ Заявка сохранена с ID: {new_id}")
            return new_id

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка сохранения заявки: {e}")
            return None

    def get_applications_page(self,
                              page: int = 0,
                              per_page: int = 5) -> List[Dict]:
        """Получает страницу истории заявок"""
        if not self.connection:
            if not self.connect():
                return []

        try:
            offset = page * per_page
            query = """
            SELECT id, application_text, comment, status, created_date
            FROM applications
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """

            cursor = self.connection.cursor()
            cursor.execute(query, (per_page, offset))
            rows = cursor.fetchall()

            # Конвертируем в словари
            result = []
            for row in rows:
                result.append(
                    {
                        "id": row["id"],
                        "application_text": row["application_text"],
                        "comment": row["comment"],
                        "status": row["status"],
                        "created_date": row["created_date"],
                    }
                )

            return result

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка получения истории заявок: {e}")
            return []

    def get_total_pages(self, per_page: int = 5) -> int:
        """Получает общее количество страниц"""
        if not self.connection:
            if not self.connect():
                return 0

        try:
            query = "SELECT COUNT(*) FROM applications"
            cursor = self.connection.cursor()
            cursor.execute(query)
            total_records = cursor.fetchone()[0]

            return (total_records + per_page - 1) // per_page

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка получения количества страниц: {e}")
            return 0

    def get_application_by_id(self, application_id: int) -> Optional[Dict]:
        """Получает заявку по ID"""
        if not self.connection:
            if not self.connect():
                return None

        try:
            query = """
            SELECT id, application_text, comment, status, created_date,
                   contacts, name, purchaser_comment
            FROM applications
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(query, (application_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "application_text": row["application_text"],
                    "comment": row["comment"],
                    "status": row["status"],
                    "created_date": row["created_date"],
                    "contacts": row["contacts"] or "",
                    "name": row["name"] or "",
                    "purchaser_comment": row["purchaser_comment"] or "",
                }
            return None

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка получения заявки по ID: {e}")
            return None

    def get_all_applications(self) -> List[Dict]:
        """Получает все заявки из базы"""
        if not self.connection:
            if not self.connect():
                return []

        try:
            query = """
            SELECT id, application_text, comment, status, created_date,
                   contacts, name, purchaser_comment
            FROM applications
            ORDER BY id DESC
            """

            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            # Конвертируем в словари
            result = []
            for row in rows:
                result.append(
                    {
                        "id": row["id"],
                        "application_text": row["application_text"],
                        "comment": row["comment"],
                        "status": row["status"],
                        "created_date": row["created_date"],
                        "contacts": row["contacts"] or "",
                        "name": row["name"] or "",
                        "purchaser_comment": row["purchaser_comment"] or "",
                    }
                )

            return result

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка получения всех заявок: {e}")
            return []

    def get_applications_by_period(self,
                                   start_date: str,
                                   end_date: str) -> List[Dict]:
        """Получает заявки за указанный период"""
        if not self.connection:
            if not self.connect():
                return []

        try:
            query = """
            SELECT id, application_text, comment, status, created_date,
                   contacts, name, purchaser_comment
            FROM applications
            WHERE date(created_date) BETWEEN date(?) AND date(?)
            ORDER BY id DESC
            """

            cursor = self.connection.cursor()
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()

            # Конвертируем в словари
            result = []
            for row in rows:
                result.append(
                    {
                        "id": row["id"],
                        "application_text": row["application_text"],
                        "comment": row["comment"],
                        "status": row["status"],
                        "created_date": row["created_date"],
                        "contacts": row["contacts"] or "",
                        "name": row["name"] or "",
                        "purchaser_comment": row["purchaser_comment"] or "",
                    }
                )

            return result

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка получения заявок за период: {e}")
            return []

    def update_comment(self, application_id: int, new_comment: str) -> bool:
        """Обновляет поле комментария"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            # Получаем текущую заявку
            current_record = self.get_application_by_id(application_id)
            if not current_record:
                return False

            # Обновляем текст заявки
            old_text = current_record["application_text"]
            lines = old_text.split("\n")

            # Заменяем строку с комментарием
            new_lines = []
            for line in lines:
                if line.strip().startswith("• Комментарий:"):
                    new_lines.append(f"  • Комментарий: {new_comment}")
                else:
                    new_lines.append(line)

            new_text = "\n".join(new_lines)

            # Обновляем в базе
            update_query = """
            UPDATE applications
            SET application_text = ?, comment = ?
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(
                update_query, (new_text, new_comment, application_id))
            self.connection.commit()

            logger.info(f"✅ Комментарий обновлен для заявки {application_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка обновления комментария: {e}")
            return False

    def update_status(self, application_id: int, new_status: str) -> bool:
        """Обновляет поле статуса"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            # Получаем текущую заявку
            current_record = self.get_application_by_id(application_id)
            if not current_record:
                return False

            # Обновляем текст заявки
            old_text = current_record["application_text"]
            lines = old_text.split("\n")

            # Заменяем строку со статусом
            new_lines = []
            for line in lines:
                if line.strip().startswith("• Статус заявки:"):
                    new_lines.append(f" • Статус заявки: {new_status}")
                else:
                    new_lines.append(line)

            new_text = "\n".join(new_lines)

            # Обновляем в базе
            update_query = """
            UPDATE applications
            SET application_text = ?, status = ?
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(
                update_query, (new_text, new_status, application_id))
            self.connection.commit()

            logger.info(f"✅ Статус обновлен для заявки {application_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")
            return False

    def update_contacts(self, application_id: int, new_contacts: str) -> bool:
        """Обновляет поле контактов"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            # Получаем текущую заявку
            current_record = self.get_application_by_id(application_id)
            if not current_record:
                return False

            # Обновляем текст заявки
            old_text = current_record["application_text"]
            lines = old_text.split("\n")

            # Заменяем строку с контактами
            new_lines = []
            contact_updated = False
            for line in lines:
                if line.strip().startswith("• Контакты:"):
                    new_lines.append(f"  • Контакты: {new_contacts}")
                    contact_updated = True
                else:
                    new_lines.append(line)

            # Если строка с контактами не найдена, добавляем её
            if not contact_updated:
                # Находим место для вставки (после имени)
                for i, line in enumerate(lines):
                    if line.strip().startswith("• Имя:"):
                        new_lines.insert(i + 1, f"  • Контакты: {new_contacts}")
                        break

            new_text = "\n".join(new_lines)

            # Обновляем в базе
            update_query = """
            UPDATE applications
            SET application_text = ?, contacts = ?
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(
                update_query, (new_text, new_contacts, application_id))
            self.connection.commit()

            logger.info(f"✅ Контакты обновлены для заявки {application_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка обновления контактов: {e}")
            return False

    def update_name(self, application_id: int, new_name: str) -> bool:
        """Обновляет поле имени"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            # Получаем текущую заявку
            current_record = self.get_application_by_id(application_id)
            if not current_record:
                return False

            # Обновляем текст заявки
            old_text = current_record["application_text"]
            lines = old_text.split("\n")

            # Заменяем строку с именем
            new_lines = []
            for line in lines:
                if line.strip().startswith("• Имя:"):
                    new_lines.append(f"  • Имя: {new_name}")
                else:
                    new_lines.append(line)

            new_text = "\n".join(new_lines)

            # Обновляем в базе
            update_query = """
            UPDATE applications
            SET application_text = ?, name = ?
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(
                update_query, (new_text, new_name, application_id))
            self.connection.commit()

            logger.info(f"✅ Имя обновлено для заявки {application_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка обновления имени: {e}")
            return False

    def update_purchaser_comment(self, application_id: int, new_purchaser_comment: str) -> bool:
        """Обновляет поле комментария закупщика"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            # Получаем текущую заявку
            current_record = self.get_application_by_id(application_id)
            if not current_record:
                return False

            # Обновляем текст заявки
            old_text = current_record["application_text"]
            lines = old_text.split("\n")

            # Заменяем строку с комментарием закупщика
            new_lines = []
            comment_updated = False
            for line in lines:
                if line.strip().startswith("• Комментарий от закупщика:"):
                    new_lines.append(f"  • Комментарий от закупщика: {new_purchaser_comment}")
                    comment_updated = True
                else:
                    new_lines.append(line)

            # Если строка с комментарием закупщика не найдена, добавляем её в конец
            if not comment_updated:
                new_lines.append(f"  • Комментарий от закупщика: {new_purchaser_comment}")

            new_text = "\n".join(new_lines)

            # Обновляем в базе
            update_query = """
            UPDATE applications
            SET application_text = ?, purchaser_comment = ?
            WHERE id = ?
            """

            cursor = self.connection.cursor()
            cursor.execute(
                update_query, (new_text, new_purchaser_comment, application_id))
            self.connection.commit()

            logger.info(f"✅ Комментарий закупщика обновлен для заявки {application_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка обновления комментария закупщика: {e}")
            return False

    def delete_application(self, application_id: int) -> bool:
        """Удаляет заявку по ID"""
        if not self.connection:
            if not self.connect():
                return False

        try:
            delete_query = "DELETE FROM applications WHERE id = ?"

            cursor = self.connection.cursor()
            cursor.execute(delete_query, (application_id,))
            self.connection.commit()

            if cursor.rowcount > 0:
                logger.info(f"✅ Заявка {application_id} удалена")
                return True
            else:
                logger.warning(
                    f"⚠️ Заявка {application_id} не найдена для удаления")
                return False

        except sqlite3.Error as e:
            logger.error(f"❌ Ошибка удаления заявки: {e}")
            return False

    def disconnect(self):
        """Закрывает подключение"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Подключение к SQLite базе закрыто")


# Создаем менеджер истории заявок
applications_manager = SQLiteHistoryManager(Config.DB_PATH)


# Ваша функция format_final_result (заглушка)
def format_final_result(books):
    """Форматирует финальный результат (ваша реализация)"""
    if isinstance(books, str):
        return books
    elif isinstance(books, list):
        return "\n".join([str(book) for book in books])
    else:
        return str(books)


async def show_applications_history(callback_query: CallbackQuery,
                                    page: int = 0):
    """Показывает историю заявок с пагинацией"""
    try:
        applications = applications_manager.get_applications_page(
            page=page, per_page=5)
        total_pages = applications_manager.get_total_pages(per_page=5)

        if not applications:
            await callback_query.message.answer("📝 История заявок пуста")
            await callback_query.answer()
            return

        response = f"📋 История заявок (стр. {page + 1}/{total_pages or 1}):\n\n"

        for application in applications:
            response += f"🆔 ID: {application['id']}\n"
            response += f"{application['application_text']}\n"
            response += "─" * 40 + "\n\n"

        # Создаем клавиатуру с кнопками редактирования и удаления
        keyboard_buttons = []

        # Кнопки редактирования и удаления
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать заявки",
                    callback_data=f"edit_page:{page}"
                )
            ]
        )
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить заявки",
                    callback_data=f"delete_page:{page}"
                )
            ]
        )
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="  В главное меню",
                    callback_data="main_menu"
                )
            ]
        )

        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"history:{page-1}")
            )

        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперед ➡️", callback_data=f"history:{page+1}")
            )

        if nav_buttons:
            keyboard_buttons.append(nav_buttons)

        await callback_query.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_buttons),
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Ошибка при получении истории: {e}"
            )
        await callback_query.answer()


async def show_edit_page(callback_query: CallbackQuery, page: int = 0):
    """Показывает страницу с кнопками редактирования для каждой заявки"""
    try:
        applications = applications_manager.get_applications_page(
            page=page, per_page=5)

        if not applications:
            await callback_query.answer(
                "❌ На этой странице нет заявок", show_alert=True
            )
            return

        response = f"✏️ Выберите заявку для редактирования (стр. {page + 1}):\n\n"

        for application in applications:
            response += f"🆔 ID: {application['id']}\n"
            response += (
                f"💬 Комментарий: {application['comment'][:30]}...\n"
                if len(application["comment"]) > 30
                else f"💬 Комментарий: {application['comment']}\n"
            )
            response += f"📋 Статус: {application['status']}\n"
            response += "─" * 30 + "\n\n"

        # Создаем кнопки для каждой заявки на странице
        keyboard_buttons = []

        for application in applications:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"✏️ ID {application['id']} - {application['status']}",
                        callback_data=f"edit_application:{application['id']}",
                    )
                ]
            )

        # Кнопка возврата к просмотру истории
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к просмотру",
                    callback_data=f"history:{page}"
                )
            ]
        )

        await callback_query.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_buttons),
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def show_delete_page(callback_query: CallbackQuery, page: int = 0):
    """Показывает страницу с кнопками удаления для каждой заявки"""
    try:
        applications = applications_manager.get_applications_page(
            page=page, per_page=5)

        if not applications:
            await callback_query.answer(
                "❌ На этой странице нет заявок", show_alert=True
            )
            return

        response = f"🗑️ Выберите заявку для удаления (стр. {page + 1}):\n\n"

        for application in applications:
            response += f"🆔 ID: {application['id']}\n"
            response += (
                f"💬 Комментарий: {application['comment'][:30]}...\n"
                if len(application["comment"]) > 30
                else f"💬 Комментарий: {application['comment']}\n"
            )
            response += f"📋 Статус: {application['status']}\n"
            response += "─" * 30 + "\n\n"

        # Создаем кнопки для каждой заявки на странице
        keyboard_buttons = []

        for application in applications:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"🗑️ ID {application['id']} - {application['status']}",
                        callback_data=f"confirm_delete:{application['id']}",
                    )
                ]
            )

        # Кнопка возврата к просмотру истории
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к просмотру",
                    callback_data=f"history:{page}"
                )
            ]
        )

        await callback_query.message.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_buttons),
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def show_delete_confirmation(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Показывает первое подтверждение удаления"""
    try:
        application = applications_manager.get_application_by_id(
            application_id)

        if not application:
            await callback_query.answer("❌ Заявка не найдена", show_alert=True)
            return

        response = f"⚠️ ВНИМАНИЕ: Вы собираетесь удалить заявку!\n\n"
        response += f"🆔 ID: {application['id']}\n"
        response += f"💬 Комментарий: {application['comment']}\n"
        response += f"📋 Статус: {application['status']}\n\n"
        response += "❌ Это действие нельзя отменить!\n\n"
        response += "Для подтверждения удаления введите ID заявки:\n"
        response += f"`{application_id}`"

        # Сохраняем ID заявки в состоянии
        await state.update_data(delete_application_id=application_id)
        await state.set_state(DeleteStates.waiting_delete_confirmation)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отменить удаление", callback_data="history:0"
                    )
                ]
            ]
        )

        await callback_query.message.edit_text(response, reply_markup=keyboard)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def show_edit_options(callback_query: CallbackQuery,
                            application_id: int):
    """Показывает опции редактирования для конкретной заявки"""
    try:
        application = applications_manager.get_application_by_id(
            application_id)

        if not application:
            await callback_query.answer("❌ Заявка не найдена", show_alert=True)
            return

        response = f"✏️ Редактирование заявки ID: {application_id}\n\n"
        response += f"💬 Текущий комментарий: {application['comment']}\n"
        response += f"📋 Текущий статус: {application['status']}\n"
        response += f"📞 Текущие контакты: {application.get('contacts', 'не указаны')}\n"
        response += f"👤 Текущее имя: {application.get('name', 'не указано')}\n"
        response += f"💼 Комментарий закупщика: {application.get('purchaser_comment', 'не указан')}\n\n"
        response += "Выберите что хотите изменить:"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Изменить комментарий",
                        callback_data=f"edit_comment:{application_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Изменить статус",
                        callback_data=f"edit_status:{application_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📞 Изменить контакты",
                        callback_data=f"edit_contacts:{application_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👤 Изменить имя",
                        callback_data=f"edit_name:{application_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💼 Изменить комментарий закупщика",
                        callback_data=f"edit_purchaser_comment:{application_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад к списку", callback_data="edit_page:0"
                    )
                ],
            ]
        )

        await callback_query.message.edit_text(response, reply_markup=keyboard)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def start_edit_comment(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Начинает процесс редактирования комментария"""
    try:
        await state.update_data(edit_application_id=application_id)
        await state.set_state(EditStates.waiting_edit_comment)

        application = applications_manager.get_application_by_id(
            application_id)
        current_comment = application["comment"] if application else ""

        await callback_query.message.answer(
            f"✏️ Введите новый комментарий для заявки ID: {application_id}\n\n"
            f"Текущий комментарий: {current_comment}\n\n"
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def start_edit_status(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Начинает процесс редактирования статуса"""
    try:
        await state.update_data(edit_application_id=application_id)
        await state.set_state(EditStates.waiting_edit_status)

        application = applications_manager.get_application_by_id(
            application_id)
        current_status = application["status"] if application else ""

        await callback_query.message.answer(
            f"✏️ Введите новый статус для заявки ID: {application_id}\n\n"
            f"Текущий статус: {current_status}\n\n"
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def start_edit_contacts(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Начинает процесс редактирования контактов"""
    try:
        await state.update_data(edit_application_id=application_id)
        await state.set_state(EditStates.waiting_edit_contacts)

        application = applications_manager.get_application_by_id(application_id)
        current_contacts = application.get("contacts", "") if application else ""

        await callback_query.message.answer(
            f"📞 Введите новые контакты для заявки ID: {application_id}\n\n"
            f"Текущие контакты: {current_contacts if current_contacts else 'не указаны'}\n\n"
            "Пример: +7 (999) 123-45-67, example@email.com"
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def start_edit_name(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Начинает процесс редактирования имени"""
    try:
        await state.update_data(edit_application_id=application_id)
        await state.set_state(EditStates.waiting_edit_name)

        application = applications_manager.get_application_by_id(application_id)
        current_name = application.get("name", "") if application else ""

        await callback_query.message.answer(
            f"👤 Введите новое имя для заявки ID: {application_id}\n\n"
            f"Текущее имя: {current_name if current_name else 'не указано'}\n\n"
            "Пример: Иванов Иван Иванович"
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)


async def start_edit_purchaser_comment(
    callback_query: CallbackQuery, state: FSMContext, application_id: int
):
    """Начинает процесс редактирования комментария закупщика"""
    try:
        await state.update_data(edit_application_id=application_id)
        await state.set_state(EditStates.waiting_edit_purchaser_comment)

        application = applications_manager.get_application_by_id(application_id)
        current_purchaser_comment = application.get("purchaser_comment", "") if application else ""

        await callback_query.message.answer(
            f"💼 Введите новый комментарий закупщика для заявки ID: {application_id}\n\n"
            f"Текущий комментарий закупщика: {current_purchaser_comment if current_purchaser_comment else 'не указан'}\n\n"
            "Пример: Товар заказан, ожидаем поставку"
        )
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Ошибка: {e}", show_alert=True)
