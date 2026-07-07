# app/services/attachment_service.py

import json
import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_attachment.v1"
DEFAULT_MASTER_USER_TABLE = "logiklu0_leadactuator.zp_users"
ALLOWED_ATTACHMENT_SCOPES = ["lead", "contact", "deal"]

CONTACT_PHONE_COLUMN_CANDIDATES = [
    "primary_phone",
    "mobile",
    "mobile_number",
    "phone_number",
    "contact_phone",
    "contact_number",
    "whatsapp",
    "alternative_phone",
    "alternate_phone",
    "alt_phone",
]


# -----------------------------
# Generic helpers
# -----------------------------

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


def to_number(value: Any) -> Any:
    if value is None or value == "":
        return None

    if isinstance(value, Decimal):
        value = float(value)

    try:
        number = float(value)
    except Exception:
        return value

    if number.is_integer():
        return int(number)

    return number


def to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except Exception:
        return None


def format_date(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def format_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    return str(value)


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


def format_contact_phone(value: Any) -> Optional[str]:
    """Return primary phone as '+CC number' when value is stored as JSON."""
    if value is None:
        return None

    if isinstance(value, dict):
        country_code = str(value.get("country_code") or "").strip()
        phone = str(value.get("phone") or value.get("number") or "").strip()
        combined = " ".join([part for part in [country_code, phone] if part]).strip()
        return combined or None

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    text = str(value).strip()

    if not text:
        return None

    if text.startswith("{") and text.endswith("}"):
        decoded = safe_json_decode(text, {})
        if isinstance(decoded, dict):
            country_code = str(decoded.get("country_code") or "").strip()
            phone = str(decoded.get("phone") or decoded.get("number") or "").strip()
            combined = " ".join([part for part in [country_code, phone] if part]).strip()
            return combined or None

    return text


def extract_original_filename(value: Any) -> Optional[str]:
    """originalname may be a string or an upload-array JSON object."""
    if value is None:
        return None

    if isinstance(value, dict):
        return first_non_empty(value.get("name"), value.get("filename"), value.get("originalname"))

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    text = str(value).strip()

    if not text:
        return None

    if text.startswith("{") and text.endswith("}"):
        decoded = safe_json_decode(text, {})
        if isinstance(decoded, dict):
            return first_non_empty(decoded.get("name"), decoded.get("filename"), decoded.get("originalname"))

    return text


def build_attachment_url(fullpath: Any) -> Optional[str]:
    if not fullpath:
        return None

    path = str(fullpath).replace("\\", "/").strip()

    if not path:
        return None

    # Old data may store absolute paths like /var/www/html/app/v1/attachments/...
    marker = "app/v1/"
    if marker in path:
        path = path.split(marker, 1)[1]

    if "attachments/" in path:
        path = path[path.find("attachments/"):]

    base_url = str(getattr(settings, "ATTACHMENT_BASE_URL", "https://logiklu.com/app/v1/") or "https://logiklu.com/app/v1/").rstrip("/") + "/"
    return base_url + path.lstrip("/")


def clean_filter_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def split_csv_values(value: Any) -> List[str]:
    value = clean_filter_value(value)

    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def split_id_values(value: Any) -> List[int]:
    output = []

    for item in split_csv_values(value):
        parsed_id = to_int(item)

        if parsed_id is not None:
            output.append(parsed_id)

    return output


def unique_ints(values: List[Any]) -> List[int]:
    output = []
    seen = set()

    for value in values:
        parsed_id = to_int(value)

        if parsed_id is None or parsed_id in seen:
            continue

        seen.add(parsed_id)
        output.append(parsed_id)

    return output


def make_placeholders(values: List[Any]) -> str:
    return ", ".join(["%s"] * len(values))


def get_master_user_table() -> str:
    table_name = str(getattr(settings, "MASTER_USER_TABLE", DEFAULT_MASTER_USER_TABLE) or DEFAULT_MASTER_USER_TABLE).strip()

    if not re.match(r"^[A-Za-z0-9_\.]+$", table_name):
        return DEFAULT_MASTER_USER_TABLE

    return table_name


def fetch_existing_table_columns(connection: Any, table_name: str) -> set:
    """Return existing columns for a client DB table.

    Some LogiKlu client databases use different contact phone column names.
    This keeps the endpoint from failing when one expected phone column is absent.
    """
    if not re.match(r"^[A-Za-z0-9_]+$", str(table_name or "")):
        return set()

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            rows = cursor.fetchall()

        return set([str(row.get("Field") or "").strip() for row in rows if row.get("Field")])
    except Exception:
        return set()


def get_contact_phone_columns(connection: Any) -> List[str]:
    existing_columns = fetch_existing_table_columns(connection, "lk_central_contacts")

    if not existing_columns:
        return []

    return [column for column in CONTACT_PHONE_COLUMN_CANDIDATES if column in existing_columns]


def contact_phone_like_sql(alias: str, phone_columns: Optional[List[str]]) -> str:
    columns = phone_columns or []

    if not columns:
        return ""

    return " OR ".join([f"{alias}.{column} LIKE %s" for column in columns])


def append_contact_phone_like_params(params: List[Any], phone_columns: Optional[List[str]], like_value: str) -> None:
    for _column in (phone_columns or []):
        params.append(like_value)


# -----------------------------
# SQL filter helpers
# -----------------------------

def append_like_filter(where_parts: List[str], params: List[Any], expressions: List[str], value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        like_value = f"%{token}%"

        for expression in expressions:
            clauses.append(f"{expression} LIKE %s")
            params.append(like_value)

    if clauses:
        where_parts.append("(" + " OR ".join(clauses) + ")")


def append_string_exact_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    if len(tokens) == 1:
        where_parts.append(f"{expression} = %s")
        params.append(tokens[0])
        return

    where_parts.append(f"{expression} IN ({make_placeholders(tokens)})")
    params.extend(tokens)


def append_integer_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    if len(ids) == 1:
        where_parts.append(f"{expression} = %s")
        params.append(ids[0])
        return

    where_parts.append(f"{expression} IN ({make_placeholders(ids)})")
    params.extend(ids)


def append_date_range_filter(
    where_parts: List[str],
    params: List[Any],
    expression: str,
    from_value: Any = None,
    to_value: Any = None,
) -> None:
    if clean_filter_value(from_value) is not None:
        where_parts.append(f"{expression} >= %s")
        params.append(str(from_value).strip())

    if clean_filter_value(to_value) is not None:
        where_parts.append(f"{expression} <= %s")
        params.append(str(to_value).strip())


def append_filesize_range_filter(where_parts: List[str], params: List[Any], min_value: Any = None, max_value: Any = None) -> None:
    if clean_filter_value(min_value) is not None:
        where_parts.append("CAST(JSON_UNQUOTE(JSON_EXTRACT(las.activity_details, '$.filesize')) AS UNSIGNED) >= %s")
        params.append(str(min_value).strip())

    if clean_filter_value(max_value) is not None:
        where_parts.append("CAST(JSON_UNQUOTE(JSON_EXTRACT(las.activity_details, '$.filesize')) AS UNSIGNED) <= %s")
        params.append(str(max_value).strip())


def append_attachment_scope_filter(where_parts: List[str], attachment_scope: Optional[str]) -> None:
    attachment_scope = str(attachment_scope or "all").strip().lower()

    if attachment_scope == "lead":
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_leads lal_scope
                WHERE lal_scope.activity_id = las.activity_id
            )
            """
        )
        return

    if attachment_scope == "contact":
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_contacts lac_scope
                WHERE lac_scope.activity_id = las.activity_id
                  AND COALESCE(lac_scope.contact_id, 0) > 0
            )
            """
        )
        return

    if attachment_scope == "deal":
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_opportunities lao_scope
                WHERE lao_scope.activity_id = las.activity_id
            )
            """
        )
        return

    # /usernotes returns notes that are attached to at least one supported CRM object.
    where_parts.append(
        """
        (
            EXISTS (SELECT 1 FROM lk_activity_leads lal_scope WHERE lal_scope.activity_id = las.activity_id)
            OR EXISTS (SELECT 1 FROM lk_activity_contacts lac_scope WHERE lac_scope.activity_id = las.activity_id AND COALESCE(lac_scope.contact_id, 0) > 0)
            OR EXISTS (SELECT 1 FROM lk_activity_opportunities lao_scope WHERE lao_scope.activity_id = las.activity_id)
        )
        """
    )


def append_lead_integer_filter(where_parts: List[str], params: List[Any], column: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    where_parts.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_activity_leads lal_filter
            WHERE lal_filter.activity_id = las.activity_id
              AND lal_filter.{column} IN ({make_placeholders(ids)})
        )
        """
    )
    params.extend(ids)


