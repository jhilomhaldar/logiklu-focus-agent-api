from typing import Any, Dict, List, Optional

from app.config import settings
from app.db.client import get_client_connection, validate_database_name


SCHEMA_VERSION = "logiklu_role.v1"


def normalize_role_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role_id": row.get("id"),
        "role_code": row.get("type_code"),
        "role_name": row.get("type_name"),        
        "description": row.get("description"),
    }


def fetch_roles(
    search: Optional[str] = None,
    role_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    where_clauses = [
        "is_active = 1",
        "parent_id IS NOT NULL",
        "parent_id > 0",
    ]

    params: List[Any] = []

    if role_code:
        where_clauses.append("type_code = %s")
        params.append(str(role_code).strip())

    if search:
        search_value = "%" + str(search).strip() + "%"

        where_clauses.append(
            """
            (
                type_code LIKE %s
                OR type_name LIKE %s
                OR description LIKE %s
            )
            """
        )

        params.extend([
            search_value,
            search_value,
            search_value,
        ])

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(master_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    id,
                    type_code,
                    parent_id,
                    type_name,
                    description,
                    is_active,
                    sort_ord
                FROM logiklu_user_types
                WHERE {where_sql}
                ORDER BY
                    sort_ord ASC,
                    type_name ASC,
                    id ASC
            """

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        return [normalize_role_row(row) for row in rows]

    finally:
        if connection:
            connection.close()


def fetch_role_by_code(role_code: str) -> Optional[Dict[str, Any]]:
    if not role_code:
        return None

    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    try:
        connection = get_client_connection(master_database)

        with connection.cursor() as cursor:
            sql = """
                SELECT
                    id,
                    type_code,
                    parent_id,
                    type_name,
                    description,
                    is_active,
                    sort_ord
                FROM logiklu_user_types
                WHERE type_code = %s
                  AND is_active = 1
                  AND parent_id IS NOT NULL
                  AND parent_id > 0
                LIMIT 1
            """

            cursor.execute(sql, tuple([str(role_code).strip()]))
            row = cursor.fetchone()

        if not row:
            return None

        return normalize_role_row(row)

    finally:
        if connection:
            connection.close()