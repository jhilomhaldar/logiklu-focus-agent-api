import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_leadform.v1"


LEADFORM_SEARCH_FIELDS = {
    "id": "form_id",
    "form_id": "form_id",
    "name": "form_name",
    "form_name": "form_name",
    "description": "description",
    "form_json": "form_json",
    "custom_css": "custom_css",
    "assigned_admins": "assigned_admins",
    "assign_owner": "assign_owner",
    "created_by": "created_by",
    "modified_by": "modified_by",
    "is_active": "is_active",
    "active_status": "active_status",
    "embed_id": "embed_id",
    "embed_name": "embed_name",
    "embed_description": "embed_description",
    "setting": "setting",
    "submit_message": "submit_message",
    "redirect_url": "redirect_url",
    "email_subject_user": "email_subject_user",
    "email_subject_admin": "email_subject_admin",
    "created_date": "created_date",
    "modified_date": "modified_date",
}


TEXT_FIELDS = {
    "form_name",
    "name",
    "description",
    "form_json",
    "custom_css",
    "assigned_admins",
    "embed_name",
    "embed_description",
    "setting",
    "submit_message",
    "redirect_url",
    "email_subject_user",
    "email_subject_admin",
}


EXACT_FIELDS = {
    "id",
    "form_id",
    "embed_id",
    "is_active",
    "active_status",
    "created_by",
    "modified_by",
    "assign_owner",
}


DATE_FIELDS = {
    "created_date": "lf.created_date",
    "modified_date": "lf.modified_date",
}


def safe_json_decode(value: Any, default: Any = None) -> Any:
    if default is None:
        default = {}

    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    if not isinstance(value, str):
        return default

    value = value.strip()

    if not value:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def parse_json_or_string_list(value: Any) -> list:
    if value is None:
        return []

    decoded = safe_json_decode(value, None)

    if isinstance(decoded, list):
        return decoded

    if isinstance(decoded, dict):
        return [decoded]

    value_string = str(value or "").strip()

    if not value_string:
        return []

    return [
        item.strip()
        for item in value_string.split(",")
        if item.strip()
    ]


def to_number(value: Any) -> Any:
    if value is None:
        return 0

    if isinstance(value, Decimal):
        value = float(value)

    try:
        number = float(value)
    except Exception:
        return 0

    if number.is_integer():
        return int(number)

    return number


def to_int(value: Any) -> int:
    if value is None:
        return 0

    try:
        return int(float(value))
    except Exception:
        return 0


def format_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    return str(value)


