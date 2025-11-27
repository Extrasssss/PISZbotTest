#!/usr/bin/env python3
import os
import sys
import sqlite3

def health_check():
    try:
        # Проверяем обязательные переменные
        required_vars = ['BOT_TOKEN', 'SERVER_IP', 'DB_NAME', 'SQL_LOGIN', 'SQL_PASSWORD']
        for var in required_vars:
            if not os.getenv(var):
                print(f"Missing environment variable: {var}")
                return False
        
        # Проверяем базу данных
        if os.path.exists('applications.db'):
            with sqlite3.connect('applications.db') as conn:
                conn.execute("SELECT 1")
        
        print("Health check passed")
        return True
        
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if health_check() else 1)