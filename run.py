import os
import asyncio
import logging
import sys

# Добавляем путь для импортов в Docker
sys.path.append('/app')

from aiogram import Bot, Dispatcher
from app.email_service.report_service import setup_weekly_report_scheduler
from app.handlers import router, start_periodic_cleanup
from app.onec_requests import DatabaseMiddleware
from config import Config  # ✅ Используем Config вместо TOKEN

async def main():
    # Настройка логирования для Docker
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]  # ✅ Важно для Docker
    )
    
    # Инициализация бота
    bot = Bot(token=Config.TOKEN)  # ✅ Используем Config.TOKEN
    dp = Dispatcher()
    
    # Middleware
    dp.update.middleware(DatabaseMiddleware())
    
    try:
        dp.include_router(router)
        setup_weekly_report_scheduler()
        asyncio.create_task(start_periodic_cleanup())
        
        logging.info("🚀 Bot starting...")
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logging.error(f"❌ Bot crashed: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")