def append_lead_like_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM lk_activity_leads lal_filter
                INNER JOIN lk_lead_master lm_filter
                    ON lm_filter.lead_id = lal_filter.lead_id
                WHERE lal_filter.activity_id = las.activity_id
                  AND {expression} LIKE %s
            )
            """
        )
        params.append(f"%{token}%")

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_contact_integer_filter(where_parts: List[str], params: List[Any], column: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    where_parts.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_activity_contacts lac_filter
            WHERE lac_filter.activity_id = las.activity_id
              AND COALESCE(lac_filter.contact_id, 0) > 0
              AND lac_filter.{column} IN ({make_placeholders(ids)})
        )
        """
    )
    params.extend(ids)


def append_contact_like_filter(
    where_parts: List[str],
    params: List[Any],
    field: str,
    value: Any,
    contact_phone_columns: Optional[List[str]] = None,
) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []
    phone_sql = contact_phone_like_sql("cc_filter", contact_phone_columns)

    for token in tokens:
        like_value = f"%{token}%"

        if field == "name":
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts lac_filter
                    INNER JOIN lk_central_contacts cc_filter
                        ON cc_filter.contact_id = lac_filter.contact_id
                    WHERE lac_filter.activity_id = las.activity_id
                      AND COALESCE(lac_filter.contact_id, 0) > 0
                      AND (
                            cc_filter.first_name LIKE %s
                            OR cc_filter.last_name LIKE %s
                            OR CONCAT_WS(' ', cc_filter.first_name, cc_filter.last_name) LIKE %s
                      )
                )
                """
            )
            params.extend([like_value, like_value, like_value])
        elif field == "email":
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts lac_filter
                    INNER JOIN lk_central_contacts cc_filter
                        ON cc_filter.contact_id = lac_filter.contact_id
                    WHERE lac_filter.activity_id = las.activity_id
                      AND COALESCE(lac_filter.contact_id, 0) > 0
                      AND cc_filter.email LIKE %s
                )
                """
            )
            params.append(like_value)
        elif field == "phone":
            if phone_sql:
                clauses.append(
                    f"""
                    EXISTS (
                        SELECT 1
                        FROM lk_activity_contacts lac_filter
                        INNER JOIN lk_central_contacts cc_filter
                            ON cc_filter.contact_id = lac_filter.contact_id
                        WHERE lac_filter.activity_id = las.activity_id
                          AND COALESCE(lac_filter.contact_id, 0) > 0
                          AND ({phone_sql})
                    )
                    """
                )
                append_contact_phone_like_params(params, contact_phone_columns, like_value)
            else:
                # contact_phone was requested but this client DB has no known phone column.
                clauses.append("1=0")
        else:
            phone_part = ""
            if phone_sql:
                phone_part = " OR " + phone_sql

            clauses.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts lac_filter
                    INNER JOIN lk_central_contacts cc_filter
                        ON cc_filter.contact_id = lac_filter.contact_id
                    WHERE lac_filter.activity_id = las.activity_id
                      AND COALESCE(lac_filter.contact_id, 0) > 0
                      AND (
                            cc_filter.first_name LIKE %s
                            OR cc_filter.last_name LIKE %s
                            OR CONCAT_WS(' ', cc_filter.first_name, cc_filter.last_name) LIKE %s
                            OR cc_filter.email LIKE %s
                            {phone_part}
                      )
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value])
            append_contact_phone_like_params(params, contact_phone_columns, like_value)

    where_parts.append("(" + " OR ".join(clauses) + ")")

