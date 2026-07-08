# app/services/activities_service.py

import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_activity.v1"
DEFAULT_MASTER_USER_TABLE = "logiklu0_leadactuator.zp_users"

SUPPORTED_DB_ACTIVITY_TYPES = ["call", "meeting", "videomeeting", "task"]
SUPPORT_CRITICALITY_LABELS = {
    "P0": "Blocker",
    "P1": "Critical",
    "P2": "High",
    "P3": "Medium",
    "P4": "Low",
}


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


def to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except Exception:
        return None


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


def format_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


def clean_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def split_csv_values(value: Any) -> List[str]:
    value = clean_value(value)

    if not value:
        return []

    return [item.strip() for item in value.split(",") if item.strip()]


def split_id_values(value: Any) -> List[int]:
    ids: List[int] = []

    for item in split_csv_values(value):
        parsed_id = to_int(item)
        if parsed_id is not None:
            ids.append(parsed_id)

    return ids


def unique_ints(values: List[Any]) -> List[int]:
    output: List[int] = []
    seen = set()

    for value in values:
        parsed_id = to_int(value)

        if parsed_id is None or parsed_id <= 0 or parsed_id in seen:
            continue

        seen.add(parsed_id)
        output.append(parsed_id)

    return output


def make_placeholders(values: List[Any]) -> str:
    return ",".join(["%s"] * len(values))


def parse_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    text = str(value).strip().lower()

    if text in ["1", "true", "yes", "y", "on"]:
        return True

    if text in ["0", "false", "no", "n", "off"]:
        return False

    return None


def flag_to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in ["1", "true", "yes", "y", "on"]


def normalize_activity_type_for_db(value: Any) -> Optional[str]:
    value = clean_value(value)

    if not value:
        return None

    value = value.lower()

    if value in ["video_call", "video-call", "video call", "videocall", "videomeeting", "video_meeting"]:
        return "videomeeting"

    if value in ["call", "meeting", "task"]:
        return value

    return value


def normalize_activity_type_for_api(value: Any) -> Optional[str]:
    value = clean_value(value)

    if not value:
        return None

    value = value.lower()

    if value == "videomeeting":
        return "video_call"

    return value


def parse_reminder_list(value: Any) -> List[Dict[str, Any]]:
    decoded = safe_json_decode(value, [])

    if not isinstance(decoded, list):
        return []

    output: List[Dict[str, Any]] = []

    for item in decoded:
        if not isinstance(item, dict):
            continue

        output.append(
            {
                "unit": item.get("unit"),
                "value": str(item.get("value")) if item.get("value") is not None else None,
            }
        )

    return output


def format_contact_phone(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, dict):
        country_code = str(value.get("country_code") or "").strip()
        phone = str(value.get("phone") or value.get("number") or "").strip()
        return " ".join([part for part in [country_code, phone] if part]).strip() or None

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
            return " ".join([part for part in [country_code, phone] if part]).strip() or None

    return text


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


def append_exact_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
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
    if clean_value(from_value) is not None:
        where_parts.append(f"{expression} >= %s")
        params.append(str(from_value).strip())

    if clean_value(to_value) is not None:
        where_parts.append(f"{expression} <= %s")
        params.append(str(to_value).strip())


