import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.email_service.report_service import setup_weekly_report_scheduler
from app.handlers import router, start_periodic_cleanup
from app.onec_requests import DatabaseMiddleware
from config import TOKEN

# from app.database.models import async_main

bot = Bot(token=TOKEN)
dp = Dispatcher()


dp.update.middleware(DatabaseMiddleware())


async def main():
    dp.include_router(router)
    setup_weekly_report_scheduler()
    asyncio.create_task(start_periodic_cleanup())
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