def append_deal_integer_filter(where_parts: List[str], params: List[Any], column: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    where_parts.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_activity_opportunities lao_filter
            INNER JOIN lk_opportunities o_filter
                ON o_filter.opportunity_id = lao_filter.opportunity_id
            WHERE lao_filter.activity_id = las.activity_id
              AND {column} IN ({make_placeholders(ids)})
        )
        """
    )
    params.extend(ids)


def append_deal_like_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM lk_activity_opportunities lao_filter
                INNER JOIN lk_opportunities o_filter
                    ON o_filter.opportunity_id = lao_filter.opportunity_id
                LEFT JOIN jos_setting_sales_executive_action stage_filter
                    ON stage_filter.id = o_filter.opportunity_status_id
                   AND stage_filter.section = 'STATUS'
                WHERE lao_filter.activity_id = las.activity_id
                  AND {expression} LIKE %s
            )
            """
        )
        params.append(f"%{token}%")

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_user_name_filter(where_parts: List[str], params: List[Any], user_expression: str, value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    table_name = get_master_user_table()
    clauses = []

    for token in tokens:
        like_value = f"%{token}%"
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM {table_name} user_filter
                WHERE user_filter.id = {user_expression}
                  AND (
                        user_filter.name LIKE %s
                        OR user_filter.username LIKE %s
                        OR user_filter.email LIKE %s
                  )
            )
            """
        )
        params.extend([like_value, like_value, like_value])

    where_parts.append("(" + " OR ".join(clauses) + ")")


EXACT_ATTACHMENT_FILTERS = {
    "owner": "las.owner",
    "created_by": "las.created_by",
    "modified_by": "las.modified_by",
}

TEXT_ATTACHMENT_FILTERS = {
    "name": ["las.activity_name"],
    "attachment_name": ["las.activity_name", "las.activity_details"],
    "originalname": ["las.activity_details"],
    "attachmentname": ["las.activity_details"],
    "filetype": ["las.activity_details"],
    "activity_name": ["las.activity_name"],
}

NUMERIC_ATTACHMENT_FILTERS = {
    "filesize": "las.activity_details",
}

STATUS_FILTERS = {
    "status": "las.status",
    "active_status": "las.active_status",
}

DATE_FILTERS = {
    "created_date": "las.created_date",
    "modified_date": "las.modified_date",
    "startdate": "las.startdate",
    "enddate": "las.enddate",
}


def append_named_filter(where_parts: List[str], params: List[Any], field_name: str, value: Any, contact_phone_columns: Optional[List[str]] = None) -> None:
    field_name = str(field_name or "").strip().lower()

    if not field_name:
        return

    if field_name in TEXT_ATTACHMENT_FILTERS:
        append_like_filter(where_parts, params, TEXT_ATTACHMENT_FILTERS[field_name], value)
        return

    if field_name == "filesize":
        append_filesize_range_filter(where_parts, params, value, value)
        return

    if field_name in EXACT_ATTACHMENT_FILTERS:
        append_integer_filter(where_parts, params, EXACT_ATTACHMENT_FILTERS[field_name], value)
        return

    if field_name in STATUS_FILTERS:
        append_string_exact_filter(where_parts, params, STATUS_FILTERS[field_name], value)
        return

    if field_name in ["owner_name", "created_by_name", "modified_by_name"]:
        user_column = {
            "owner_name": "las.owner",
            "created_by_name": "las.created_by",
            "modified_by_name": "las.modified_by",
        }[field_name]
        append_user_name_filter(where_parts, params, user_column, value)
        return

    if field_name in ["lead_id", "account_id"]:
        append_lead_integer_filter(where_parts, params, "lead_id", value)
        return

    if field_name == "customer_id":
        append_lead_integer_filter(where_parts, params, "customer_id", value)
        return

    if field_name == "company_id":
        append_lead_integer_filter(where_parts, params, "company_id", value)
        return

    if field_name == "lead_name":
        append_lead_like_filter(where_parts, params, "lm_filter.lead_name", value)
        return

    if field_name == "lead_city":
        append_lead_like_filter(where_parts, params, "lm_filter.city", value)
        return

    if field_name == "lead_state":
        append_lead_like_filter(where_parts, params, "lm_filter.state", value)
        return

    if field_name == "lead_country":
        append_lead_like_filter(where_parts, params, "lm_filter.country", value)
        return

    if field_name == "contact_id":
        append_contact_integer_filter(where_parts, params, "contact_id", value)
        return

    if field_name == "contact_role":
        roles = split_csv_values(value)

        if roles:
            where_parts.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts lac_role
                    WHERE lac_role.activity_id = las.activity_id
                      AND COALESCE(lac_role.contact_id, 0) > 0
                      AND lac_role.contact_role IN ({make_placeholders(roles)})
                )
                """
            )
            params.extend(roles)

        return

    if field_name == "contact_name":
        append_contact_like_filter(where_parts, params, "name", value, contact_phone_columns)
        return

    if field_name == "contact_email":
        append_contact_like_filter(where_parts, params, "email", value, contact_phone_columns)
        return

    if field_name == "contact_phone":
        append_contact_like_filter(where_parts, params, "phone", value, contact_phone_columns)
        return

    if field_name in ["deal_id", "opportunity_id"]:
        append_deal_integer_filter(where_parts, params, "o_filter.opportunity_id", value)
        return

    if field_name in ["deal_stage_id", "opportunity_status_id", "status_id"]:
        append_deal_integer_filter(where_parts, params, "o_filter.opportunity_status_id", value)
        return

    if field_name == "deal_name":
        append_deal_like_filter(where_parts, params, "o_filter.opportunity_name", value)
        return

    if field_name == "deal_status":
        append_deal_like_filter(where_parts, params, "o_filter.oportunity_status", value)
        return

    if field_name == "deal_stage_title":
        append_deal_like_filter(where_parts, params, "stage_filter.title", value)
        return


