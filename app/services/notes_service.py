# app/services/notes_service.py

import json
import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_note.v1"
DEFAULT_MASTER_USER_TABLE = "logiklu0_leadactuator.zp_users"
ALLOWED_NOTE_SCOPES = ["account", "contact", "deal"]


def normalize_note_scope(note_scope: Optional[str]) -> Optional[str]:
    """Public note scope uses account/contact/deal. Internal database mapping still uses lead tables."""
    if note_scope is None:
        return None

    value = str(note_scope or "").strip().lower()

    if value == "lead":
        return "account"

    return value or None


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
    # Notes must map users from this master actuator table.
    return DEFAULT_MASTER_USER_TABLE


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


def append_note_scope_filter(where_parts: List[str], note_scope: Optional[str]) -> None:
    note_scope = normalize_note_scope(note_scope) or "all"

    if note_scope == "account":
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

    if note_scope == "contact":
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

    if note_scope == "deal":
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

    # /notes returns notes that are attached to at least one supported CRM object.
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


def append_contact_like_filter(where_parts: List[str], params: List[Any], field: str, value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

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
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts lac_filter
                    INNER JOIN lk_central_contacts cc_filter
                        ON cc_filter.contact_id = lac_filter.contact_id
                    WHERE lac_filter.activity_id = las.activity_id
                      AND COALESCE(lac_filter.contact_id, 0) > 0
                      AND cc_filter.primary_phone LIKE %s
                )
                """
            )
            params.append(like_value)
        else:
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
                            OR cc_filter.email LIKE %s
                            OR cc_filter.primary_phone LIKE %s
                      )
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value, like_value])

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


EXACT_NOTE_FILTERS = {
    "owner": "las.owner",
    "created_by": "las.created_by",
    "modified_by": "las.modified_by",
}

TEXT_NOTE_FILTERS = {
    "subject": ["las.activity_name", "las.activity_details"],
    "notes_subject": ["las.activity_name", "las.activity_details"],
    "note": ["las.activity_details"],
    "notes_text": ["las.activity_details"],
    "activity_name": ["las.activity_name"],
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


def append_named_filter(where_parts: List[str], params: List[Any], field_name: str, value: Any) -> None:
    field_name = str(field_name or "").strip().lower()

    if not field_name:
        return

    if field_name in TEXT_NOTE_FILTERS:
        append_like_filter(where_parts, params, TEXT_NOTE_FILTERS[field_name], value)
        return

    if field_name in EXACT_NOTE_FILTERS:
        append_integer_filter(where_parts, params, EXACT_NOTE_FILTERS[field_name], value)
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

    if field_name in ["lead_name", "account_name"]:
        append_lead_like_filter(where_parts, params, "lm_filter.lead_name", value)
        return

    if field_name in ["lead_type", "account_type"]:
        append_lead_like_filter(where_parts, params, "lm_filter.lead_type", value)
        return

    if field_name in ["lead_city", "account_city"]:
        append_lead_like_filter(where_parts, params, "lm_filter.city", value)
        return

    if field_name in ["lead_state", "account_state"]:
        append_lead_like_filter(where_parts, params, "lm_filter.state", value)
        return

    if field_name in ["lead_country", "account_country"]:
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
        append_contact_like_filter(where_parts, params, "name", value)
        return

    if field_name == "contact_email":
        append_contact_like_filter(where_parts, params, "email", value)
        return

    if field_name == "contact_phone":
        append_contact_like_filter(where_parts, params, "phone", value)
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


def append_advanced_filters(where_parts: List[str], params: List[Any], filters: Optional[str]) -> None:
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

        if field_name in DATE_FILTERS:
            expression = DATE_FILTERS[field_name]

            if operator in ["from", "gte", ">="]:
                append_date_range_filter(where_parts, params, expression, from_value=value)
            elif operator in ["to", "lte", "<="]:
                append_date_range_filter(where_parts, params, expression, to_value=value)
            elif operator in ["between", "range"] and isinstance(value, list) and len(value) >= 2:
                append_date_range_filter(where_parts, params, expression, value[0], value[1])
            else:
                append_named_filter(where_parts, params, field_name, value)

            continue

        append_named_filter(where_parts, params, field_name, value)


def build_where_clause(
    note_scope: Optional[str] = None,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any]]:
    where_parts = [
        "las.activity_type = 'note'",
        "(las.active_status IS NULL OR las.active_status <> 'deleted')",
    ]
    params: List[Any] = []

    append_note_scope_filter(where_parts, note_scope)

    if search:
        if search_by:
            append_named_filter(where_parts, params, search_by, search)
        else:
            search_value = f"%{search.strip()}%"
            where_parts.append(
                """
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
                                OR lm_search.lead_type LIKE %s
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
                                OR cc_search.primary_phone LIKE %s
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
                search_value,
                search_value,
                search_value,
                search_value,
            ])

    filter_params = filter_params or {}

    for field_name, value in filter_params.items():
        if value is None or str(value).strip() == "":
            continue

        if field_name.endswith("_from") or field_name.endswith("_to"):
            continue

        append_named_filter(where_parts, params, field_name, value)

    for date_field, expression in DATE_FILTERS.items():
        append_date_range_filter(
            where_parts,
            params,
            expression,
            filter_params.get(f"{date_field}_from"),
            filter_params.get(f"{date_field}_to"),
        )

    append_advanced_filters(where_parts, params, filters)

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


