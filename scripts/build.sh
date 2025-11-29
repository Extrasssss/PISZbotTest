#!/bin/bash

set -e

echo "🔨 Building PISZBOT Docker image..."

# Очистка кэша Python
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete

# Проверка обязательных файлов
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found, using .env.example"
    cp .env.example .env
    echo "📝 Please edit .env file before running in production"
fi

# Сборка образа
docker build -t piszbot .

echo "✅ Build completed!"
echo "🐳 Image: piszbot"