def append_advanced_filters(where_parts: List[str], params: List[Any], filters: Optional[str], contact_phone_columns: Optional[List[str]] = None) -> None:
    if not filters:
        return

    decoded = safe_json_decode(filters, [])

    if isinstance(decoded, dict):
        if isinstance(decoded.get("filters"), list):
            decoded = decoded.get("filters")
        else:
            decoded = [decoded]

    if not isinstance(decoded, list):
        return

    for item in decoded:
        if not isinstance(item, dict):
            continue

        field_name = str(item.get("field") or "").strip().lower()
        operator = str(item.get("operator") or "like").strip().lower()
        value = item.get("value")

        if not field_name:
            continue

        if field_name in ["filesize"]:
            if operator in ["from", "gte", ">=", "gt", ">"]:
                append_filesize_range_filter(where_parts, params, min_value=value)
            elif operator in ["to", "lte", "<=", "lt", "<"]:
                append_filesize_range_filter(where_parts, params, max_value=value)
            elif operator in ["between", "range"] and isinstance(value, list) and len(value) >= 2:
                append_filesize_range_filter(where_parts, params, value[0], value[1])
            else:
                append_named_filter(where_parts, params, field_name, value, contact_phone_columns)
            continue

        if field_name in DATE_FILTERS:
            expression = DATE_FILTERS[field_name]

            if operator in ["from", "gte", ">="]:
                append_date_range_filter(where_parts, params, expression, from_value=value)
            elif operator in ["to", "lte", "<="]:
                append_date_range_filter(where_parts, params, expression, to_value=value)
            elif operator in ["between", "range"] and isinstance(value, list) and len(value) >= 2:
                append_date_range_filter(where_parts, params, expression, value[0], value[1])
            else:
                append_named_filter(where_parts, params, field_name, value, contact_phone_columns)

            continue

        append_named_filter(where_parts, params, field_name, value, contact_phone_columns)