def fetch_note_accounts(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            lal.activity_id,
            lal.lead_id,
            lal.customer_id,
            lal.company_id,
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
            "account_id": row.get("lead_id"),
            "name": row.get("lead_name"),
            "account_type": row.get("lead_type"),
            "location": {
                "city": row.get("city"),
                "state": row.get("state"),
                "country": row.get("country"),
            },
        })

    return output


def fetch_note_contacts(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
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


def fetch_note_deals(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            lao.activity_id,
            lao.opportunity_id,
            o.opportunity_name,
            o.status,
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

def determine_note_type(
    activity_id: int,
    note_scope: Optional[str],
    accounts_map: Dict[int, List[Dict[str, Any]]],
    contacts_map: Dict[int, List[Dict[str, Any]]],
    deals_map: Dict[int, List[Dict[str, Any]]],
) -> Optional[str]:
    note_scope = normalize_note_scope(note_scope)

    if note_scope in ALLOWED_NOTE_SCOPES:
        return note_scope

    if activity_id in deals_map and deals_map.get(activity_id):
        return "deal"

    if activity_id in contacts_map and contacts_map.get(activity_id):
        return "contact"

    if activity_id in accounts_map and accounts_map.get(activity_id):
        return "account"

    return None


def build_note_item(
    row: Dict[str, Any],
    note_scope: Optional[str],
    accounts_map: Dict[int, List[Dict[str, Any]]],
    contacts_map: Dict[int, List[Dict[str, Any]]],
    deals_map: Dict[int, List[Dict[str, Any]]],
    user_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    activity_id = int(row.get("note_id"))
    details = safe_json_decode(row.get("activity_details"), {})
    note_type = determine_note_type(activity_id, note_scope, accounts_map, contacts_map, deals_map)

    account = None
    contact = None
    deal = None

    if note_type == "account":
        account = (accounts_map.get(activity_id) or [None])[0]
    elif note_type == "contact":
        contact = (contacts_map.get(activity_id) or [None])[0]
    elif note_type == "deal":
        deal = (deals_map.get(activity_id) or [None])[0]

    return {
        "note_id": row.get("note_id"),
        "note_type": note_type,
        "subject": first_non_empty(details.get("Subject"), details.get("subject"), row.get("activity_name")),
        "note": first_non_empty(details.get("Note"), details.get("note")),
        "account": account,
        "contact": contact,
        "deal": deal,
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date")),
    }

def hydrate_note_rows(connection: Any, rows: List[Dict[str, Any]], note_scope: Optional[str]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    activity_ids = [int(row.get("note_id")) for row in rows if row.get("note_id") is not None]

    accounts_map = fetch_note_accounts(connection, activity_ids)
    contacts_map = fetch_note_contacts(connection, activity_ids)
    deals_map = fetch_note_deals(connection, activity_ids)

    user_ids: List[Any] = []

    for row in rows:
        user_ids.extend([row.get("created_by"), row.get("modified_by")])

    user_map = fetch_users(connection, user_ids)

    return [
        build_note_item(
            row=row,
            note_scope=note_scope,
            accounts_map=accounts_map,
            contacts_map=contacts_map,
            deals_map=deals_map,
            user_map=user_map,
        )
        for row in rows
    ]


# -----------------------------
# Public service functions
# -----------------------------

def fetch_notes_list(
    client_database: str,
    note_scope: Optional[str] = None,
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
        note_scope = normalize_note_scope(note_scope)
        connection = get_client_connection(client_database)
        where_clause, params = build_where_clause(
            note_scope=note_scope,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
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
                las.activity_id AS note_id,
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

        items = hydrate_note_rows(connection, rows, note_scope)

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


def fetch_note_detail(
    client_database: str,
    note_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None

    try:
        connection = get_client_connection(client_database)

        sql = """
            SELECT
                las.activity_id AS note_id,
                las.activity_name,
                las.activity_details,
                las.created_by,
                las.created_date,
                las.modified_by,
                las.modified_date
            FROM lk_activity_schedule las
            WHERE las.activity_type = 'note'
              AND (las.active_status IS NULL OR las.active_status <> 'deleted')
              AND las.activity_id = %s
            LIMIT 1
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, [note_id])
            row = cursor.fetchone()

        if not row:
            return None

        items = hydrate_note_rows(connection, [row], None)

        if not items:
            return None

        return items[0]

    finally:
        if connection:
            connection.close()
