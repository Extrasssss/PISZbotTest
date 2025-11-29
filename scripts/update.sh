#!/bin/bash
set -e

echo "🔄 Updating PISZBOT..."

# Автоопределение compose команды
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Git pull (если используется)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes..."
    git pull
fi

# Перезапуск
echo "🔁 Restarting containers..."
$COMPOSE_CMD down
$COMPOSE_CMD up -d --build

echo "✅ Update completed!"