def build_where_clause(
    attachment_scope: Optional[str] = None,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
    contact_phone_columns: Optional[List[str]] = None,
) -> Tuple[str, List[Any]]:
    where_parts = [
        "las.activity_type = 'attachment'",
        "(las.active_status IS NULL OR las.active_status <> 'deleted')",
    ]
    params: List[Any] = []

    append_attachment_scope_filter(where_parts, attachment_scope)

    if search:
        if search_by:
            append_named_filter(where_parts, params, search_by, search, contact_phone_columns)
        else:
            search_value = f"%{search.strip()}%"
            contact_search_phone_sql = contact_phone_like_sql("cc_search", contact_phone_columns)
            contact_search_phone_part = ""
            if contact_search_phone_sql:
                contact_search_phone_part = "OR " + contact_search_phone_sql

            where_parts.append(
                f"""
                (
                    las.activity_name LIKE %s
                    OR las.activity_details LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM lk_activity_leads lal_search
                        INNER JOIN lk_lead_master lm_search
                            ON lm_search.lead_id = lal_search.lead_id
                        WHERE lal_search.activity_id = las.activity_id
                          AND (
                                lm_search.lead_name LIKE %s
                                OR lm_search.city LIKE %s
                                OR lm_search.state LIKE %s
                                OR lm_search.country LIKE %s
                          )
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM lk_activity_contacts lac_search
                        INNER JOIN lk_central_contacts cc_search
                            ON cc_search.contact_id = lac_search.contact_id
                        WHERE lac_search.activity_id = las.activity_id
                          AND COALESCE(lac_search.contact_id, 0) > 0
                          AND (
                                cc_search.first_name LIKE %s
                                OR cc_search.last_name LIKE %s
                                OR CONCAT_WS(' ', cc_search.first_name, cc_search.last_name) LIKE %s
                                OR cc_search.email LIKE %s
                                {contact_search_phone_part}
                          )
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM lk_activity_opportunities lao_search
                        INNER JOIN lk_opportunities o_search
                            ON o_search.opportunity_id = lao_search.opportunity_id
                        WHERE lao_search.activity_id = las.activity_id
                          AND (
                                o_search.opportunity_name LIKE %s
                                OR o_search.oportunity_status LIKE %s
                          )
                    )
                )
                """
            )
            params.extend([
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
            ])
            append_contact_phone_like_params(params, contact_phone_columns, search_value)
            params.extend([
                search_value,
                search_value,
            ])

    filter_params = filter_params or {}

    append_filesize_range_filter(
        where_parts,
        params,
        filter_params.get("filesize_min"),
        filter_params.get("filesize_max"),
    )

    for field_name, value in filter_params.items():
        if value is None or str(value).strip() == "":
            continue

        if field_name.endswith("_from") or field_name.endswith("_to") or field_name in ["filesize_min", "filesize_max"]:
            continue

        append_named_filter(where_parts, params, field_name, value, contact_phone_columns)

    for date_field, expression in DATE_FILTERS.items():
        append_date_range_filter(
            where_parts,
            params,
            expression,
            filter_params.get(f"{date_field}_from"),
            filter_params.get(f"{date_field}_to"),
        )

    append_advanced_filters(where_parts, params, filters, contact_phone_columns)

    return " AND ".join(where_parts), params


