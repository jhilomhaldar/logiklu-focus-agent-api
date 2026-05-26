import re
from typing import Optional

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings


DB_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_database_name(database_name: str) -> str:
    """
    Prevent SQL/database injection.
    Database names cannot be parameterized in MySQL,
    so we strictly allow only letters, numbers and underscore.
    """
    if not database_name:
        raise ValueError("Client database name is empty")

    if not DB_NAME_PATTERN.match(database_name):
        raise ValueError("Invalid client database name")

    return database_name


def get_client_connection(client_database: str):
    """
    Create a connection to the authenticated client's database.
    """
    safe_database = validate_database_name(client_database)

    return pymysql.connect(
        host=settings.MASTER_DB_HOST,
        port=settings.MASTER_DB_PORT,
        user=settings.MASTER_DB_USER,
        password=settings.MASTER_DB_PASSWORD,
        database=safe_database,
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        charset="utf8mb4",
    )


def test_client_connection(client_database: str) -> dict:
    connection = None

    try:
        connection = get_client_connection(client_database)

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