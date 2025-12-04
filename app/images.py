import datetime
import os
from io import BytesIO

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from aiogram import Dispatcher
from aiogram.fsm.state import State, StatesGroup



dp = Dispatcher()


current_time = datetime.datetime.now()
r_time = current_time.strftime("%H:%M %d-%m-%Y")
user_search_sessions = {}


class ReportStates(StatesGroup):
    waiting_email = State()


class Add(StatesGroup):
    article = State()
    title = State()
    number = State()
    name = State()
    publisher = State()
    purchiser = State()
    comment = State()
    cont_q = State()
    approve = State()
    senders = State()
    neverbook = State()
    neverbook_number = State()
    neverbook_name = State()
    neverbook_senders = State()
    neverbook_comment = State()
    old_year_confirm = State()
    employee = State()
    neverbook_employee = State()
    new_request = State()
    baza_state1 = State()  # В поисковике
    baza_state2 = State()  # В заявке


# ======================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ
# ======================

def get_book_image_path(filepath: str) -> str:
    """Преобразует путь из базы данных в полный путь к файлу"""
    try:
        if not filepath or not isinstance(filepath, str):
            return None

        # Очищаем путь от лишних символов
        clean_path = filepath.strip().replace('"', "").replace("'", "")
        clean_path = clean_path.replace("\\", "/").replace("//", "/")

        # Базовый путь к папке с изображениями - ИЗМЕНЕНИЕ ТОЛЬКО ЗДЕСЬ
        base_image_path = "/mnt/images"  # ✅ Изменили путь для Docker

        # Формируем полный путь
        full_path = os.path.join(base_image_path, clean_path)

        # Проверяем существование файла
        if os.path.exists(full_path):
            return full_path
        else:
            print(f"Image file not found: {full_path}")
            return None

    except Exception as e:
        print(f"Error getting book image path: {e}")
        return None


def create_format_comparison_image(book_format: str):
    """Создает изображение с наложением форматов (стандартный сверху)"""
    try:
        # Стандартный формат для сравнения
        STANDARD_FORMAT = "115x180"

        # Парсим форматы
        book_width, book_height = parse_format(book_format)
        standard_width, standard_height = parse_format(STANDARD_FORMAT)

        if book_width is None or book_height is None:
            return None

        # Создаем одну фигуру
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))

        # Масштабируем для лучшего отображения
        max_dim = max(book_width, book_height, standard_width, standard_height)
        scale = 300 / max_dim

        book_w_scaled = book_width * scale
        book_h_scaled = book_height * scale
        std_w_scaled = standard_width * scale
        std_h_scaled = standard_height * scale

        # Сначала рисуем книжный формат (как фон)
        rect_book = patches.Rectangle(
            (0, 0),
            book_w_scaled,
            book_h_scaled,
            linewidth=4,
            edgecolor="#A23B72",
            facecolor="#F18FBC",
            alpha=0.7,
        )
        ax.add_patch(rect_book)

        # Затем рисуем стандартный формат поверх книжного
        rect_std = patches.Rectangle(
            (0, 0),
            std_w_scaled,
            std_h_scaled,
            linewidth=4,
            edgecolor="#2E86AB",
            facecolor="#A9D6E5",
            alpha=0.8,
        )
        ax.add_patch(rect_std)

        # Настраиваем оси
        max_width = max(book_w_scaled, std_w_scaled)
        max_height = max(book_h_scaled, std_h_scaled)
        ax.set_xlim(0, max_width + 50)
        ax.set_ylim(0, max_height + 50)
        ax.set_aspect("equal")

        # Добавляем подписи размеров для стандартного формата (сверху)
        ax.text(
            std_w_scaled / 2,
            std_h_scaled + 15,
            f"{standard_width}×{standard_height} мм",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color="#2E86AB",
        )
        ax.text(
            std_w_scaled / 2,
            std_h_scaled + 5,
            "стандартный покет АСТ",
            ha="center",
            va="bottom",
            fontsize=12,
            color="#2E86AB",
            style="italic",
        )

        # Добавляем подписи размеров для книжного формата
        ax.text(
            book_w_scaled / 2,
            book_h_scaled + 30,
            f"{book_width}×{book_height} мм",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
            color="#A23B72",
        )
        ax.text(
            book_w_scaled / 2,
            book_h_scaled + 20,
            "ваша книга",
            ha="center",
            va="bottom",
            fontsize=12,
            color="#A23B72",
            style="italic",
        )

        # Убираем оси
        ax.set_xticks([])
        ax.set_yticks([])

        # Убираем рамку
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        plt.tight_layout()

        # Сохраняем в буфер
        buffer = BytesIO()
        plt.savefig(
            buffer,
            format="png",
            dpi=100,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
            pad_inches=0.1,
        )
        buffer.seek(0)
        plt.close()

        return buffer

    except Exception as e:
        print(f"Error creating format comparison image: {e}")
        plt.close()
        return None


def parse_format(format_str: str):
    """Парсит строку формата в ширину и высоту"""
    try:
        # Убираем пробелы и приводим к нижнему регистру
        format_str = format_str.strip().lower()

        # Разные варианты разделителей
        separators = ["x", "х", "*", "×", " "]

        for sep in separators:
            if sep in format_str:
                parts = format_str.split(sep)
                if len(parts) == 2:
                    # Извлекаем числа из строки
                    width = extract_number(parts[0])
                    height = extract_number(parts[1])
                    if width and height:
                        return width, height

        # Если не нашли разделитель, пробуем извлечь два числа подряд
        numbers = extract_all_numbers(format_str)
        if len(numbers) >= 2:
            return numbers[0], numbers[1]

        return None, None

    except Exception as e:
        print(f"Error parsing format {format_str}: {e}")
        return None, None


def extract_number(text: str):
    """Извлекает первое число из текста"""
    import re

    numbers = re.findall(r"\d+", text)
    return int(numbers[0]) if numbers else None


def extract_all_numbers(text: str):
    """Извлекает все числа из текста"""
    import re

    numbers = re.findall(r"\d+", text)
    return [int(num) for num in numbers]
