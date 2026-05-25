import pymysql
from pymysql.cursors import DictCursor

from app.config import settings


def get_master_connection():
    """
    Create a connection to LogiKlu master database.
    This is used to resolve clients, API keys, permissions, and central settings.
    """
    return pymysql.connect(
        host=settings.MASTER_DB_HOST,
        port=settings.MASTER_DB_PORT,
        user=settings.MASTER_DB_USER,
        password=settings.MASTER_DB_PASSWORD,
        database=settings.MASTER_DB_NAME,
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=20,
        write_timeout=20,
        charset="utf8mb4",
    )


def test_master_connection() -> dict:
    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS database_name, NOW() AS server_time")
            row = cursor.fetchone()

        return {
            "connected": True,
            "database_name": row.get("database_name"),
            "server_time": str(row.get("server_time")),
        }

    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
        }

    finally:
        if connection:
            connection.close()