# -----------------------------
# Related data fetchers
# -----------------------------

def fetch_users(connection: Any, user_ids: List[Any]) -> Dict[int, Dict[str, Any]]:
    ids = unique_ints(user_ids)

    if not ids:
        return {}

    fallback = {user_id: {"id": user_id, "name": None, "email": None} for user_id in ids}
    table_name = get_master_user_table()

    try:
        sql = f"SELECT * FROM {table_name} WHERE id IN ({make_placeholders(ids)})"

        with connection.cursor() as cursor:
            cursor.execute(sql, ids)
            rows = cursor.fetchall()

        users = dict(fallback)

        for row in rows:
            user_id = to_int(row.get("id") or row.get("user_id"))

            if user_id is None:
                continue

            full_name = first_non_empty(
                row.get("name"),
                row.get("full_name"),
                " ".join([
                    str(row.get("first_name") or "").strip(),
                    str(row.get("middle_name") or "").strip(),
                    str(row.get("last_name") or "").strip(),
                ]).strip(),
                row.get("username"),
            )
            email = first_non_empty(row.get("email"), row.get("user_email"))

            if not email and row.get("username") and "@" in str(row.get("username")):
                email = row.get("username")

            users[user_id] = {
                "id": user_id,
                "name": full_name,
                "email": email,
            }

        return users

    except Exception:
        return fallback


