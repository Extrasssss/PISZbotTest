import pyodbc
import subprocess
import sys

def check_system_info():
    """Проверяет информацию о системе"""
    print("=" * 50)
    print("🔍 ДИАГНОСТИКА СИСТЕМЫ И ODBC ДРАЙВЕРОВ")
    print("=" * 50)
    
    # Проверяем разрядность Python
    print(f"🐍 Версия Python: {sys.version}")
    print(f"📊 Разрядность Python: {'64-bit' if sys.maxsize > 2**32 else '32-bit'}")
    print(f"📦 Версия pyodbc: {pyodbc.version}")

def check_odbc_drivers():
    """Проверяет доступные ODBC драйверы"""
    print("\n📋 ДОСТУПНЫЕ ODBC ДРАЙВЕРЫ:")
    print("-" * 30)
    
    try:
        drivers = pyodbc.drivers()
        if not drivers:
            print("❌ Не найдено ни одного ODBC драйвера!")
            return False
        
        for i, driver in enumerate(drivers, 1):
            print(f"{i:2d}. {driver}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка драйверов: {e}")
        return False

def check_data_sources():
    """Проверяет зарегистрированные источники данных"""
    print("\n📊 ЗАРЕГИСТРИРОВАННЫЕ ИСТОЧНИКИ ДАННЫХ:")
    print("-" * 40)
    
    try:
        sources = pyodbc.dataSources()
        if not sources:
            print("❌ Не найдено зарегистрированных источников данных")
            return False
        
        for name, description in sources.items():
            print(f"🔹 {name} -> {description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при получении источников данных: {e}")
        return False

def test_driver_connection(driver_name, server, database, username, password):
    """Тестирует подключение с конкретным драйвером"""
    print(f"\n🧪 ТЕСТИРУЕМ ДРАЙВЕР: {driver_name}")
    print("-" * 35)
    
    try:
        # Пробуем разные варианты строк подключения
        connection_strings = [
            # Вариант 1: Стандартный
            f"DRIVER={{{driver_name}}};SERVER={server};DATABASE={database};UID={username};PWD={password};Trusted_Connection=no;Encrypt=no;",
            # Вариант 2: С портом
            f"DRIVER={{{driver_name}}};SERVER={server},1433;DATABASE={database};UID={username};PWD={password};Trusted_Connection=no;Encrypt=no;",
            # Вариант 3: Без указания базы
            f"DRIVER={{{driver_name}}};SERVER={server};UID={username};PWD={password};Trusted_Connection=no;Encrypt=no;"
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            print(f"Попытка {i}: {conn_str[:80]}...")
            try:
                connection = pyodbc.connect(conn_str, timeout=10)
                cursor = connection.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                connection.close()
                print(f"✅ УСПЕХ! Драйвер работает: {driver_name}")
                print(f"📋 Версия SQL: {version[:100]}...")
                return True
                
            except pyodbc.Error as e:
                print(f"❌ Ошибка: {e}")
                continue
                
        return False
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return False

def main():
    """Основная функция диагностики"""
    check_system_info()
    
    # Проверяем драйверы
    if not check_odbc_drivers():
        print("\n🚨 ПРОБЛЕМА: Не установлены ODBC драйверы!")
        print("\n💡 РЕШЕНИЕ:")
        print("1. Скачайте и установите ODBC Driver for SQL Server")
        print("2. Убедитесь, что разрядность драйвера совпадает с разрядностью Python")
        print("3. Перезагрузите компьютер после установки")
        return
    
    check_data_sources()
    
    # Тестируем подключение
    print("\n" + "=" * 50)
    print("🧪 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К 1С")
    print("=" * 50)
    
    # Параметры подключения (замените на свои)
    config = {
        'server': '192.168.0.251\\analytics',
        'database': 'torgnew',
        'username': 'reader',
        'password': 'T00r_reader_@42'
    }
    
    drivers = pyodbc.drivers()
    
    success = False
    for driver in drivers:
        if 'SQL Server' in driver or 'ODBC' in driver:
            if test_driver_connection(driver, **config):
                success = True
                break
    
    if not success:
        print("\n🚨 НИ ОДИН ДРАЙВЕР НЕ СРАБОТАЛ!")
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        print("1. Установите Microsoft ODBC Driver 17 for SQL Server")
        print("2. Проверьте правильность параметров подключения")
        print("3. Убедитесь, что сервер доступен по сети")
        print("4. Проверьте логин и пароль")

if __name__ == "__main__":
    main()