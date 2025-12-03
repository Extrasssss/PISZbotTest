services:
  piszbot:
    build: .
    container_name: piszbot
    restart: unless-stopped
    env_file:
      - .env
    network_mode: "host"
    user: "1000:1000"  # 🆕 ДОБАВЬТЕ ЭТУ СТРОКУ
    environment:
      - DB_PATH=/app/data/applications.db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
      - /mnt/md3/servers/imagessmb/images:/mnt/images:ro
      - ./cache:/app/cache
[app@podpisnie PISZbotTest]$ cat check-config.py
#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

def check_config():
    print("🔍 Checking configuration...")

    config = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'SERVER_IP': os.getenv('SERVER_IP'),
        'DB_NAME': os.getenv('DB_NAME'),
        'SQL_LOGIN': os.getenv('SQL_LOGIN'),
        'SQL_PASSWORD': os.getenv('SQL_PASSWORD'),
        'ADMIN_IDS': os.getenv('ADMIN_IDS')
    }

    all_good = True

    for key, value in config.items():
        if not value or value.startswith('your_') or '***' in value:
            print(f"❌ {key}: NOT SET")
            all_good = False
        else:
            print(f"✅ {key}: Set")

    if all_good:
        print("\n🎉 Configuration is ready!")
    else:
        print("\n⚠️  Please complete the configuration in .env file")

if __name__ == "__main__":
    check_config()[app@podpisnie PISZbotTest]$ cat Dockerfile
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

# 1. Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Копируем исходный код (dockerignore исключит data/, applications.db и т.д.)
COPY . .

# 3. Создаем структуру директорий
RUN mkdir -p /app/data /app/logs /app/reports /app/cache

# 4. Удаляем случайно скопированные файлы БД (на всякий случай)
RUN rm -f /app/applications.db 2>/dev/null || true
RUN rm -rf /app/data/* 2>/dev/null || true

# 5. Создаем пользователя
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g ${GROUP_ID} appgroup && \
    useradd -u ${USER_ID} -g appgroup -m -s /bin/bash appuser && \
    chown -R ${USER_ID}:${GROUP_ID} /app

USER appuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "run.py"]