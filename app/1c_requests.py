import pyodbc
from config import SERVER_IP, DB_NAME, SQL_LOGIN, SQL_PASSWORD


def connect_to_1c_77_sql(server_ip, db_name, sql_login, sql_password):
    try:
        conn = pyodbc.connect(
            f"DRIVER={{SQL Server}};"
            f"SERVER={server_ip};"
            f"DATABASE={db_name};"
            f"UID={sql_login};"
            f"PWD={sql_password}"
        )
        print("Успешное подключение к SQL-серверу 1С 7.7!")
        return conn
    except Exception as e:
        print(f"Ошибка SQL-подключения: {e}")
        return None


if __name__ == "__main__":
    server_ip = SERVER_IP
    db_name = DB_NAME
    sql_login = SQL_LOGIN
    sql_password = SQL_PASSWORD

    sql_connection = connect_to_1c_77_sql(server_ip, db_name,
                                          sql_login, sql_password)
    if sql_connection:
        cursor = sql_connection.cursor()
        cursor.execute("SELECT TOP (1000) [nomen_code], [nomen_id], [nomen_name], [sklad_name], [count_] FROM [torgpi].[dbo].[nomen_bot] where [nomen_code] = '1205363'")  # пример таблицы
        rows = cursor.fetchall()
        for row in rows:
            print(row)
