FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    unixodbc-dev \
    freetds-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем зависимости первыми для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/data /app/reports

# Создаем безопасного пользователя
RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /app
USER app

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "run.py"]