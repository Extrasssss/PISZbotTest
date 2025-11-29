#!/bin/bash

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if ! command -v python &> /dev/null; then
        error "Python is not installed or not in PATH"
        exit 1
    fi
    
    PYTHON_VERSION=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    log "Python version: $PYTHON_VERSION"
}

check_dependencies() {
    log "Checking Python dependencies..."
    if ! python -c "import aiogram, sqlalchemy" &> /dev/null; then
        error "Missing required Python dependencies"
        log "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
    fi
}

setup_environment() {
    if [ ! -f .env ]; then
        warn ".env file not found"
        if [ -f .env.example ]; then
            log "Creating .env from .env.example..."
            cp .env.example .env
            error "Please edit .env file with your actual settings and run again"
            exit 1
        else
            error ".env.example not found. Please create .env file manually"
            exit 1
        fi
    fi

    # Проверяем что значения заменены
    if grep -q -E "your_|example|placeholder" .env; then
        error ".env file contains example values. Please update with real values"
        exit 1
    fi

    # Загружаем .env
    set -a
    source .env
    set +a
}

validate_config() {
    local required_vars=("BOT_TOKEN" "SERVER_IP" "DB_NAME" "SQL_LOGIN" "SQL_PASSWORD")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi
}

create_directories() {
    local dirs=("reports" "logs" "data")
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log "Creating directory: $dir"
            mkdir -p "$dir"
        fi
    done
}

main() {
    log "🚀 Starting PISZBOT..."
    
    check_python
    check_dependencies
    setup_environment
    validate_config
    create_directories
    
    log "✅ All checks passed"
    log "🐍 Starting application..."
    
    # Запускаем приложение
    exec python run.py
}

# Обработка сигналов
trap 'log "Shutting down..."; exit 0' SIGINT SIGTERM

main "$@"