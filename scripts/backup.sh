#!/bin/bash
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="piszbot_backup_${TIMESTAMP}"

echo "💾 Starting backup..."

mkdir -p "$BACKUP_DIR"

# Бэкап Docker volumes (если используются)
if docker volume ls | grep -q piszbot_data; then
    echo "📦 Backing up Docker volumes..."
    docker run --rm -v piszbot_data:/source -v $(pwd)/$BACKUP_DIR:/backup alpine \
        tar -czf /backup/${BACKUP_NAME}_data.tar.gz -C /source .
fi

# Бэкап базы данных
if [ -f "applications.db" ]; then
    cp "applications.db" "${BACKUP_DIR}/${BACKUP_NAME}.db"
    echo "✅ Database backed up"
fi

# Бэкап конфигурации
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" \
    ".env" "config.py" "requirements.txt" "docker-compose.yml" \
    2>/dev/null || true

echo "✅ Backup completed: ${BACKUP_NAME}"