def append_activity_type_filter(where_parts: List[str], params: List[Any], value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    db_values = []
    for token in tokens:
        db_value = normalize_activity_type_for_db(token)
        if db_value and db_value in SUPPORTED_DB_ACTIVITY_TYPES:
            db_values.append(db_value)

    if not db_values:
        return

    if len(db_values) == 1:
        where_parts.append("a.activity_type = %s")
        params.append(db_values[0])
        return

    where_parts.append(f"a.activity_type IN ({make_placeholders(db_values)})")
    params.extend(db_values)


def activity_for_condition(activity_for: Any) -> Tuple[Optional[str], List[Any]]:
    value = clean_value(activity_for)

    if not value:
        return None, []

    value = value.lower()

    if value in ["all", "any"]:
        return None, []

    if value in ["account", "lead"]:
        return (
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_leads al_for
                WHERE al_for.activity_id = a.activity_id
                  AND al_for.lead_id IS NOT NULL
                  AND al_for.lead_id <> 0
            )
            """,
            [],
        )

    if value in ["deal", "opportunity"]:
        return (
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_opportunities ao_for
                WHERE ao_for.activity_id = a.activity_id
                  AND ao_for.opportunity_id IS NOT NULL
                  AND ao_for.opportunity_id <> 0
            )
            """,
            [],
        )

    if value == "contact":
        return (
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_contacts ac_for
                WHERE ac_for.activity_id = a.activity_id
                  AND ac_for.contact_role = 'contact'
                  AND ac_for.contact_id IS NOT NULL
                  AND ac_for.contact_id <> 0
            )
            """,
            [],
        )

    if value == "general":
        return (
            """
            NOT EXISTS (
                SELECT 1
                FROM lk_activity_leads al_for
                WHERE al_for.activity_id = a.activity_id
                  AND al_for.lead_id IS NOT NULL
                  AND al_for.lead_id <> 0
            )
            AND NOT EXISTS (
                SELECT 1
                FROM lk_activity_opportunities ao_for
                WHERE ao_for.activity_id = a.activity_id
                  AND ao_for.opportunity_id IS NOT NULL
                  AND ao_for.opportunity_id <> 0
            )
            AND NOT EXISTS (
                SELECT 1
                FROM lk_activity_contacts ac_for
                WHERE ac_for.activity_id = a.activity_id
                  AND ac_for.contact_role = 'contact'
                  AND ac_for.contact_id IS NOT NULL
                  AND ac_for.contact_id <> 0
            )
            """,
            [],
        )

    return None, []


def append_account_filters(where_parts: List[str], params: List[Any], filter_params: Dict[str, Any]) -> None:
    if clean_value(filter_params.get("account_id")) is not None or clean_value(filter_params.get("lead_id")) is not None:
        append_integer_filter(
            where_parts,
            params,
            """
            (
                SELECT al_filter.lead_id
                FROM lk_activity_leads al_filter
                WHERE al_filter.activity_id = a.activity_id
                LIMIT 1
            )
            """,
            first_non_empty(filter_params.get("account_id"), filter_params.get("lead_id")),
        )

    account_like_filters = [
        ("account_name", ["lm_filter.lead_name"]),
        ("lead_name", ["lm_filter.lead_name"]),
        ("account_type", ["lm_filter.lead_type"]),
        ("account_city", ["lm_filter.city"]),
        ("account_state", ["lm_filter.state"]),
        ("account_country", ["lm_filter.country"]),
    ]

    for key, expressions in account_like_filters:
        value = filter_params.get(key)
        if clean_value(value) is None:
            continue

        inner_clauses = []
        inner_params: List[Any] = []
        append_like_filter(inner_clauses, inner_params, expressions, value)

        if inner_clauses:
            where_parts.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM lk_activity_leads al_filter
                    INNER JOIN lk_lead_master lm_filter
                        ON lm_filter.lead_id = al_filter.lead_id
                    WHERE al_filter.activity_id = a.activity_id
                      AND {' AND '.join(inner_clauses)}
                )
                """
            )
            params.extend(inner_params)


def append_deal_filters(where_parts: List[str], params: List[Any], filter_params: Dict[str, Any]) -> None:
    if clean_value(filter_params.get("deal_id")) is not None or clean_value(filter_params.get("opportunity_id")) is not None:
        append_integer_filter(
            where_parts,
            params,
            """
            (
                SELECT ao_filter.opportunity_id
                FROM lk_activity_opportunities ao_filter
                WHERE ao_filter.activity_id = a.activity_id
                LIMIT 1
            )
            """,
            first_non_empty(filter_params.get("deal_id"), filter_params.get("opportunity_id")),
        )

    deal_like_filters = [
        ("deal_name", ["o_filter.opportunity_name"]),
        ("opportunity_name", ["o_filter.opportunity_name"]),
        ("deal_status", ["o_filter.oportunity_status", "o_filter.status"]),
    ]

    for key, expressions in deal_like_filters:
        value = filter_params.get(key)
        if clean_value(value) is None:
            continue

        inner_clauses = []
        inner_params: List[Any] = []
        append_like_filter(inner_clauses, inner_params, expressions, value)

        if inner_clauses:
            where_parts.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM lk_activity_opportunities ao_filter
                    INNER JOIN lk_opportunities o_filter
                        ON o_filter.opportunity_id = ao_filter.opportunity_id
                    WHERE ao_filter.activity_id = a.activity_id
                      AND {' AND '.join(inner_clauses)}
                )
                """
            )
            params.extend(inner_params)


def append_contact_filters(where_parts: List[str], params: List[Any], filter_params: Dict[str, Any]) -> None:
    if clean_value(filter_params.get("contact_id")) is not None:
        append_integer_filter(
            where_parts,
            params,
            """
            (
                SELECT ac_filter.contact_id
                FROM lk_activity_contacts ac_filter
                WHERE ac_filter.activity_id = a.activity_id
                  AND ac_filter.contact_role = 'contact'
                  AND ac_filter.contact_id IS NOT NULL
                  AND ac_filter.contact_id <> 0
                LIMIT 1
            )
            """,
            filter_params.get("contact_id"),
        )

    contact_like_filters = [
        ("contact_name", ["cc_filter.first_name", "cc_filter.last_name", "CONCAT_WS(' ', cc_filter.first_name, cc_filter.last_name)"]),
        ("contact_email", ["cc_filter.email"]),
        ("contact_phone", ["cc_filter.primary_phone", "cc_filter.whatsappno", "cc_filter.alternative_phone"]),
    ]

    for key, expressions in contact_like_filters:
        value = filter_params.get(key)
        if clean_value(value) is None:
            continue

        inner_clauses = []
        inner_params: List[Any] = []
        append_like_filter(inner_clauses, inner_params, expressions, value)

        if inner_clauses:
            where_parts.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM lk_activity_contacts ac_filter
                    INNER JOIN lk_central_contacts cc_filter
                        ON cc_filter.contact_id = ac_filter.contact_id
                    WHERE ac_filter.activity_id = a.activity_id
                      AND ac_filter.contact_role = 'contact'
                      AND ac_filter.contact_id IS NOT NULL
                      AND ac_filter.contact_id <> 0
                      AND {' AND '.join(inner_clauses)}
                )
                """
            )
            params.extend(inner_params)


