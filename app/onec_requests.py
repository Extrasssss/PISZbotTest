from typing import Any, Awaitable, Callable, Dict

import pyodbc
from aiogram import BaseMiddleware
from aiogram.types import Message

import config

import os
from dotenv import load_dotenv

load_dotenv()

SERVER_IP = os.getenv('SERVER_IP')
DB_NAME = os.getenv('DB_NAME')
SQL_LOGIN = os.getenv('SQL_LOGIN')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.connection = None

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Подключаемся к базе данных если соединение не установлено
        if not self.connection:
            self.connection = self.connect_to_1c_77_sql()

        # Добавляем соединение в данные, которые передаются в хэндлер
        data["db_connection"] = self.connection

        # Вызываем следующий middleware или хэндлер
        return await handler(event, data)

    def connect_to_1c_77_sql(self):
        """Установка соединения с SQL Server"""
        try:
            conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={SERVER_IP};"
                f"DATABASE={DB_NAME};"
                f"UID={SQL_LOGIN};"
                f"PWD={SQL_PASSWORD}"
            )
            print("Успешное подключение к SQL-серверу 1С 7.7!")
            return conn
        except Exception as e:
            print(f"Ошибка SQL-подключения: {e}")
            return None

    async def close_connection(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("Соединение с базой данных закрыто")
