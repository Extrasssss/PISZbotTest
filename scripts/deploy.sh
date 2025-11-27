#!/bin/bash
set -e

echo "🚀 Starting PISZBOT deployment..."

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Create .env from .env.example and configure it first"
    exit 1
fi

# Проверка обязательных переменных
source .env
required_vars=("BOT_TOKEN" "SERVER_IP" "DB_NAME" "SQL_LOGIN" "SQL_PASSWORD")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Please set $var in .env file"
        exit 1
    fi
done

echo "✅ Environment configuration verified"

# Останавливаем старые контейнеры
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Пересобираем и запускаем
echo "🔨 Building and starting new container..."
docker-compose up -d --build

echo "✅ Deployment completed!"
echo "📊 Check status: docker-compose ps"
echo "📋 View logs: docker-compose logs -f"