def append_recipient_filters(where_parts: List[str], params: List[Any], filter_params: Dict[str, Any]) -> None:
    recipient_type = clean_value(filter_params.get("recipient_type"))
    if recipient_type:
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_contacts ac_rec
                WHERE ac_rec.activity_id = a.activity_id
                  AND ac_rec.contact_role IN ('host', 'guest')
                  AND ac_rec.contact_role = %s
            )
            """
        )
        params.append(recipient_type)

    user_id_value = first_non_empty(
        filter_params.get("recipient_user_id"),
        filter_params.get("host_user_id"),
        filter_params.get("guest_user_id"),
        filter_params.get("user_id"),
    )
    if clean_value(user_id_value) is not None:
        append_integer_filter(
            where_parts,
            params,
            """
            (
                SELECT ac_rec.user_id
                FROM lk_activity_contacts ac_rec
                WHERE ac_rec.activity_id = a.activity_id
                  AND ac_rec.contact_role IN ('host', 'guest')
                  AND ac_rec.user_id IS NOT NULL
                  AND ac_rec.user_id <> 0
                LIMIT 1
            )
            """,
            user_id_value,
        )

    recipient_contact_id = first_non_empty(filter_params.get("recipient_contact_id"), filter_params.get("guest_contact_id"))
    if clean_value(recipient_contact_id) is not None:
        append_integer_filter(
            where_parts,
            params,
            """
            (
                SELECT ac_rec.contact_id
                FROM lk_activity_contacts ac_rec
                WHERE ac_rec.activity_id = a.activity_id
                  AND ac_rec.contact_role IN ('host', 'guest')
                  AND ac_rec.contact_id IS NOT NULL
                  AND ac_rec.contact_id <> 0
                LIMIT 1
            )
            """,
            recipient_contact_id,
        )

    recipient_search_value = first_non_empty(
        filter_params.get("recipient_search"),
        filter_params.get("recipient_name"),
        filter_params.get("recipient_email"),
        filter_params.get("recipient_phone"),
    )

    if clean_value(recipient_search_value) is not None:
        tokens = split_csv_values(recipient_search_value)
        if tokens:
            clauses = []
            for token in tokens:
                like_value = f"%{token}%"
                clauses.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM lk_activity_contacts ac_rec
                        LEFT JOIN lk_central_contacts cc_rec
                            ON cc_rec.contact_id = ac_rec.contact_id
                           AND ac_rec.contact_id IS NOT NULL
                           AND ac_rec.contact_id <> 0
                        LEFT JOIN {DEFAULT_MASTER_USER_TABLE} mu_rec
                            ON mu_rec.id = ac_rec.user_id
                           AND ac_rec.user_id IS NOT NULL
                           AND ac_rec.user_id <> 0
                        WHERE ac_rec.activity_id = a.activity_id
                          AND ac_rec.contact_role IN ('host', 'guest')
                          AND (
                              cc_rec.first_name LIKE %s
                              OR cc_rec.last_name LIKE %s
                              OR CONCAT_WS(' ', cc_rec.first_name, cc_rec.last_name) LIKE %s
                              OR cc_rec.email LIKE %s
                              OR cc_rec.primary_phone LIKE %s
                              OR mu_rec.name LIKE %s
                              OR mu_rec.full_name LIKE %s
                              OR CONCAT_WS(' ', mu_rec.first_name, mu_rec.middle_name, mu_rec.last_name) LIKE %s
                              OR mu_rec.email LIKE %s
                              OR mu_rec.username LIKE %s
                          )
                    )
                    """
                )
                params.extend([like_value] * 10)

            where_parts.append("(" + " OR ".join(clauses) + ")")


def append_record_filters(where_parts: List[str], params: List[Any], filter_params: Dict[str, Any]) -> None:
    has_records = parse_bool(filter_params.get("has_records"))

    if has_records is True:
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_record ar_filter
                WHERE ar_filter.activity_id = a.activity_id
                  AND (ar_filter.active_status IS NULL OR ar_filter.active_status <> 'deleted')
            )
            """
        )
    elif has_records is False:
        where_parts.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM lk_activity_record ar_filter
                WHERE ar_filter.activity_id = a.activity_id
                  AND (ar_filter.active_status IS NULL OR ar_filter.active_status <> 'deleted')
            )
            """
        )

    record_type = clean_value(filter_params.get("record_type"))
    if record_type:
        where_parts.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_activity_record ar_filter
                WHERE ar_filter.activity_id = a.activity_id
                  AND ar_filter.record_type = %s
                  AND (ar_filter.active_status IS NULL OR ar_filter.active_status <> 'deleted')
            )
            """
        )
        params.append(record_type)

    record_search = first_non_empty(filter_params.get("record_name"), filter_params.get("record_details"))
    if clean_value(record_search) is not None:
        tokens = split_csv_values(record_search)
        clauses = []
        for token in tokens:
            like_value = f"%{token}%"
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_activity_record ar_filter
                    WHERE ar_filter.activity_id = a.activity_id
                      AND (ar_filter.reord_name LIKE %s OR ar_filter.record_details LIKE %s)
                      AND (ar_filter.active_status IS NULL OR ar_filter.active_status <> 'deleted')
                )
                """
            )
            params.extend([like_value, like_value])

        if clauses:
            where_parts.append("(" + " OR ".join(clauses) + ")")


