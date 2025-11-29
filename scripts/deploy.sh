#!/bin/bash
set -e

echo "🚀 Starting PISZBOT deployment..."

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Create .env from .env.example and configure it first"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found!"
    exit 1
fi

# Проверка Docker Compose v2
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose v2 not available"
    echo "💡 Try: docker-compose --version to check for v1"
    exit 1
fi

echo "✅ Docker Compose v2 detected"

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
docker compose down || true

# Пересобираем и запускаем
echo "🔨 Building and starting new container..."
docker compose up -d --build

echo "✅ Deployment completed!"
echo "📊 Check status: docker compose ps"
echo "📋 View logs: docker compose logs -f"