def get_user(user_map: Dict[int, Dict[str, Any]], user_id: Any) -> Optional[Dict[str, Any]]:
    parsed_id = to_int(user_id)

    if parsed_id is None:
        return None

    return user_map.get(parsed_id) or {"id": parsed_id, "name": None, "email": None}


def fetch_attachment_leads(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            lal.activity_id,
            lal.lead_id,
            lm.lead_name,
            lm.lead_type,
            lm.city,
            lm.state,
            lm.country
        FROM lk_activity_leads lal
        LEFT JOIN lk_lead_master lm
            ON lm.lead_id = lal.lead_id
        WHERE lal.activity_id IN ({make_placeholders(activity_ids)})
        ORDER BY lal.activity_id ASC, lal.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))

        if activity_id is None:
            continue

        output.setdefault(activity_id, []).append({
            "lead_id": row.get("lead_id"),
            "name": row.get("lead_name"),
            "lead_type": row.get("lead_type"),
            "city": row.get("city"),
            "state": row.get("state"),
            "country": row.get("country"),
        })

    return output



def fetch_attachment_contacts(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            lac.activity_id,
            lac.contact_id,
            lac.contact_role,
            cc.first_name,
            cc.last_name,
            cc.email,
            cc.primary_phone AS phone
        FROM lk_activity_contacts lac
        LEFT JOIN lk_central_contacts cc
            ON cc.contact_id = lac.contact_id
        WHERE lac.activity_id IN ({make_placeholders(activity_ids)})
          AND COALESCE(lac.contact_id, 0) > 0
        ORDER BY lac.activity_id ASC, lac.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))

        if activity_id is None:
            continue

        name = " ".join([
            str(row.get("first_name") or "").strip(),
            str(row.get("last_name") or "").strip(),
        ]).strip()

        output.setdefault(activity_id, []).append({
            "id": row.get("contact_id"),
            "name": name or None,
            "email": row.get("email"),
            "phone": format_contact_phone(row.get("phone")),
            "contact_role": row.get("contact_role"),
        })

    return output



def fetch_attachment_deals(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            lao.activity_id,
            lao.opportunity_id,
            o.opportunity_name,
            o.oportunity_status,
            stage.id AS deal_stage_id,
            stage.title AS deal_stage_title,
            stage.color AS deal_stage_color
        FROM lk_activity_opportunities lao
        LEFT JOIN lk_opportunities o
            ON o.opportunity_id = lao.opportunity_id
        LEFT JOIN jos_setting_sales_executive_action stage
            ON stage.id = o.opportunity_status_id
           AND stage.section = 'STATUS'
        WHERE lao.activity_id IN ({make_placeholders(activity_ids)})
        ORDER BY lao.activity_id ASC, lao.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))

        if activity_id is None:
            continue

        output.setdefault(activity_id, []).append({
            "deal_id": row.get("opportunity_id"),
            "name": row.get("opportunity_name"),
            "deal_status": row.get("oportunity_status"),
            "deal_stage": {
                "id": row.get("deal_stage_id"),
                "title": row.get("deal_stage_title"),
                "color": row.get("deal_stage_color"),
            } if row.get("deal_stage_id") else None,
        })

    return output




# -----------------------------
# Row builders
# -----------------------------

def determine_attachment_type(
    activity_id: int,
    attachment_scope: Optional[str],
    leads_map: Dict[int, List[Dict[str, Any]]],
    contacts_map: Dict[int, List[Dict[str, Any]]],
    deals_map: Dict[int, List[Dict[str, Any]]],
) -> Optional[str]:
    if attachment_scope in ALLOWED_ATTACHMENT_SCOPES:
        return attachment_scope

    if activity_id in deals_map and deals_map.get(activity_id):
        return "deal"

    if activity_id in contacts_map and contacts_map.get(activity_id):
        return "contact"

    if activity_id in leads_map and leads_map.get(activity_id):
        return "lead"

    return None


