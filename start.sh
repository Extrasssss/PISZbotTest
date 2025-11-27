#!/bin/bash

set -e

echo "🔧 PISZBOT Startup Script"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    if [ -f .env.example ]; then
        echo "📝 Copying .env.example to .env..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your actual settings:"
        echo "   nano .env"
        echo "   Then run this script again: ./start.sh"
    else
        echo "❌ .env.example also not found!"
        echo "📝 Create .env file manually with required variables:"
        echo "   BOT_TOKEN, SERVER_IP, DB_NAME, SQL_LOGIN, SQL_PASSWORD"
    fi
    exit 1
fi

# Проверяем что .env не содержит примеры значений
if grep -q "your_telegram_bot_token_here" .env || \
   grep -q "your_server_ip" .env || \
   grep -q "your_database_name" .env; then
    echo "❌ .env file contains example values!"
    echo "📝 Please edit .env file with your actual settings:"
    echo "   nano .env"
    exit 1
fi

# Загружаем переменные окружения
set -a
source .env
set +a

# Проверяем обязательные переменные
required_vars=("BOT_TOKEN" "SERVER_IP" "DB_NAME" "SQL_LOGIN" "SQL_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required variable $var is not set in .env file"
        exit 1
    fi
done

echo "✅ Configuration validated successfully"
echo "🐍 Starting PISZBOT with Python..."

# Запускаем приложение
exec python run.py