from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, session


class DataMiddleware(BaseMiddleware):
    def __init__(self
                 session: async_sessionmaker[AsyncSession]) -> None:
    self.session = session
    
    async def __call__(self, 
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        async with self.session() as session:
            db = Database(session=session)
            data['db'] = db
            return await handler(event, data)