def append_user_name_filter(where_parts: List[str], params: List[Any], field_expression: str, value: Any) -> None:
    if clean_value(value) is None:
        return

    tokens = split_csv_values(value)
    clauses = []

    for token in tokens:
        like_value = f"%{token}%"
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM {DEFAULT_MASTER_USER_TABLE} mu_filter
                WHERE mu_filter.id = {field_expression}
                  AND (
                      mu_filter.name LIKE %s
                      OR mu_filter.full_name LIKE %s
                      OR mu_filter.first_name LIKE %s
                      OR mu_filter.last_name LIKE %s
                      OR CONCAT_WS(' ', mu_filter.first_name, mu_filter.middle_name, mu_filter.last_name) LIKE %s
                      OR mu_filter.email LIKE %s
                      OR mu_filter.username LIKE %s
                  )
            )
            """
        )
        params.extend([like_value] * 7)

    if clauses:
        where_parts.append("(" + " OR ".join(clauses) + ")")


def append_advanced_filters(where_parts: List[str], params: List[Any], filters: Optional[str]) -> None:
    decoded = safe_json_decode(filters, []) if filters else []

    if not isinstance(decoded, list):
        return

    simple_map = {
        "activity_id": "a.activity_id",
        "activity_category": "a.activity_category",
        "activity_name": "a.activity_name",
        "activity_description": "a.activity_description",
        "activity_location": "a.activity_location",
        "join_url": "a.join_url",
        "status": "a.status",
        "active_status": "a.active_status",
        "owner": "a.owner",
        "created_by": "a.created_by",
        "modified_by": "a.modified_by",
    }

    for item in decoded:
        if not isinstance(item, dict):
            continue

        field = clean_value(item.get("field"))
        operator = clean_value(item.get("operator")) or "eq"
        value = item.get("value")

        if not field or field not in simple_map:
            continue

        expression = simple_map[field]
        operator = operator.lower()

        if operator in ["eq", "="]:
            where_parts.append(f"{expression} = %s")
            params.append(value)
        elif operator in ["neq", "!="]:
            where_parts.append(f"{expression} <> %s")
            params.append(value)
        elif operator in ["like", "contains"]:
            where_parts.append(f"{expression} LIKE %s")
            params.append(f"%{value}%")
        elif operator == "in" and isinstance(value, list) and value:
            where_parts.append(f"{expression} IN ({make_placeholders(value)})")
            params.extend(value)
        elif operator in ["from", "gte", ">="]:
            where_parts.append(f"{expression} >= %s")
            params.append(value)
        elif operator in ["to", "lte", "<="]:
            where_parts.append(f"{expression} <= %s")
            params.append(value)
        elif operator == "between" and isinstance(value, list) and len(value) == 2:
            where_parts.append(f"{expression} BETWEEN %s AND %s")
            params.extend([value[0], value[1]])


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any]]:
    filter_params = filter_params or {}
    where_parts: List[str] = []
    params: List[Any] = []

    where_parts.append(f"a.activity_type IN ({make_placeholders(SUPPORTED_DB_ACTIVITY_TYPES)})")
    params.extend(SUPPORTED_DB_ACTIVITY_TYPES)

    active_status = clean_value(filter_params.get("active_status"))
    if active_status:
        active_status = active_status.lower()
        if active_status == "all":
            where_parts.append("(a.active_status IS NULL OR a.active_status <> 'deleted')")
        elif active_status in ["active", "archived", "deleted"]:
            where_parts.append("a.active_status = %s")
            params.append(active_status)
    else:
        where_parts.append("(a.active_status IS NULL OR a.active_status = 'active')")

    condition, condition_params = activity_for_condition(filter_params.get("activity_for"))
    if condition:
        where_parts.append("(" + condition + ")")
        params.extend(condition_params)

    append_activity_type_filter(where_parts, params, filter_params.get("activity_type"))

    if clean_value(filter_params.get("activity_id")) is not None:
        append_integer_filter(where_parts, params, "a.activity_id", filter_params.get("activity_id"))

    append_like_filter(where_parts, params, ["a.activity_category"], filter_params.get("activity_category"))
    append_like_filter(where_parts, params, ["a.activity_name"], filter_params.get("activity_name"))
    append_like_filter(where_parts, params, ["a.activity_description"], filter_params.get("activity_description"))
    append_like_filter(where_parts, params, ["a.activity_location"], filter_params.get("activity_location"))
    append_like_filter(where_parts, params, ["a.join_url"], filter_params.get("join_url"))
    append_like_filter(where_parts, params, ["a.calendar_id"], filter_params.get("calendar_id"))

    append_exact_filter(where_parts, params, "a.status", filter_params.get("status"))
    append_exact_filter(where_parts, params, "a.all_day", filter_params.get("all_day"))

    append_date_range_filter(where_parts, params, "a.startdate", filter_params.get("startdate_from"), filter_params.get("startdate_to"))
    append_date_range_filter(where_parts, params, "a.enddate", filter_params.get("enddate_from"), filter_params.get("enddate_to"))
    append_date_range_filter(where_parts, params, "a.created_date", filter_params.get("created_date_from"), filter_params.get("created_date_to"))
    append_date_range_filter(where_parts, params, "a.modified_date", filter_params.get("modified_date_from"), filter_params.get("modified_date_to"))
    append_date_range_filter(where_parts, params, "a.followup_date", filter_params.get("followup_date_from"), filter_params.get("followup_date_to"))

    append_integer_filter(where_parts, params, "a.owner", filter_params.get("owner"))
    append_integer_filter(where_parts, params, "a.created_by", filter_params.get("created_by"))
    append_integer_filter(where_parts, params, "a.modified_by", filter_params.get("modified_by"))

    append_user_name_filter(where_parts, params, "a.owner", filter_params.get("owner_name"))
    append_user_name_filter(where_parts, params, "a.created_by", filter_params.get("created_by_name"))
    append_user_name_filter(where_parts, params, "a.modified_by", filter_params.get("modified_by_name"))

    is_followup = parse_bool(filter_params.get("is_followup"))
    if is_followup is not None:
        where_parts.append("a.if_followup = %s")
        params.append("1" if is_followup else "0")

    is_support_call = parse_bool(filter_params.get("is_support_call"))
    if is_support_call is not None:
        where_parts.append("a.is_support_call = %s")
        params.append("1" if is_support_call else "0")

    append_integer_filter(where_parts, params, "a.support_call_type_id", filter_params.get("support_call_type_id"))
    append_like_filter(where_parts, params, ["sct.support_call_type_name"], filter_params.get("support_call_type_name"))
    append_exact_filter(where_parts, params, "a.support_call_criticality", filter_params.get("support_call_criticality"))

    append_account_filters(where_parts, params, filter_params)
    append_deal_filters(where_parts, params, filter_params)
    append_contact_filters(where_parts, params, filter_params)
    append_recipient_filters(where_parts, params, filter_params)
    append_record_filters(where_parts, params, filter_params)

    if clean_value(search) is not None:
        search_fields = {
            "activity_name": ["a.activity_name"],
            "activity_description": ["a.activity_description"],
            "activity_location": ["a.activity_location"],
            "activity_category": ["a.activity_category"],
            "join_url": ["a.join_url"],
            "status": ["a.status"],
            "active_status": ["a.active_status"],
            "support_call_type_name": ["sct.support_call_type_name"],
            "support_call_criticality": ["a.support_call_criticality"],
        }

        if clean_value(search_by) and str(search_by).strip() in search_fields:
            append_like_filter(where_parts, params, search_fields[str(search_by).strip()], search)
        else:
            append_like_filter(
                where_parts,
                params,
                [
                    "a.activity_name",
                    "a.activity_description",
                    "a.activity_location",
                    "a.activity_category",
                    "a.join_url",
                    "a.status",
                    "a.active_status",
                    "sct.support_call_type_name",
                    "a.support_call_criticality",
                ],
                search,
            )

    append_advanced_filters(where_parts, params, filters)

    return " AND ".join(where_parts), params


# -----------------------------
# User and related data fetchers
# -----------------------------

def fetch_users(connection: Any, user_ids: List[Any]) -> Dict[int, Dict[str, Any]]:
    ids = unique_ints(user_ids)

    if not ids:
        return {}

    try:
        sql = f"SELECT * FROM {DEFAULT_MASTER_USER_TABLE} WHERE id IN ({make_placeholders(ids)})"

        with connection.cursor() as cursor:
            cursor.execute(sql, ids)
            rows = cursor.fetchall()

        users: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            user_id = to_int(row.get("id") or row.get("user_id"))
            if user_id is None:
                continue

            full_name = first_non_empty(
                row.get("name"),
                row.get("full_name"),
                " ".join(
                    [
                        str(row.get("first_name") or "").strip(),
                        str(row.get("middle_name") or "").strip(),
                        str(row.get("last_name") or "").strip(),
                    ]
                ).strip(),
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
        return {}


def get_user(user_map: Dict[int, Dict[str, Any]], user_id: Any) -> Optional[Dict[str, Any]]:
    parsed_id = to_int(user_id)

    if parsed_id is None or parsed_id <= 0:
        return None

    return user_map.get(parsed_id)


def fetch_account_map(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            al.activity_id,
            lm.lead_id AS account_id,
            lm.lead_name AS account_name,
            lm.lead_type AS account_type,
            lm.city,
            lm.state,
            lm.country
        FROM lk_activity_leads al
        INNER JOIN lk_lead_master lm
            ON lm.lead_id = al.lead_id
        WHERE al.activity_id IN ({make_placeholders(activity_ids)})
          AND al.lead_id IS NOT NULL
          AND al.lead_id <> 0
        ORDER BY al.activity_id ASC, al.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))
        if activity_id is None:
            continue

        output.setdefault(activity_id, []).append(
            {
                "account_id": to_int(row.get("account_id")),
                "name": row.get("account_name"),
                "account_type": row.get("account_type"),
                "location": {
                    "city": row.get("city"),
                    "state": row.get("state"),
                    "country": row.get("country"),
                },
            }
        )

    return output


def fetch_deal_map(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            ao.activity_id,
            o.opportunity_id AS deal_id,
            o.opportunity_name AS deal_name,
            o.oportunity_status AS deal_status,
            o.status
        FROM lk_activity_opportunities ao
        INNER JOIN lk_opportunities o
            ON o.opportunity_id = ao.opportunity_id
        WHERE ao.activity_id IN ({make_placeholders(activity_ids)})
          AND ao.opportunity_id IS NOT NULL
          AND ao.opportunity_id <> 0
        ORDER BY ao.activity_id ASC, ao.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))
        if activity_id is None:
            continue

        output.setdefault(activity_id, []).append(
            {
                "deal_id": to_int(row.get("deal_id")),
                "name": row.get("deal_name"),
                "deal_status": row.get("deal_status"),
            }
        )

    return output


def fetch_activity_contact_map(connection: Any, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            ac.activity_id,
            ac.contact_id,
            cc.first_name,
            cc.last_name,
            cc.email,
            cc.primary_phone,
            cc.whatsappno
        FROM lk_activity_contacts ac
        INNER JOIN lk_central_contacts cc
            ON cc.contact_id = ac.contact_id
        WHERE ac.activity_id IN ({make_placeholders(activity_ids)})
          AND ac.contact_role = 'contact'
          AND ac.contact_id IS NOT NULL
          AND ac.contact_id <> 0
        ORDER BY ac.activity_id ASC, ac.id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))
        if activity_id is None:
            continue

        name = " ".join([str(row.get("first_name") or "").strip(), str(row.get("last_name") or "").strip()]).strip()

        output.setdefault(activity_id, []).append(
            {
                "contact_id": to_int(row.get("contact_id")),
                "name": name or None,
                "email": row.get("email"),
                "phone": format_contact_phone(first_non_empty(row.get("primary_phone"), row.get("whatsappno"))),
            }
        )

    return output


def fetch_recipients_map(connection: Any, activity_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not activity_ids:
        return {}

    sql = f"""
        SELECT
            ac.activity_id,
            ac.contact_role,
            ac.contact_id,
            ac.user_id,
            cc.first_name AS contact_first_name,
            cc.last_name AS contact_last_name,
            cc.email AS contact_email,
            mu.first_name AS user_first_name,
            mu.middle_name AS user_middle_name,
            mu.last_name AS user_last_name,
            mu.email AS user_email,
            mu.username AS user_username
        FROM lk_activity_contacts ac
        LEFT JOIN lk_central_contacts cc
            ON cc.contact_id = ac.contact_id
           AND ac.contact_id IS NOT NULL
           AND ac.contact_id <> 0
        LEFT JOIN {DEFAULT_MASTER_USER_TABLE} mu
            ON mu.id = ac.user_id
           AND ac.user_id IS NOT NULL
           AND ac.user_id <> 0
        WHERE ac.activity_id IN ({make_placeholders(activity_ids)})
          AND ac.contact_role IN ('host', 'guest')
        ORDER BY ac.activity_id ASC, ac.id ASC
    """

    output: Dict[int, Dict[str, Any]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))
        if activity_id is None:
            continue

        recipients = output.setdefault(
            activity_id,
            {
                "host": None,
                "guest": [],
                "colleagues": [],
            },
        )

        contact_role = clean_value(row.get("contact_role"))
        contact_id = to_int(row.get("contact_id"))
        user_id = to_int(row.get("user_id"))

        if contact_role == "host" and user_id is not None and user_id > 0:
            name = first_non_empty(
                " ".join(
                    [
                        str(row.get("user_first_name") or "").strip(),
                        str(row.get("user_middle_name") or "").strip(),
                        str(row.get("user_last_name") or "").strip(),
                    ]
                ).strip(),
                row.get("user_username"),
            )
            email = first_non_empty(row.get("user_email"), row.get("user_username"))
            recipients["host"] = {
                "contact_id": user_id,
                "name": name,
                "email": email,
            }

        elif contact_role == "guest" and user_id is not None and user_id > 0:
            name = first_non_empty(
                " ".join(
                    [
                        str(row.get("user_first_name") or "").strip(),
                        str(row.get("user_middle_name") or "").strip(),
                        str(row.get("user_last_name") or "").strip(),
                    ]
                ).strip(),
                row.get("user_username"),
            )
            email = first_non_empty(row.get("user_email"), row.get("user_username"))
            recipients["colleagues"].append(
                {
                    "contact_id": user_id,
                    "name": name,
                    "email": email,
                }
            )

        elif contact_role == "guest" and contact_id is not None and contact_id > 0:
            name = " ".join(
                [
                    str(row.get("contact_first_name") or "").strip(),
                    str(row.get("contact_last_name") or "").strip(),
                ]
            ).strip()
            recipients["guest"].append(
                {
                    "contact_id": contact_id,
                    "name": name or None,
                    "email": row.get("contact_email"),
                }
            )

    return output

def fetch_records_map(connection: Any, activity_ids: List[int]) -> Tuple[Dict[int, List[Dict[str, Any]]], List[int]]:
    if not activity_ids:
        return {}, []

    sql = f"""
        SELECT
            ar.activity_id,
            ar.record_id,
            ar.record_type,
            ar.reord_name,
            ar.record_details,
            ar.created_by,
            ar.created_date,
            ar.modified_by,
            ar.modified_date,
            ar.active_status
        FROM lk_activity_record ar
        WHERE ar.activity_id IN ({make_placeholders(activity_ids)})
          AND (ar.active_status IS NULL OR ar.active_status <> 'deleted')
        ORDER BY ar.activity_id ASC, ar.created_date ASC, ar.record_id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}
    user_ids: List[int] = []

    with connection.cursor() as cursor:
        cursor.execute(sql, activity_ids)
        rows = cursor.fetchall()

    for row in rows:
        activity_id = to_int(row.get("activity_id"))
        if activity_id is None:
            continue

        user_ids.extend([row.get("created_by"), row.get("modified_by")])
        output.setdefault(activity_id, []).append(row)

    return output, unique_ints(user_ids)