def format_date(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def normalize_start_datetime(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if len(value) == 10:
        return f"{value} 00:00:00"

    return value


def normalize_end_datetime(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if len(value) == 10:
        return f"{value} 23:59:59"

    return value


def normalize_date_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if len(value) >= 10:
        return value[:10]

    return value


def split_filter_values(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    value_string = str(value).strip()

    if not value_string:
        return []

    try:
        parsed = json.loads(value_string)

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass

    return [item.strip() for item in value_string.split(",") if item.strip()]


def normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    value_string = str(value).strip().lower()

    if value_string in ["true", "1", "yes", "y"]:
        return True

    if value_string in ["false", "0", "no", "n"]:
        return False

    return None


def build_submission_date_condition(
    alias: str = "lfs",
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    date_from = normalize_date_value(submission_date_from)
    date_to = normalize_date_value(submission_date_to)
    date_time_from = normalize_start_datetime(submission_date_from)
    date_time_to = normalize_end_datetime(submission_date_to)

    if date_from and date_time_from:
        clauses.append(
            f"""
            (
                {alias}.track_date_time >= %s
                OR (
                    {alias}.track_date_time IS NULL
                    AND {alias}.track_date >= %s
                )
            )
            """
        )
        params.extend([date_time_from, date_from])

    if date_to and date_time_to:
        clauses.append(
            f"""
            (
                {alias}.track_date_time <= %s
                OR (
                    {alias}.track_date_time IS NULL
                    AND {alias}.track_date <= %s
                )
            )
            """
        )
        params.extend([date_time_to, date_to])

    if not clauses:
        return "", []

    return " AND " + " AND ".join(clauses), params


def build_form_submission_summary_subquery(
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    date_condition, params = build_submission_date_condition(
        alias="lfs",
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
    )

    sql = f"""
        SELECT
            lfe.form_id,
            COUNT(lfs.id) AS total_submissions,
            MIN(COALESCE(lfs.track_date_time, CAST(lfs.track_date AS DATETIME))) AS first_submission_at,
            MAX(COALESCE(lfs.track_date_time, CAST(lfs.track_date AS DATETIME))) AS last_submission_at
        FROM leadform_form_embed lfe
        INNER JOIN lk_leadform_form_submission lfs
            ON lfs.form_embed_id = lfe.id
        WHERE lfe.active_status <> 'deleted'
        {date_condition}
        GROUP BY lfe.form_id
    """

    return sql, params


def build_embed_submission_summary_subquery(
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    date_condition, params = build_submission_date_condition(
        alias="lfs",
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
    )

    sql = f"""
        SELECT
            lfs.form_embed_id,
            COUNT(lfs.id) AS total_submissions,
            MIN(COALESCE(lfs.track_date_time, CAST(lfs.track_date AS DATETIME))) AS first_submission_at,
            MAX(COALESCE(lfs.track_date_time, CAST(lfs.track_date AS DATETIME))) AS last_submission_at
        FROM lk_leadform_form_submission lfs
        WHERE 1=1
        {date_condition}
        GROUP BY lfs.form_embed_id
    """

    return sql, params


def build_embed_exists_condition(
    embed_where_sql: str = "",
) -> str:
    return f"""
        EXISTS (
            SELECT 1
            FROM leadform_form_embed lfe_exists
            WHERE lfe_exists.form_id = lf.id
              AND lfe_exists.active_status <> 'deleted'
              {embed_where_sql}
        )
    """


def build_submission_exists_condition(
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    date_condition, params = build_submission_date_condition(
        alias="lfs_exists",
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
    )

    sql = f"""
        EXISTS (
            SELECT 1
            FROM leadform_form_embed lfe_sub_exists
            INNER JOIN lk_leadform_form_submission lfs_exists
                ON lfs_exists.form_embed_id = lfe_sub_exists.id
            WHERE lfe_sub_exists.form_id = lf.id
              AND lfe_sub_exists.active_status <> 'deleted'
              {date_condition}
        )
    """

    return sql, params


def build_search_condition(
    search: Optional[str],
    search_by: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not search:
        return

    search_value_raw = str(search).strip()

    if not search_value_raw:
        return

    search_by_value = str(search_by or "").strip().lower()
    search_value = f"%{search_value_raw}%"

    if search_by_value == "searchby":
        search_by_value = ""

    if not search_by_value:
        where_clauses.append(
            """
            (
                lf.form_name LIKE %s
                OR lf.description LIKE %s
                OR lf.form_json LIKE %s
                OR lf.assigned_admins LIKE %s
                OR EXISTS (
                    SELECT 1
                    FROM leadform_form_embed lfe_search
                    WHERE lfe_search.form_id = lf.id
                      AND lfe_search.active_status <> 'deleted'
                      AND (
                            lfe_search.embed_name LIKE %s
                         OR lfe_search.description LIKE %s
                         OR CAST(lfe_search.setting AS CHAR) LIKE %s
                         OR lfe_search.submit_message LIKE %s
                         OR lfe_search.redirect_url LIKE %s
                         OR lfe_search.email_subject_user LIKE %s
                         OR lfe_search.email_subject_admin LIKE %s
                      )
                )
            )
            """
        )
        params.extend([search_value] * 11)
        return

    field = LEADFORM_SEARCH_FIELDS.get(search_by_value)

    if not field:
        return

    apply_single_field_condition(
        field=search_by_value,
        operator="like",
        value=search_value_raw,
        where_clauses=where_clauses,
        params=params,
    )


def add_in_condition(
    column: str,
    values: List[Any],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not values:
        return

    placeholders = ",".join(["%s"] * len(values))
    where_clauses.append(f"{column} IN ({placeholders})")
    params.extend(values)


def apply_embed_text_condition(
    column_name: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    values = split_filter_values(value)

    if operator == "in" and values:
        placeholders = ",".join(["%s"] * len(values))
        where_clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM leadform_form_embed lfe_filter
                WHERE lfe_filter.form_id = lf.id
                  AND lfe_filter.active_status <> 'deleted'
                  AND lfe_filter.{column_name} IN ({placeholders})
            )
            """
        )
        params.extend(values)
        return

    if not values:
        return

    single_value = values[0]

    if operator == "eq":
        comparison = "="
        filter_value = single_value
    elif operator == "neq":
        comparison = "<>"
        filter_value = single_value
    elif operator == "starts_with":
        comparison = "LIKE"
        filter_value = f"{single_value}%"
    elif operator == "ends_with":
        comparison = "LIKE"
        filter_value = f"%{single_value}"
    else:
        comparison = "LIKE"
        filter_value = f"%{single_value}%"

    where_clauses.append(
        f"""
        EXISTS (
            SELECT 1
            FROM leadform_form_embed lfe_filter
            WHERE lfe_filter.form_id = lf.id
              AND lfe_filter.active_status <> 'deleted'
              AND lfe_filter.{column_name} {comparison} %s
        )
        """
    )
    params.append(filter_value)


def apply_embed_id_condition(
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    values = split_filter_values(value)

    numeric_values: List[int] = []

    for item in values:
        try:
            numeric_values.append(int(item))
        except Exception:
            pass

    if not numeric_values:
        return

    if operator == "in" or len(numeric_values) > 1:
        placeholders = ",".join(["%s"] * len(numeric_values))
        where_clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM leadform_form_embed lfe_filter
                WHERE lfe_filter.form_id = lf.id
                  AND lfe_filter.active_status <> 'deleted'
                  AND lfe_filter.id IN ({placeholders})
            )
            """
        )
        params.extend(numeric_values)
        return

    where_clauses.append(
        """
        EXISTS (
            SELECT 1
            FROM leadform_form_embed lfe_filter
            WHERE lfe_filter.form_id = lf.id
              AND lfe_filter.active_status <> 'deleted'
              AND lfe_filter.id = %s
        )
        """
    )
    params.append(numeric_values[0])


def apply_single_field_condition(
    field: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    field = str(field or "").strip().lower()
    operator = str(operator or "eq").strip().lower()

    mapped_field = LEADFORM_SEARCH_FIELDS.get(field)

    if not mapped_field:
        return

    if mapped_field in ["form_id"]:
        values = split_filter_values(value)
        numeric_values: List[int] = []

        for item in values:
            try:
                numeric_values.append(int(item))
            except Exception:
                pass

        if not numeric_values:
            return

        if operator == "in" or len(numeric_values) > 1:
            add_in_condition("lf.id", numeric_values, where_clauses, params)
        elif operator == "neq":
            where_clauses.append("lf.id <> %s")
            params.append(numeric_values[0])
        else:
            where_clauses.append("lf.id = %s")
            params.append(numeric_values[0])

        return

    if mapped_field in ["created_by", "modified_by", "assign_owner"]:
        values = split_filter_values(value)
        numeric_values: List[int] = []

        for item in values:
            try:
                numeric_values.append(int(item))
            except Exception:
                pass

        if not numeric_values:
            return

        column = f"lf.{mapped_field}"

        if operator == "in" or len(numeric_values) > 1:
            add_in_condition(column, numeric_values, where_clauses, params)
        elif operator == "neq":
            where_clauses.append(f"{column} <> %s")
            params.append(numeric_values[0])
        else:
            where_clauses.append(f"{column} = %s")
            params.append(numeric_values[0])

        return

    if mapped_field in ["is_active", "active_status"]:
        values = split_filter_values(value)

        if not values:
            return

        column = f"lf.{mapped_field}"

        if operator == "in" or len(values) > 1:
            add_in_condition(column, values, where_clauses, params)
        elif operator == "neq":
            where_clauses.append(f"{column} <> %s")
            params.append(values[0])
        else:
            where_clauses.append(f"{column} = %s")
            params.append(values[0])

        return

    if mapped_field in ["created_date", "modified_date"]:
        column = DATE_FIELDS.get(mapped_field)

        if not column:
            return

        if operator in ["from", "gte", "after"]:
            where_clauses.append(f"{column} >= %s")
            params.append(normalize_start_datetime(value))
            return

        if operator in ["to", "lte", "before"]:
            where_clauses.append(f"{column} <= %s")
            params.append(normalize_end_datetime(value))
            return

        if operator == "between" and isinstance(value, list) and len(value) >= 2:
            where_clauses.append(f"{column} BETWEEN %s AND %s")
            params.extend(
                [
                    normalize_start_datetime(value[0]),
                    normalize_end_datetime(value[1]),
                ]
            )
            return

        return

    if mapped_field == "embed_id":
        apply_embed_id_condition(
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    embed_text_map = {
        "embed_name": "embed_name",
        "embed_description": "description",
        "setting": "setting",
        "submit_message": "submit_message",
        "redirect_url": "redirect_url",
        "email_subject_user": "email_subject_user",
        "email_subject_admin": "email_subject_admin",
    }

    if mapped_field in embed_text_map:
        column_name = embed_text_map[mapped_field]

        if column_name == "setting":
            values = split_filter_values(value)

            if not values:
                return

            single_value = values[0]

            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM leadform_form_embed lfe_filter
                    WHERE lfe_filter.form_id = lf.id
                      AND lfe_filter.active_status <> 'deleted'
                      AND CAST(lfe_filter.setting AS CHAR) LIKE %s
                )
                """
            )
            params.append(f"%{single_value}%")
            return

        apply_embed_text_condition(
            column_name=column_name,
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    form_text_columns = {
        "form_name": "lf.form_name",
        "name": "lf.form_name",
        "description": "lf.description",
        "form_json": "lf.form_json",
        "custom_css": "lf.custom_css",
        "assigned_admins": "lf.assigned_admins",
    }

    column = form_text_columns.get(mapped_field)

    if not column:
        return

    values = split_filter_values(value)

    if not values:
        return

    if operator == "in" and values:
        add_in_condition(column, values, where_clauses, params)
        return

    single_value = values[0]

    if operator == "eq":
        where_clauses.append(f"{column} = %s")
        params.append(single_value)
    elif operator == "neq":
        where_clauses.append(f"{column} <> %s")
        params.append(single_value)
    elif operator == "starts_with":
        where_clauses.append(f"{column} LIKE %s")
        params.append(f"{single_value}%")
    elif operator == "ends_with":
        where_clauses.append(f"{column} LIKE %s")
        params.append(f"%{single_value}")
    else:
        where_clauses.append(f"{column} LIKE %s")
        params.append(f"%{single_value}%")


def build_dynamic_filters(
    filters: Optional[List[Dict[str, Any]]],
) -> Tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []

    if not filters:
        return where_clauses, params

    for item in filters:
        if not isinstance(item, dict):
            continue

        field = str(item.get("field") or "").strip().lower()
        operator = str(item.get("operator") or "eq").strip().lower()
        value = item.get("value")

        if not field:
            continue

        apply_single_field_condition(
            field=field,
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )

    return where_clauses, params


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    has_embeds: Optional[bool] = None,
    has_submissions: Optional[bool] = None,
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Any]]:
    where_clauses = [
        "lf.active_status <> 'deleted'"
    ]

    params: List[Any] = []

    build_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    if has_embeds is not None:
        if has_embeds:
            where_clauses.append(build_embed_exists_condition())
        else:
            where_clauses.append(f"NOT {build_embed_exists_condition()}")

    submission_exists_sql, submission_exists_params = build_submission_exists_condition(
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
    )

    if has_submissions is not None:
        if has_submissions:
            where_clauses.append(submission_exists_sql)
        else:
            where_clauses.append(f"NOT {submission_exists_sql}")

        params.extend(submission_exists_params)

    elif submission_date_from or submission_date_to:
        where_clauses.append(submission_exists_sql)
        params.extend(submission_exists_params)

    dynamic_where, dynamic_params = build_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    return " AND ".join(where_clauses), params


def build_submission_summary(total: Any, first_at: Any, last_at: Any) -> Dict[str, Any]:
    return {
        "total_submissions": to_int(total),
        "first_submission_at": format_datetime(first_at),
        "last_submission_at": format_datetime(last_at),
    }


def normalize_embed_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "embed_id": row.get("embed_id"),
        "form_id": row.get("form_id"),
        "embed_name": row.get("embed_name"),
        "description": row.get("embed_description"),
        "setting": safe_json_decode(row.get("setting"), {}),
        "submit_message": row.get("submit_message"),
        "email_subject_user": row.get("email_subject_user"),
        "email_message_user": row.get("email_message_user"),
        "email_subject_admin": row.get("email_subject_admin"),
        "email_message_admin": row.get("email_message_admin"),
        "redirect_url": row.get("redirect_url"),
        "is_active": row.get("embed_is_active"),
        "active_status": row.get("embed_active_status"),
        "created_by": row.get("embed_created_by"),
        "created_date": format_datetime(row.get("embed_created_date")),
        "modified_by": row.get("embed_modified_by"),
        "modified_date": format_datetime(row.get("embed_modified_date")),
        "submission_summary": build_submission_summary(
            row.get("embed_total_submissions"),
            row.get("embed_first_submission_at"),
            row.get("embed_last_submission_at"),
        ),
    }


def normalize_leadform_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "form_id": row.get("form_id"),
        "form_template_id": row.get("form_template_id"),
        "form_name": row.get("form_name"),
        "description": row.get("description"),
        "form_json": safe_json_decode(row.get("form_json"), {}),
        "custom_css": row.get("custom_css"),
        "assigned_admins": parse_json_or_string_list(row.get("assigned_admins")),
        "assign_owner": row.get("assign_owner"),
        "created_by": row.get("created_by"),
        "created_date": format_datetime(row.get("created_date")),
        "modified_by": row.get("modified_by"),
        "modified_date": format_datetime(row.get("modified_date")),
        "is_active": row.get("is_active"),
        "active_status": row.get("active_status"),
        "embed_summary": {
            "total_embeds": to_int(row.get("total_embeds")),
            "active_embeds": to_int(row.get("active_embeds")),
        },
        "submission_summary": build_submission_summary(
            row.get("total_submissions"),
            row.get("first_submission_at"),
            row.get("last_submission_at"),
        ),
        "embeds": [],
    }


def fetch_leadform_embeds(
    client_database: str,
    form_ids: List[int],
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
) -> Dict[int, List[Dict[str, Any]]]:
    if not form_ids:
        return {}

    connection = None

    try:
        connection = get_client_connection(client_database)

        placeholders = ",".join(["%s"] * len(form_ids))

        embed_submission_subquery, embed_submission_params = build_embed_submission_summary_subquery(
            submission_date_from=submission_date_from,
            submission_date_to=submission_date_to,
        )

        sql = f"""
            SELECT
                lfe.id AS embed_id,
                lfe.form_id,
                lfe.embed_name,
                lfe.description AS embed_description,
                lfe.setting,
                lfe.submit_message,
                lfe.email_subject_user,
                lfe.email_message_user,
                lfe.email_subject_admin,
                lfe.email_message_admin,
                lfe.redirect_url,
                lfe.created_by AS embed_created_by,
                lfe.created_date AS embed_created_date,
                lfe.modified_by AS embed_modified_by,
                lfe.modified_date AS embed_modified_date,
                lfe.is_active AS embed_is_active,
                lfe.active_status AS embed_active_status,

                COALESCE(ess.total_submissions, 0) AS embed_total_submissions,
                ess.first_submission_at AS embed_first_submission_at,
                ess.last_submission_at AS embed_last_submission_at

            FROM leadform_form_embed lfe

            LEFT JOIN (
                {embed_submission_subquery}
            ) ess
                ON ess.form_embed_id = lfe.id

            WHERE lfe.form_id IN ({placeholders})
              AND lfe.active_status <> 'deleted'

            ORDER BY
                lfe.id ASC
        """

        query_params = embed_submission_params + form_ids

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(query_params))
            rows = cursor.fetchall()

        embeds_by_form_id: Dict[int, List[Dict[str, Any]]] = {}

        for row in rows:
            form_id = int(row.get("form_id") or 0)

            if form_id not in embeds_by_form_id:
                embeds_by_form_id[form_id] = []

            embeds_by_form_id[form_id].append(normalize_embed_row(row))

        return embeds_by_form_id

    finally:
        if connection:
            connection.close()


def fetch_leadforms(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    has_embeds: Optional[bool] = None,
    has_submissions: Optional[bool] = None,
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    connection = None

    page = max(int(page), 1)
    per_page = max(1, min(int(per_page), 100))
    offset = (page - 1) * per_page

    where_clause, where_params = build_where_clause(
        search=search,
        search_by=search_by,
        has_embeds=has_embeds,
        has_submissions=has_submissions,
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
        filters=filters,
    )

    form_submission_subquery, form_submission_params = build_form_submission_summary_subquery(
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
    )

    try:
        connection = get_client_connection(client_database)

        count_sql = f"""
            SELECT COUNT(*) AS total_records
            FROM leadform_form lf
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, tuple(where_params))
            count_row = cursor.fetchone()

        total_records = int(count_row.get("total_records") or 0)
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0

        sql = f"""
            SELECT
                lf.id AS form_id,
                lf.form_template_id,
                lf.form_name,
                lf.description,
                lf.form_json,
                lf.custom_css,
                lf.assigned_admins,
                lf.assign_owner,
                lf.created_by,
                lf.created_date,
                lf.modified_by,
                lf.modified_date,
                lf.is_active,
                lf.active_status,

                (
                    SELECT COUNT(*)
                    FROM leadform_form_embed lfe_count
                    WHERE lfe_count.form_id = lf.id
                      AND lfe_count.active_status <> 'deleted'
                ) AS total_embeds,

                (
                    SELECT COUNT(*)
                    FROM leadform_form_embed lfe_active_count
                    WHERE lfe_active_count.form_id = lf.id
                      AND lfe_active_count.active_status <> 'deleted'
                      AND lfe_active_count.is_active = 'Y'
                ) AS active_embeds,

                COALESCE(fss.total_submissions, 0) AS total_submissions,
                fss.first_submission_at,
                fss.last_submission_at

            FROM leadform_form lf

            LEFT JOIN (
                {form_submission_subquery}
            ) fss
                ON fss.form_id = lf.id

            WHERE {where_clause}

            ORDER BY
                lf.modified_date DESC,
                lf.created_date DESC,
                lf.id DESC

            LIMIT %s OFFSET %s
        """

        query_params = form_submission_params + where_params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(query_params))
            rows = cursor.fetchall()

        items = [normalize_leadform_row(row) for row in rows]

        form_ids = [
            int(item.get("form_id"))
            for item in items
            if item.get("form_id")
        ]

        embeds_by_form_id = fetch_leadform_embeds(
            client_database=client_database,
            form_ids=form_ids,
            submission_date_from=submission_date_from,
            submission_date_to=submission_date_to,
        )

        for item in items:
            form_id = int(item.get("form_id") or 0)
            item["embeds"] = embeds_by_form_id.get(form_id, [])

        return {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "offset": offset,
                "record_count": len(items),
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    finally:
        if connection:
            connection.close()


def count_leadforms(
    client_database: str,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    has_embeds: Optional[bool] = None,
    has_submissions: Optional[bool] = None,
    submission_date_from: Optional[str] = None,
    submission_date_to: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> int:
    connection = None

    where_clause, where_params = build_where_clause(
        search=search,
        search_by=search_by,
        has_embeds=has_embeds,
        has_submissions=has_submissions,
        submission_date_from=submission_date_from,
        submission_date_to=submission_date_to,
        filters=filters,
    )

    try:
        connection = get_client_connection(client_database)

        sql = f"""
            SELECT COUNT(*) AS total_records
            FROM leadform_form lf
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(where_params))
            row = cursor.fetchone()

        return int(row.get("total_records") or 0)

    finally:
        if connection:
            connection.close()


def fetch_leadform_by_id(
    client_database: str,
    form_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None

    form_submission_subquery, form_submission_params = build_form_submission_summary_subquery()

    try:
        connection = get_client_connection(client_database)

        sql = f"""
            SELECT
                lf.id AS form_id,
                lf.form_template_id,
                lf.form_name,
                lf.description,
                lf.form_json,
                lf.custom_css,
                lf.assigned_admins,
                lf.assign_owner,
                lf.created_by,
                lf.created_date,
                lf.modified_by,
                lf.modified_date,
                lf.is_active,
                lf.active_status,

                (
                    SELECT COUNT(*)
                    FROM leadform_form_embed lfe_count
                    WHERE lfe_count.form_id = lf.id
                      AND lfe_count.active_status <> 'deleted'
                ) AS total_embeds,

                (
                    SELECT COUNT(*)
                    FROM leadform_form_embed lfe_active_count
                    WHERE lfe_active_count.form_id = lf.id
                      AND lfe_active_count.active_status <> 'deleted'
                      AND lfe_active_count.is_active = 'Y'
                ) AS active_embeds,

                COALESCE(fss.total_submissions, 0) AS total_submissions,
                fss.first_submission_at,
                fss.last_submission_at

            FROM leadform_form lf

            LEFT JOIN (
                {form_submission_subquery}
            ) fss
                ON fss.form_id = lf.id

            WHERE lf.id = %s
              AND lf.active_status <> 'deleted'

            LIMIT 1
        """

        query_params = form_submission_params + [form_id]

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(query_params))
            row = cursor.fetchone()

        if not row:
            return None

        leadform = normalize_leadform_row(row)

        embeds_by_form_id = fetch_leadform_embeds(
            client_database=client_database,
            form_ids=[int(form_id)],
        )

        leadform["embeds"] = embeds_by_form_id.get(int(form_id), [])

        return leadform

    finally:
        if connection:
            connection.close()
