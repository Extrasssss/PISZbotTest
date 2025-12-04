import os
import asyncio
import logging
import sys

# Добавляем путь для импортов в Docker
sys.path.append('/app')

from aiogram import Bot, Dispatcher
from app.email_service.report_service import setup_weekly_report_scheduler
from app import router
from app.search_system.ss_utils import start_periodic_cleanup
from app.onec_requests import DatabaseMiddleware
from config import Config  # ✅ Используем Config вместо TOKEN

import app.images
import app.handlers
import app.search_system.search_system
import app.search_system.ss_handlers
import app.search_system.ss_results
import app.search_system.ss_utils
import app.order_desk_requests.od_history_handlers
import app.order_desk_requests.od_requests
import app.inner_db.inner_db
import app.email_service.email_service
import app.email_service.report_service
import app.email_service.rs_handlers


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