# -----------------------------
# Response builders
# -----------------------------

def determine_activity_for(
    activity_id: int,
    account_map: Dict[int, List[Dict[str, Any]]],
    deal_map: Dict[int, List[Dict[str, Any]]],
    contact_map: Dict[int, List[Dict[str, Any]]],
) -> str:
    if deal_map.get(activity_id):
        return "deal"

    if account_map.get(activity_id):
        return "account"

    if contact_map.get(activity_id):
        return "contact"

    return "general"


def build_support_object(row: Dict[str, Any], activity_type: Optional[str]) -> Dict[str, Any]:
    if activity_type == "task":
        return {
            "is_support_call": False,
            "support_call_type": None,
            "criticality": None,
        }

    is_support_call = flag_to_bool(row.get("is_support_call"))

    support_call_type = None
    support_type_id = to_int(row.get("support_call_type_id"))

    if is_support_call and support_type_id is not None:
        support_call_type = {
            "id": support_type_id,
            "name": row.get("support_call_type_name"),
            "code": row.get("support_call_type_code"),
            "description": row.get("support_call_type_description"),
        }

    criticality_code = row.get("support_call_criticality") if is_support_call else None

    return {
        "is_support_call": is_support_call,
        "support_call_type": support_call_type,
        "criticality": {
            "code": criticality_code,
            "label": SUPPORT_CRITICALITY_LABELS.get(str(criticality_code or "").upper()),
        } if criticality_code else None,
    }


