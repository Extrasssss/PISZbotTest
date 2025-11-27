#!/bin/bash
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="piszbot_backup_${TIMESTAMP}"

echo "💾 Starting backup..."

mkdir -p "$BACKUP_DIR"

# Бэкап базы данных
if [ -f "applications.db" ]; then
    cp "applications.db" "${BACKUP_DIR}/${BACKUP_NAME}.db"
    echo "✅ Database backed up"
fi

# Бэкап конфигурации
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" \
    ".env" "config.py" "requirements.txt" \
    2>/dev/null || true

echo "✅ Backup completed: ${BACKUP_NAME}"