def build_attachment_item(
    row: Dict[str, Any],
    attachment_scope: Optional[str],
    leads_map: Dict[int, List[Dict[str, Any]]],
    contacts_map: Dict[int, List[Dict[str, Any]]],
    deals_map: Dict[int, List[Dict[str, Any]]],
    user_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    activity_id = int(row.get("attachment_id"))
    details = safe_json_decode(row.get("activity_details"), {})

    fullpath = first_non_empty(details.get("fullpath"), details.get("full_path"), details.get("path"))
    attachment_type = determine_attachment_type(activity_id, attachment_scope, leads_map, contacts_map, deals_map)

    lead = None
    contact = None
    deal = None

    if attachment_type == "lead":
        lead = (leads_map.get(activity_id) or [None])[0]
    elif attachment_type == "contact":
        contact = (contacts_map.get(activity_id) or [None])[0]
    elif attachment_type == "deal":
        deal = (deals_map.get(activity_id) or [None])[0]

    return {
        "attachment_id": row.get("attachment_id"),
        "attachment_type": attachment_type,
        "name": first_non_empty(row.get("activity_name"), details.get("Subject"), details.get("subject")),
        "originalname": extract_original_filename(first_non_empty(details.get("originalname"), details.get("original_name"))),
        "attachmentname": first_non_empty(details.get("modifiedname"), details.get("modified_name")),
        "filetype": first_non_empty(details.get("filetype"), details.get("file_type")),
        "filesize": to_number(first_non_empty(details.get("filesize"), details.get("file_size"))),
        "attachment_url": build_attachment_url(fullpath),
        "lead": lead,
        "contact": contact,
        "deal": deal,
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date")),
    }


def hydrate_attachment_rows(connection: Any, rows: List[Dict[str, Any]], attachment_scope: Optional[str]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    activity_ids = [int(row.get("attachment_id")) for row in rows if row.get("attachment_id") is not None]

    leads_map = fetch_attachment_leads(connection, activity_ids)
    contacts_map = fetch_attachment_contacts(connection, activity_ids)
    deals_map = fetch_attachment_deals(connection, activity_ids)

    user_ids: List[Any] = []

    for row in rows:
        user_ids.extend([row.get("created_by"), row.get("modified_by")])

    user_map = fetch_users(connection, user_ids)

    return [
        build_attachment_item(
            row=row,
            attachment_scope=attachment_scope,
            leads_map=leads_map,
            contacts_map=contacts_map,
            deals_map=deals_map,
            user_map=user_map,
        )
        for row in rows
    ]


# -----------------------------
# Public service functions
# -----------------------------

def fetch_user_attachments_list(
    client_database: str,
    attachment_scope: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    connection = None

    page = max(page, 1)
    per_page = max(per_page, 10)
    offset = (page - 1) * per_page

    try:
        connection = get_client_connection(client_database)
        contact_phone_columns = get_contact_phone_columns(connection)

        where_clause, params = build_where_clause(
            attachment_scope=attachment_scope,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
            contact_phone_columns=contact_phone_columns,
        )

        count_sql = f"""
            SELECT COUNT(DISTINCT las.activity_id) AS total_records
            FROM lk_activity_schedule las
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            count_row = cursor.fetchone()

        total_records = int(count_row.get("total_records") or 0)
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0

        sql = f"""
            SELECT
                las.activity_id AS attachment_id,
                las.activity_name,
                las.activity_details,
                las.created_by,
                las.created_date,
                las.modified_by,
                las.modified_date
            FROM lk_activity_schedule las
            WHERE {where_clause}
            ORDER BY las.created_date DESC, las.activity_id DESC
            LIMIT %s OFFSET %s
        """

        query_params = params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        items = hydrate_attachment_rows(connection, rows, attachment_scope)

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


def fetch_user_attachment_detail(
    client_database: str,
    attachment_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None

    try:
        connection = get_client_connection(client_database)

        sql = """
            SELECT
                las.activity_id AS attachment_id,
                las.activity_name,
                las.activity_details,
                las.created_by,
                las.created_date,
                las.modified_by,
                las.modified_date
            FROM lk_activity_schedule las
            WHERE las.activity_type = 'attachment'
              AND (las.active_status IS NULL OR las.active_status <> 'deleted')
              AND las.activity_id = %s
            LIMIT 1
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, [attachment_id])
            row = cursor.fetchone()

        if not row:
            return None

        items = hydrate_attachment_rows(connection, [row], None)

        if not items:
            return None

        return items[0]

    finally:
        if connection:
            connection.close()