def build_followup_object(row: Dict[str, Any], activity_type: Optional[str]) -> Dict[str, Any]:
    if activity_type == "task":
        return {
            "is_followup": False,
            "followup_date": None,
        }

    return {
        "is_followup": flag_to_bool(row.get("if_followup")),
        "followup_date": format_datetime(row.get("followup_date")),
    }


def build_record_item(row: Dict[str, Any], user_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "record_id": to_int(row.get("record_id")),
        "record_type": row.get("record_type"),
        "record_name": row.get("reord_name"),
        "record_details": row.get("record_details"),
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date")),
        "active_status": row.get("active_status"),
    }


def build_activity_item(
    row: Dict[str, Any],
    account_map: Dict[int, List[Dict[str, Any]]],
    deal_map: Dict[int, List[Dict[str, Any]]],
    contact_map: Dict[int, List[Dict[str, Any]]],
    recipients_map: Dict[int, Dict[str, Any]],
    records_map: Dict[int, List[Dict[str, Any]]],
    user_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    activity_id = to_int(row.get("activity_id")) or 0
    activity_type = normalize_activity_type_for_api(row.get("activity_type"))
    activity_for = determine_activity_for(activity_id, account_map, deal_map, contact_map)

    return {
        "activity_id": activity_id,
        "activity_type": activity_type,
        "activity_for": activity_for,

        "account": (account_map.get(activity_id) or [None])[0],
        "deal": (deal_map.get(activity_id) or [None])[0],
        "contact": (contact_map.get(activity_id) or [None])[0],

        "activity_category": row.get("activity_category"),
        "activity_name": row.get("activity_name"),
        "activity_description": row.get("activity_description"),
        "activity_location": row.get("activity_location"),
        "join_url": row.get("join_url"),

        "schedule": {
            "startdate": format_datetime(row.get("startdate")),
            "enddate": format_datetime(row.get("enddate")),
            "all_day": row.get("all_day"),
            "timezone": row.get("timezone"),
        },

        "followup": build_followup_object(row, activity_type),
        "support": build_support_object(row, activity_type),
        "reminders": {
            "guest": parse_reminder_list(row.get("reminders_user_time")),
            "contact": parse_reminder_list(row.get("reminder_contact_time")),
        },
        "recipients": recipients_map.get(
            activity_id,
            {
                "host": None,
                "guest": [],
                "colleagues": [],
            },
        ),
        "activity_records": [
            build_record_item(record_row, user_map)
            for record_row in records_map.get(activity_id, [])
        ],
        "owner": get_user(user_map, row.get("owner")),
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date")),
        "status": row.get("status"),
        "active_status": row.get("active_status"),
    }


def hydrate_activity_rows(connection: Any, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    activity_ids = unique_ints([row.get("activity_id") for row in rows])
    account_map = fetch_account_map(connection, activity_ids)
    deal_map = fetch_deal_map(connection, activity_ids)
    contact_map = fetch_activity_contact_map(connection, activity_ids)
    recipients_map = fetch_recipients_map(connection, activity_ids)
    records_map, record_user_ids = fetch_records_map(connection, activity_ids)

    user_ids: List[Any] = []
    for row in rows:
        user_ids.extend([row.get("owner"), row.get("created_by"), row.get("modified_by")])

    user_ids.extend(record_user_ids)
    user_map = fetch_users(connection, user_ids)

    return [
        build_activity_item(
            row=row,
            account_map=account_map,
            deal_map=deal_map,
            contact_map=contact_map,
            recipients_map=recipients_map,
            records_map=records_map,
            user_map=user_map,
        )
        for row in rows
    ]


# -----------------------------
# Public service functions
# -----------------------------

def fetch_activities_list(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    connection = None

    page = max(int(page or 1), 1)
    per_page = max(int(per_page or 10), 1)
    offset = (page - 1) * per_page

    try:
        connection = get_client_connection(client_database)
        where_clause, params = build_where_clause(
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

        count_sql = f"""
            SELECT COUNT(DISTINCT a.activity_id) AS total_records
            FROM lk_activity_schedule a
            LEFT JOIN lk_support_call_type_master sct
                ON sct.support_call_type_id = a.support_call_type_id
               AND (sct.active_status IS NULL OR sct.active_status <> 'deleted')
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            count_row = cursor.fetchone()

        total_records = int((count_row or {}).get("total_records") or 0)
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0

        sql = f"""
            SELECT
                a.activity_id,
                a.activity_type,
                a.activity_category,
                a.calendar_id,
                a.activity_name,
                a.activity_description,
                a.activity_location,
                a.startdate,
                a.enddate,
                a.all_day,
                a.originalstarteenddate,
                a.join_url,
                a.owner,
                a.created_by,
                a.created_date,
                a.modified_by,
                a.modified_date,
                a.timezone,
                a.reminders_user_time,
                a.reminder_contact_time,
                a.if_followup,
                a.followup_date,
                a.is_support_call,
                a.support_call_type_id,
                a.support_call_criticality,
                a.status,
                a.active_status,
                sct.support_call_type_name,
                sct.support_call_type_code,
                sct.description AS support_call_type_description
            FROM lk_activity_schedule a
            LEFT JOIN lk_support_call_type_master sct
                ON sct.support_call_type_id = a.support_call_type_id
               AND (sct.active_status IS NULL OR sct.active_status <> 'deleted')
            WHERE {where_clause}
            ORDER BY a.created_date ASC, a.activity_id ASC
            LIMIT %s OFFSET %s
        """

        query_params = params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        items = hydrate_activity_rows(connection, rows)

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


def fetch_activity_detail(client_database: str, activity_id: int) -> Optional[Dict[str, Any]]:
    connection = None

    try:
        connection = get_client_connection(client_database)

        sql = f"""
            SELECT
                a.activity_id,
                a.activity_type,
                a.activity_category,
                a.calendar_id,
                a.activity_name,
                a.activity_description,
                a.activity_location,
                a.startdate,
                a.enddate,
                a.all_day,
                a.originalstarteenddate,
                a.join_url,
                a.owner,
                a.created_by,
                a.created_date,
                a.modified_by,
                a.modified_date,
                a.timezone,
                a.reminders_user_time,
                a.reminder_contact_time,
                a.if_followup,
                a.followup_date,
                a.is_support_call,
                a.support_call_type_id,
                a.support_call_criticality,
                a.status,
                a.active_status,
                sct.support_call_type_name,
                sct.support_call_type_code,
                sct.description AS support_call_type_description
            FROM lk_activity_schedule a
            LEFT JOIN lk_support_call_type_master sct
                ON sct.support_call_type_id = a.support_call_type_id
               AND (sct.active_status IS NULL OR sct.active_status <> 'deleted')
            WHERE a.activity_id = %s
              AND a.activity_type IN ({make_placeholders(SUPPORTED_DB_ACTIVITY_TYPES)})
              AND (a.active_status IS NULL OR a.active_status <> 'deleted')
            LIMIT 1
        """

        params = [activity_id] + SUPPORTED_DB_ACTIVITY_TYPES

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        if not row:
            return None

        items = hydrate_activity_rows(connection, [row])

        return items[0] if items else None

    finally:
        if connection:
            connection.close()
