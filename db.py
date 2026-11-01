import pymysql
import settings

def execute(sql: str, args: dict|None=None):
    connection = pymysql.connect(
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        port=settings.DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor  # Returns rows as dictionaries instead of tuples
    )

    if args is None:
        args = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()
    finally:
        connection.close()