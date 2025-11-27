#!/bin/bash
set -e

echo "🔄 Updating PISZBOT..."

# Если используете Git
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull
fi

# Перезапускаем контейнеры
./scripts/deploy.sh

echo "✅ Update completed!"