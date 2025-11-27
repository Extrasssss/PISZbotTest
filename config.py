import os
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

# Email Configuration (вне класса для обратной совместимости)
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.yandex.ru'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'email_from': os.getenv('EMAIL_FROM', 'robot@podpisnie.ru'),
    'email_password': os.getenv('EMAIL_PASSWORD'),
    'email_to': os.getenv('EMAIL_TO', 'zakupki@podpisnie.ru'),
    'weekly_report_emails': [
        'opg@podpisnie.ru',
        'zakupki@podpisnie.ru',
        'dmitrykiselevextrasssss@gmail.com'
    ]
}

class Config:
    """Безопасная конфигурация для Docker"""
    
    # Bot Configuration
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    # Database Configuration
    SERVER_IP = os.getenv('SERVER_IP')
    DB_NAME = os.getenv('DB_NAME') 
    SQL_LOGIN = os.getenv('SQL_LOGIN')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD')
    
    # Email Configuration (дублируем для удобства)
    EMAIL_CONFIG = EMAIL_CONFIG
    
    # Admin Configuration
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 1125363386))
    
    # Current time
    r_time = datetime.now().strftime("%d.%m.%Y %H:%M")

# Алиасы для обратной совместимости
TOKEN = Config.TOKEN