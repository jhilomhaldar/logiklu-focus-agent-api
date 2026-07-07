import json
import math
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.config import settings
from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_account.v1"
DEFAULT_MASTER_USER_TABLE = "logiklu0_leadactuator.zp_users"
DEFAULT_ATTACHMENT_BASE_URL = "https://logiklu.com/app/v1/"

SOURCE_LABELS = {
    "website": "Website Visitor",
    "mailchimp": "Mass Mail",
    "leadform": "Form Submission",
    "innerform": "Inbuilt Form Submission",
    "manual": "Manual",
    "csv": "CSV",
    "whatsapp": "WhatsApp",
}


ALLOWED_FILTER_FIELDS = {
    # Account naming
    "account_id": "lm.lead_id",
    "account_name": "lm.lead_name",
    "account_segment": "lm.lead_segment",
    "account_category": "computed_account_category",
    "account_type": "lm.lead_type",
    "account_status_id": "lm.lead_persuing_status",
    "account_status_name": "lsm.lead_status_name",
    "account_source": "lm.lead_source",

    # Backward-compatible aliases
    "lead_id": "lm.lead_id",
    "lead_name": "lm.lead_name",
    "lead_segment": "lm.lead_segment",
    "lead_category": "computed_account_category",
    "lead_type": "lm.lead_type",
    "lead_status_id": "lm.lead_persuing_status",
    "lead_status_name": "lsm.lead_status_name",
    "lead_source": "lm.lead_source",

    "website": "lm.website",
    "email": "lm.email",
    "phone": "lm.phone",
    "industry": "lm.industry",
    "address": "lm.address",
    "city": "lm.city",
    "state": "lm.state",
    "country": "lm.country",
    "zipcode": "lm.zipcode",
    "source": "lm.source",
    "owner": "lm.owner",
    "created_by": "lm.created_by",
    "modified_by": "lm.modified_by",
    "created_date": "lm.created_date",
    "modified_date": "lm.modified_date",
    "status_change_date": "lm.status_change_date",
    "assigned_to": "assigned_to",
    "product_name": "product_name",
    "product_id": "product_id",
    "product_category_id": "product_category_id",
    "page_id": "page_id",

    # Account existence/relationship filters
    "is_lead": "is_lead",
    "has_contacts": "has_contacts",
    "with_contacts": "has_contacts",
    "account_with_contacts": "has_contacts",
    "has_notes": "has_notes",
    "with_notes": "has_notes",
    "account_with_notes": "has_notes",
    "has_attachments": "has_attachments",
    "with_attachments": "has_attachments",
    "account_with_attachments": "has_attachments",
    "has_activities": "has_activities",
    "with_activities": "has_activities",
    "account_with_activities": "has_activities",

    # Assigned user search by ID or name/email
    "assigned_user": "assigned_to",
    "assigned_user_id": "assigned_to",
    "assigned_user_search": "assigned_user_search",
    "assigned_user_name": "assigned_user_search",
    "assigned_user_email": "assigned_user_search",
    "assigned_by": "assigned_by",
    "assigned_by_search": "assigned_by_search",
}

ACCOUNT_SEARCH_FIELDS = {
    # Account naming
    "account_name": "lm.lead_name",
    "account_segment": "lm.lead_segment",
    "account_category": "computed_account_category",
    "account_type": "lm.lead_type",
    "account_status_id": "lm.lead_persuing_status",
    "account_status_name": "lsm.lead_status_name",
    "account_source": "lm.lead_source",

    # Backward-compatible aliases
    "lead_name": "lm.lead_name",
    "lead_segment": "lm.lead_segment",
    "lead_category": "computed_account_category",
    "lead_type": "lm.lead_type",
    "lead_persuing_status": "lm.lead_persuing_status",
    "lead_status_id": "lm.lead_persuing_status",
    "lead_status_name": "lsm.lead_status_name",
    "lead_source": "lm.lead_source",

    "website": "lm.website",
    "email": "lm.email",
    "phone": "lm.phone",
    "industry": "lm.industry",
    "address": "lm.address",
    "city": "lm.city",
    "state": "lm.state",
    "country": "lm.country",
    "zipcode": "lm.zipcode",
    "owner": "lm.owner",
    "created_by": "lm.created_by",
    "modified_by": "lm.modified_by",
    "source": "lm.source",
    "assigned_to": "assigned_to",
    "assigned_user": "assigned_to",
    "assigned_user_id": "assigned_to",
    "assigned_user_search": "assigned_user_search",
    "assigned_user_name": "assigned_user_search",
    "assigned_user_email": "assigned_user_search",
    "assigned_by": "assigned_by",
    "assigned_by_search": "assigned_by_search",
    "employee_count": "employee_count",
    "product_name": "product_name",
}

MULTI_VALUE_ACCOUNT_SEARCH_FIELDS = {
    "account_segment",
    "account_type",
    "account_status_id",
    "account_source",
    "lead_segment",
    "lead_type",
    "lead_persuing_status",
    "lead_status_id",
    "lead_source",
    "country",
    "owner",
    "created_by",
    "modified_by",
    "source",
    "assigned_to",
    "assigned_user",
    "assigned_user_id",
    "assigned_by",
}


# -----------------------------
# Generic helpers
# -----------------------------

def parse_json_value(value: Any) -> Any:
    if value is None or value == "":
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    try:
        return json.loads(value)
    except Exception:
        return value


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


def format_datetime(value: Any, timezone_name: Optional[str] = None) -> Optional[str]:
    if value is None:
        return None

    if not isinstance(value, datetime):
        return str(value)

    tz_name = str(timezone_name or "").strip()

    if not tz_name or tz_name.upper() in ["UTC", "HMT"]:
        return value.strftime("%Y-%m-%d %H:%M:%S")

    try:
        local_dt = value.replace(tzinfo=ZoneInfo(tz_name))
        utc_dt = local_dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return value.strftime("%Y-%m-%d %H:%M:%S")


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


def format_phone(phone_value: Any) -> Optional[str]:
    parsed = parse_json_value(phone_value)

    if isinstance(parsed, dict):
        country_code = str(
            parsed.get("country_code")
            or parsed.get("counyry_code")
            or ""
        ).strip()
        phone = str(parsed.get("phone") or parsed.get("number") or "").strip()
        combined = " ".join([part for part in [country_code, phone] if part]).strip()
        return combined or None

    text = str(phone_value or "").strip()
    return text or None


def format_employee_count(lower_range: Any, upper_range: Any) -> str:
    lower = str(lower_range or "").strip()
    upper = str(upper_range or "").strip()

    if lower and upper:
        return f"{lower} to {upper}"

    if not lower and upper:
        return f"0 to {upper}"

    if lower and not upper:
        return f"{lower}+"

    return ""


def source_label(source: Any) -> str:
    source_value = str(source or "").strip()

    if not source_value:
        return ""

    if source_value in SOURCE_LABELS:
        return SOURCE_LABELS[source_value]

    return source_value[:1].upper() + source_value[1:]


def split_search_values(value: Any) -> List[str]:
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


def unique_ints(values: List[Any]) -> List[int]:
    output = []
    seen = set()

    for value in values:
        parsed = to_int(value)

        if parsed is None or parsed <= 0 or parsed in seen:
            continue

        seen.add(parsed)
        output.append(parsed)

    return output


def make_placeholders(values: List[Any]) -> str:
    return ",".join(["%s"] * len(values))


def get_master_user_table() -> str:
    # Account user lookup must use the LogiKlu actuator user table, same as Deals.
    return DEFAULT_MASTER_USER_TABLE


def get_attachment_base_url() -> str:
    base_url = str(getattr(settings, "ATTACHMENT_BASE_URL", DEFAULT_ATTACHMENT_BASE_URL) or DEFAULT_ATTACHMENT_BASE_URL).strip()

    if not base_url:
        base_url = DEFAULT_ATTACHMENT_BASE_URL

    return base_url.rstrip("/") + "/"


def extract_original_filename(value: Any) -> Optional[str]:
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

    path = str(fullpath).replace("\\", "/").replace("\\/", "/").strip()

    if not path:
        return None

    marker = "app/v1/"
    if marker in path:
        path = path.split(marker, 1)[1]

    if "attachments/" in path:
        path = path[path.find("attachments/"):]

    return get_attachment_base_url() + path.lstrip("/")


# -----------------------------
# User helpers
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

    if parsed_id is None or parsed_id <= 0:
        return None

    return user_map.get(parsed_id) or {"id": parsed_id, "name": None, "email": None}


# -----------------------------
# Category/filter helpers
# -----------------------------

def customer_exists_condition() -> str:
    return """
    EXISTS (
        SELECT 1
        FROM lk_customer_master cm_category
        WHERE cm_category.lead_id = lm.lead_id
          AND (cm_category.active_status IS NULL OR cm_category.active_status <> 'deleted')
    )
    """


def customer_not_exists_condition() -> str:
    return """
    NOT EXISTS (
        SELECT 1
        FROM lk_customer_master cm_category
        WHERE cm_category.lead_id = lm.lead_id
          AND (cm_category.active_status IS NULL OR cm_category.active_status <> 'deleted')
    )
    """


def active_contact_count_condition(operator: str, count_value: int) -> str:
    return f"""
    (
        SELECT COUNT(*)
        FROM lk_central_contacts cc_category
        WHERE cc_category.lead_id = lm.lead_id
          AND cc_category.active_status = 'active'
    ) {operator} {count_value}
    """


def computed_account_category(raw_category: Any, active_contact_count: int, is_customer: Any = None) -> str:
    if to_int(is_customer) and int(is_customer) > 0:
        return "Customer"

    category = str(raw_category or "").strip().lower()

    if category == "lead":
        if active_contact_count > 0:
            return "Lead"
        return "Potential Lead"

    if category in ["suspect", "potential_lead", "potential lead"]:
        return "Potential Lead"

    return category[:1].upper() + category[1:] if category else ""


def normalize_account_category_values(values: List[str]) -> List[str]:
    normalized = []

    for value in values:
        clean = str(value or "").strip().lower()

        if clean in ["customer"]:
            normalized.append("customer")
        elif clean in ["lead"]:
            normalized.append("lead")
        elif clean in ["potential lead", "potential_lead", "potential", "suspect"]:
            normalized.append("potential_lead")

    return normalized


def account_category_condition(category: str) -> Optional[str]:
    category = str(category or "").strip().lower()

    if category == "customer":
        return f"({customer_exists_condition()})"

    if category == "lead":
        return f"""
        (
            {customer_not_exists_condition()}
            AND lm.lead_category = 'lead'
            AND {active_contact_count_condition('>', 0)}
        )
        """

    if category == "potential_lead":
        return f"""
        (
            {customer_not_exists_condition()}
            AND (
                lm.lead_category = 'suspect'
                OR (
                    lm.lead_category = 'lead'
                    AND {active_contact_count_condition('=', 0)}
                )
            )
        )
        """

    return None


def build_computed_account_category_condition(
    computed_category: str,
    where_clauses: List[str],
) -> None:
    values = normalize_account_category_values(split_search_values(computed_category))

    if not values or str(computed_category or "all").strip().lower() == "all":
        return

    clauses = []

    for value in values:
        clause = account_category_condition(value)
        if clause:
            clauses.append(clause)

    if clauses:
        where_clauses.append("(" + " OR ".join(clauses) + ")")


def build_publish_status_condition(
    account_publish_status: str,
    where_clauses: List[str],
) -> None:
    status_value = str(account_publish_status or "active").strip().lower()

    if status_value == "all":
        return

    if status_value in ["archive", "archived"]:
        where_clauses.append("lm.active_status = 'archived'")
        return

    if status_value == "deleted":
        where_clauses.append("lm.active_status = 'deleted'")
        return

    where_clauses.append("lm.active_status = 'active'")


def build_in_condition(column: str, values: List[Any], where_clauses: List[str], params: List[Any]) -> None:
    if not values:
        return

    where_clauses.append(f"{column} IN ({make_placeholders(values)})")
    params.extend(values)


def normalize_account_segment_values(values: List[str]) -> List[str]:
    normalized = []

    for value in values:
        clean = value.strip().lower()

        if clean in ["company", "lk_company_master"]:
            normalized.append("company")
        elif clean in ["contact", "lk_central_contacts"]:
            normalized.append("contact")

    return normalized


def append_assigned_user_condition(where_clauses: List[str], params: List[Any], values: List[str]) -> None:
    numeric_values = []

    for value in values:
        parsed = to_int(value)
        if parsed is not None:
            numeric_values.append(parsed)

    if not numeric_values:
        return

    where_clauses.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_lead_assign la_filter
            WHERE la_filter.lead_id = lm.lead_id
              AND la_filter.user_id IN ({make_placeholders(numeric_values)})
        )
        """
    )
    params.extend(numeric_values)


def append_product_filter(where_clauses: List[str], params: List[Any], field_name: str, values: List[str]) -> None:
    if not values:
        return

    if field_name == "product_name":
        clauses = []
        for value in values:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_lead_product lp_filter
                    WHERE lp_filter.lead_id = lm.lead_id
                      AND lp_filter.product_name LIKE %s
                )
                """
            )
            params.append(f"%{value}%")

        where_clauses.append("(" + " OR ".join(clauses) + ")")
        return

    column_map = {
        "product_id": "lp_filter.product_category_id",
        "product_category_id": "lp_filter.product_category_id",
        "page_id": "lp_filter.page_id",
    }
    column = column_map.get(field_name)

    if not column:
        return

    ids = []
    for value in values:
        parsed = to_int(value)
        if parsed is not None:
            ids.append(parsed)

    if not ids:
        return

    where_clauses.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_lead_product lp_filter
            WHERE lp_filter.lead_id = lm.lead_id
              AND {column} IN ({make_placeholders(ids)})
        )
        """
    )
    params.extend(ids)




def boolean_filter_enabled(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in ["1", "true", "yes", "y", "on"]


def account_has_contacts_condition() -> str:
    return active_contact_count_condition(">", 0)


def account_has_activity_condition(activity_type: Optional[str] = None) -> str:
    type_filter = ""

    if activity_type == "note":
        type_filter = "AND LOWER(las_filter.activity_type) = 'note'"
    elif activity_type == "attachment":
        type_filter = "AND LOWER(las_filter.activity_type) = 'attachment'"
    elif activity_type == "activity":
        type_filter = "AND LOWER(las_filter.activity_type) NOT IN ('note', 'attachment')"

    return f"""
    EXISTS (
        SELECT 1
        FROM lk_activity_leads lal_filter
        INNER JOIN lk_activity_schedule las_filter
            ON las_filter.activity_id = lal_filter.activity_id
        WHERE lal_filter.lead_id = lm.lead_id
          AND (las_filter.active_status IS NULL OR las_filter.active_status <> 'deleted')
          {type_filter}
    )
    """


def append_assigned_by_condition(where_clauses: List[str], params: List[Any], values: List[str]) -> None:
    numeric_values = []

    for value in values:
        parsed = to_int(value)
        if parsed is not None:
            numeric_values.append(parsed)

    if not numeric_values:
        return

    where_clauses.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_lead_assign la_filter
            WHERE la_filter.lead_id = lm.lead_id
              AND la_filter.assign_by IN ({make_placeholders(numeric_values)})
        )
        """
    )
    params.extend(numeric_values)


def append_assigned_user_search_condition(where_clauses: List[str], params: List[Any], values: List[str], search_assign_by: bool = False) -> None:
    if not values:
        return

    table_name = get_master_user_table()
    user_column = "la_filter.assign_by" if search_assign_by else "la_filter.user_id"
    clauses = []

    for value in values:
        like_value = f"%{value}%"
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM lk_lead_assign la_filter
                INNER JOIN {table_name} user_filter
                    ON user_filter.id = {user_column}
                WHERE la_filter.lead_id = lm.lead_id
                  AND (
                        user_filter.name LIKE %s
                        OR user_filter.full_name LIKE %s
                        OR CONCAT_WS(' ', user_filter.first_name, user_filter.middle_name, user_filter.last_name) LIKE %s
                        OR user_filter.first_name LIKE %s
                        OR user_filter.last_name LIKE %s
                        OR user_filter.username LIKE %s
                        OR user_filter.email LIKE %s
                        OR user_filter.user_email LIKE %s
                  )
            )
            """
        )
        params.extend([like_value] * 8)

    where_clauses.append("(" + " OR ".join(clauses) + ")")

def append_named_account_filter(where_clauses: List[str], params: List[Any], field: str, operator: str, value: Any) -> None:
    field = str(field or "").strip().lower()
    operator = str(operator or "eq").strip().lower()
    values = split_search_values(value)

    if not field or not values:
        return

    if field == "is_lead":
        if boolean_filter_enabled(values[0]):
            clause = account_category_condition("lead")
            if clause:
                where_clauses.append(clause)
        return

    if field in ["has_contacts", "with_contacts", "account_with_contacts"]:
        if boolean_filter_enabled(values[0]):
            where_clauses.append(account_has_contacts_condition())
        return

    if field in ["has_notes", "with_notes", "account_with_notes"]:
        if boolean_filter_enabled(values[0]):
            where_clauses.append(account_has_activity_condition("note"))
        return

    if field in ["has_attachments", "with_attachments", "account_with_attachments"]:
        if boolean_filter_enabled(values[0]):
            where_clauses.append(account_has_activity_condition("attachment"))
        return

    if field in ["has_activities", "with_activities", "account_with_activities"]:
        if boolean_filter_enabled(values[0]):
            where_clauses.append(account_has_activity_condition("activity"))
        return

    if field in ["account_category", "lead_category"]:
        normalized = normalize_account_category_values(values)
        clauses = []
        for item in normalized:
            clause = account_category_condition(item)
            if clause:
                clauses.append(clause)
        if clauses:
            where_clauses.append("(" + " OR ".join(clauses) + ")")
        return

    if field in ["account_segment", "lead_segment"]:
        normalized = normalize_account_segment_values(values)
        build_in_condition("lm.lead_segment", normalized, where_clauses, params)
        return

    if field in ["assigned_to", "assigned_user", "assigned_user_id"]:
        append_assigned_user_condition(where_clauses, params, values)
        return

    if field == "assigned_by":
        append_assigned_by_condition(where_clauses, params, values)
        return

    if field in ["assigned_user_search", "assigned_user_name", "assigned_user_email"]:
        append_assigned_user_search_condition(where_clauses, params, values, search_assign_by=False)
        return

    if field == "assigned_by_search":
        append_assigned_user_search_condition(where_clauses, params, values, search_assign_by=True)
        return

    if field in ["product_name", "product_id", "product_category_id", "page_id"]:
        append_product_filter(where_clauses, params, field, values)
        return

    column = ALLOWED_FILTER_FIELDS.get(field)

    if not column or column in [
        "computed_account_category",
        "assigned_to",
        "is_lead",
        "has_contacts",
        "has_notes",
        "has_attachments",
        "has_activities",
        "assigned_user_search",
        "assigned_by",
        "assigned_by_search",
        "product_name",
        "product_id",
        "product_category_id",
        "page_id",
    ]:
        return

    # Date/range operators.
    if operator in ["from", "gte", ">="]:
        where_clauses.append(f"{column} >= %s")
        params.append(values[0])
        return

    if operator in ["to", "lte", "<="]:
        where_clauses.append(f"{column} <= %s")
        params.append(values[0])
        return

    if operator in ["neq", "!=", "not"]:
        where_clauses.append(f"{column} <> %s")
        params.append(values[0])
        return

    if operator == "in" or len(values) > 1:
        build_in_condition(column, values, where_clauses, params)
        return

    if operator in ["like", "starts_with", "ends_with"]:
        if operator == "starts_with":
            params.append(f"{values[0]}%")
        elif operator == "ends_with":
            params.append(f"%{values[0]}")
        else:
            params.append(f"%{values[0]}%")
        where_clauses.append(f"{column} LIKE %s")
        return

    where_clauses.append(f"{column} = %s")
    params.append(values[0])


def build_dynamic_filters(filters: Optional[List[Dict[str, Any]]]) -> Tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []

    if not filters:
        return where_clauses, params

    for item in filters:
        if not isinstance(item, dict):
            continue

        field = str(item.get("field") or "").strip()
        operator = str(item.get("operator") or "eq").strip().lower()
        value = item.get("value")

        if field not in ALLOWED_FILTER_FIELDS:
            continue

        append_named_account_filter(where_clauses, params, field, operator, value)

    return where_clauses, params


def build_account_specific_search_condition(
    search: Optional[str],
    search_by: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not search or not search_by:
        return

    search_by_value = str(search_by or "").strip().lower()

    if search_by_value not in ACCOUNT_SEARCH_FIELDS:
        return

    values = split_search_values(search)

    if not values:
        return

    if search_by_value in ["account_name", "lead_name"]:
        where_clauses.append("lm.lead_name LIKE %s")
        params.append(f"%{values[0]}%")
        return

    if search_by_value in ["account_segment", "lead_segment"]:
        normalized = normalize_account_segment_values(values)
        build_in_condition("lm.lead_segment", normalized, where_clauses, params)
        return

    if search_by_value in ["account_category", "lead_category"]:
        append_named_account_filter(where_clauses, params, search_by_value, "in", values)
        return

    if search_by_value == "employee_count":
        where_clauses.append(
            """
            (
                lm.employee_lower_range LIKE %s
                OR lm.employee_upper_range LIKE %s
            )
            """
        )
        params.extend([f"%{values[0]}%", f"%{values[0]}%"])
        return

    if search_by_value in ["assigned_to", "assigned_user", "assigned_user_id"]:
        append_assigned_user_condition(where_clauses, params, values)
        return

    if search_by_value == "assigned_by":
        append_assigned_by_condition(where_clauses, params, values)
        return

    if search_by_value in ["assigned_user_search", "assigned_user_name", "assigned_user_email"]:
        append_assigned_user_search_condition(where_clauses, params, values, search_assign_by=False)
        return

    if search_by_value == "assigned_by_search":
        append_assigned_user_search_condition(where_clauses, params, values, search_assign_by=True)
        return

    if search_by_value == "product_name":
        append_product_filter(where_clauses, params, "product_name", values)
        return

    column = ACCOUNT_SEARCH_FIELDS[search_by_value]

    if search_by_value in MULTI_VALUE_ACCOUNT_SEARCH_FIELDS:
        build_in_condition(column, values, where_clauses, params)
        return

    if search_by_value in [
        "website",
        "email",
        "phone",
        "industry",
        "address",
        "city",
        "state",
        "country",
        "zipcode",
        "account_source",
        "lead_source",
        "account_status_name",
        "lead_status_name",
    ]:
        where_clauses.append(f"{column} LIKE %s")
        params.append(f"%{values[0]}%")
        return

    where_clauses.append(f"{column} = %s")
    params.append(values[0])


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    account_publish_status: str = "active",
    computed_account_category_value: str = "all",
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Any]]:
    where_clauses = ["lm.status = 'published'"]
    params: List[Any] = []

    build_publish_status_condition(account_publish_status, where_clauses)
    build_computed_account_category_condition(computed_account_category_value, where_clauses)

    if search and search_by:
        build_account_specific_search_condition(search, search_by, where_clauses, params)
    elif search:
        where_clauses.append(
            """
            (
                lm.lead_name LIKE %s
                OR lm.website LIKE %s
                OR lm.email LIKE %s
                OR lm.phone LIKE %s
                OR lm.industry LIKE %s
                OR lm.address LIKE %s
                OR lm.city LIKE %s
                OR lm.state LIKE %s
                OR lm.country LIKE %s
                OR lm.lead_source LIKE %s
                OR EXISTS (
                    SELECT 1
                    FROM lk_lead_assign la_search
                    INNER JOIN logiklu0_leadactuator.zp_users user_search
                        ON user_search.id = la_search.user_id
                    WHERE la_search.lead_id = lm.lead_id
                      AND (
                            user_search.name LIKE %s
                            OR user_search.full_name LIKE %s
                            OR CONCAT_WS(' ', user_search.first_name, user_search.middle_name, user_search.last_name) LIKE %s
                            OR user_search.first_name LIKE %s
                            OR user_search.last_name LIKE %s
                            OR user_search.username LIKE %s
                            OR user_search.email LIKE %s
                            OR user_search.user_email LIKE %s
                      )
                )
                OR EXISTS (
                    SELECT 1
                    FROM lk_lead_product lp_search
                    WHERE lp_search.lead_id = lm.lead_id
                      AND lp_search.product_name LIKE %s
                )
            )
            """
        )
        search_value = f"%{search}%"
        params.extend([search_value] * 19)

    dynamic_where, dynamic_params = build_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    return " AND ".join(where_clauses), params


# -----------------------------
# Related data fetchers/builders
# -----------------------------

def normalize_contact_row(row: Dict[str, Any], user_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    social_network = parse_json_value(row.get("social_network"))
    source_details = parse_json_value(row.get("source_details"))

    if not isinstance(social_network, dict):
        social_network = {}

    if not isinstance(source_details, dict):
        source_details = {}

    return {
        "contact_id": row.get("contact_id"),
        "name": f"{str(row.get('first_name') or '').strip()} {str(row.get('last_name') or '').strip()}".strip(),
        "email": row.get("email"),
        "phone": format_phone(row.get("primary_phone")),
        "whatsapp": format_phone(row.get("whatsappno")),
        "alternative_phone": format_phone(row.get("alternative_phone")),
        "alternative_emails": row.get("alternative_emails"),
        "social_network": social_network,
        "location": {
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "country": row.get("country"),
            "zipcode": row.get("zipcode"),
        },
        "avatar": row.get("avater_url"),
        "department": row.get("department"),
        "designation": row.get("designation"),
        "source": source_label(row.get("source")),
        "source_details": source_details,
        "owner": get_user(user_map, row.get("owner")),
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date"), row.get("timezone")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date"), row.get("timezone")),
        "notes": row.get("notes"),
    }


def fetch_contacts_for_accounts(connection: Any, account_ids: List[int]) -> Tuple[Dict[int, List[Dict[str, Any]]], List[Any]]:
    if not account_ids:
        return {}, []

    sql = f"""
        SELECT
            cc.contact_id,
            cc.lead_id,
            cc.first_name,
            cc.last_name,
            cc.email,
            cc.primary_phone,
            cc.whatsappno,
            cc.alternative_phone,
            cc.alternative_emails,
            cc.social_network,
            cc.address,
            cc.city,
            cc.state,
            cc.country,
            cc.zipcode,
            cc.avater_url,
            cc.department,
            cc.designation,
            cc.source,
            cc.source_details,
            cc.owner,
            cc.created_by,
            cc.created_date,
            cc.modified_by,
            cc.modified_date,
            cc.timezone,
            cc.notes
        FROM lk_central_contacts cc
        WHERE cc.lead_id IN ({make_placeholders(account_ids)})
          AND cc.active_status = 'active'
        ORDER BY cc.lead_id ASC, cc.created_date ASC, cc.contact_id ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, account_ids)
        rows = cursor.fetchall()

    rows_by_account: Dict[int, List[Dict[str, Any]]] = {}
    user_ids: List[Any] = []

    for row in rows:
        account_id = to_int(row.get("lead_id"))

        if account_id is None:
            continue

        rows_by_account.setdefault(account_id, []).append(row)
        user_ids.extend([row.get("owner"), row.get("created_by"), row.get("modified_by")])

    return rows_by_account, user_ids


def fetch_account_dynamic_details(connection: Any, account_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not account_ids:
        return {}

    sql = f"""
        SELECT
            lead_id,
            field_name,
            field_value
        FROM lk_lead_details
        WHERE lead_id IN ({make_placeholders(account_ids)})
          AND field_name IS NOT NULL
          AND field_name <> ''
        ORDER BY lead_id ASC, field_name ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, account_ids)
        rows = cursor.fetchall()

    details: Dict[int, Dict[str, Any]] = {}

    for row in rows:
        account_id = to_int(row.get("lead_id"))
        field_name = row.get("field_name")

        if account_id is None or not field_name:
            continue

        details.setdefault(account_id, {})[field_name] = parse_json_value(row.get("field_value"))

    return details


def fetch_account_products(connection: Any, account_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not account_ids:
        return {}

    sql = f"""
        SELECT
            lp.lead_id,
            lp.product_category_id,
            lp.product_name,
            lp.page_id,
            lp.created_by,
            lp.created_date,
            lp.modified_by,
            lp.modified_date
        FROM lk_lead_product lp
        WHERE lp.lead_id IN ({make_placeholders(account_ids)})
        ORDER BY lp.lead_id ASC, lp.created_date ASC, lp.product_name ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, account_ids)
        rows = cursor.fetchall()

    for row in rows:
        account_id = to_int(row.get("lead_id"))

        if account_id is None:
            continue

        output.setdefault(account_id, []).append(
            {
                "id": row.get("product_category_id"),
                "name": row.get("product_name"),
                "page_id": row.get("page_id"),
                "created_date": format_datetime(row.get("created_date")),
                "modified_date": format_datetime(row.get("modified_date")),
            }
        )

    return output


def fetch_account_assignments(connection: Any, account_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not account_ids:
        return {}

    sql = f"""
        SELECT
            la.lead_id,
            la.group_id,
            la.user_id,
            la.assign_by,
            la.assign_date,
            la.visible,
            la.added_by
        FROM lk_lead_assign la
        WHERE la.lead_id IN ({make_placeholders(account_ids)})
        ORDER BY la.lead_id ASC, la.assign_date ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, account_ids)
        rows = cursor.fetchall()

    for row in rows:
        account_id = to_int(row.get("lead_id"))

        if account_id is None:
            continue

        output.setdefault(account_id, []).append(row)

    return output


def build_assigned_users(row: Dict[str, Any], assignments: List[Dict[str, Any]], user_map: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    user_ids = []

    for assignment in assignments:
        user_id = to_int(assignment.get("user_id"))

        if user_id is not None and user_id > 0:
            user_ids.append(user_id)

    if not user_ids:
        owner_id = to_int(row.get("owner"))

        if owner_id is not None and owner_id > 0:
            user_ids.append(owner_id)

    assigned = []
    seen = set()

    for user_id in user_ids:
        if user_id in seen:
            continue

        seen.add(user_id)
        user = get_user(user_map, user_id)

        if user:
            assigned.append(user)

    return assigned


def fetch_account_activity_rows(connection: Any, account_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not account_ids:
        return {}

    # Existing LogiKlu activity mapping table is lk_activity_leads.
    sql = f"""
        SELECT
            lal.lead_id,
            las.activity_id,
            las.activity_type,
            las.activity_name,
            las.activity_description,
            las.startdate,
            las.enddate,
            las.activity_details,
            las.owner,
            las.created_by,
            las.created_date,
            las.modified_by,
            las.modified_date,
            las.status,
            las.active_status
        FROM lk_activity_leads lal
        INNER JOIN lk_activity_schedule las
            ON las.activity_id = lal.activity_id
        WHERE lal.lead_id IN ({make_placeholders(account_ids)})
          AND (las.active_status IS NULL OR las.active_status <> 'deleted')
        ORDER BY lal.lead_id ASC, las.created_date ASC, las.activity_id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, account_ids)
        rows = cursor.fetchall()

    for row in rows:
        account_id = to_int(row.get("lead_id"))

        if account_id is None:
            continue

        output.setdefault(account_id, []).append(row)

    return output


def build_account_activities(raw_activities: List[Dict[str, Any]], user_map: Dict[int, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    notes = []
    attachments = []
    activities = []

    for activity in raw_activities:
        activity_type = str(activity.get("activity_type") or "").strip().lower()
        details = safe_json_decode(activity.get("activity_details"), {})

        if activity_type == "note":
            notes.append(
                {
                    "subject": first_non_empty(details.get("Subject"), details.get("subject"), activity.get("activity_name")),
                    "note": first_non_empty(details.get("Note"), details.get("note")),
                    "created_by": get_user(user_map, activity.get("created_by")),
                    "created_date": format_datetime(activity.get("created_date")),
                    "modified_by": get_user(user_map, activity.get("modified_by")),
                    "modified_date": format_datetime(activity.get("modified_date")),
                }
            )
            continue

        if activity_type == "attachment":
            fullpath = first_non_empty(details.get("fullpath"), details.get("full_path"), details.get("path"))

            attachments.append(
                {
                    "name": activity.get("activity_name"),
                    "originalname": extract_original_filename(first_non_empty(details.get("originalname"), details.get("original_name"))),
                    "attachmentname": first_non_empty(details.get("modifiedname"), details.get("modified_name")),
                    "filetype": first_non_empty(details.get("filetype"), details.get("file_type")),
                    "filesize": to_number(first_non_empty(details.get("filesize"), details.get("file_size"))),
                    "attachment_url": build_attachment_url(fullpath),
                    "created_by": get_user(user_map, activity.get("created_by")),
                    "created_date": format_datetime(activity.get("created_date")),
                    "modified_by": get_user(user_map, activity.get("modified_by")),
                    "modified_date": format_datetime(activity.get("modified_date")),
                }
            )
            continue

        guests = first_non_empty(details.get("guest"), details.get("guests"), [])

        if isinstance(guests, str):
            guests = [guests] if guests.strip() else []

        if not isinstance(guests, list):
            guests = []

        activities.append(
            {
                "activity_id": activity.get("activity_id"),
                "activity_name": activity.get("activity_name"),
                "activity_type": activity.get("activity_type"),
                "startdate": format_datetime(activity.get("startdate")),
                "enddate": format_datetime(activity.get("enddate")),
                "guests": guests,
                "created_by": get_user(user_map, activity.get("created_by")),
                "created_date": format_datetime(activity.get("created_date")),
                "modified_by": get_user(user_map, activity.get("modified_by")),
                "modified_date": format_datetime(activity.get("modified_date")),
            }
        )

    return {
        "notes": notes,
        "attachments": attachments,
        "activities": activities,
    }


def collect_user_ids(
    account_rows: List[Dict[str, Any]],
    contact_rows_by_account: Dict[int, List[Dict[str, Any]]],
    assignments_map: Dict[int, List[Dict[str, Any]]],
    activity_map: Dict[int, List[Dict[str, Any]]],
) -> List[Any]:
    user_ids: List[Any] = []

    for row in account_rows:
        user_ids.extend([row.get("owner"), row.get("created_by"), row.get("modified_by")])

    for contacts in contact_rows_by_account.values():
        for contact in contacts:
            user_ids.extend([contact.get("owner"), contact.get("created_by"), contact.get("modified_by")])

    for assignments in assignments_map.values():
        for assignment in assignments:
            user_ids.extend([assignment.get("user_id"), assignment.get("assign_by")])

    for activities in activity_map.values():
        for activity in activities:
            user_ids.extend([activity.get("owner"), activity.get("created_by"), activity.get("modified_by")])

    return user_ids


def build_account_item(
    row: Dict[str, Any],
    dynamic_fields_map: Dict[int, Dict[str, Any]],
    contact_rows_map: Dict[int, List[Dict[str, Any]]],
    products_map: Dict[int, List[Dict[str, Any]]],
    assignments_map: Dict[int, List[Dict[str, Any]]],
    activity_map: Dict[int, List[Dict[str, Any]]],
    user_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    account_id = int(row.get("account_id"))
    social_network = parse_json_value(row.get("social_network"))
    source_details = parse_json_value(row.get("source_details"))
    active_contact_count = int(row.get("active_contact_count") or 0)
    activity_groups = build_account_activities(activity_map.get(account_id, []), user_map)

    if not isinstance(social_network, dict):
        social_network = {}

    if not isinstance(source_details, dict):
        source_details = {}

    return {
        "account_id": row.get("account_id"),
        "account_name": row.get("account_name"),
        "account_segment": row.get("account_segment"),
        "account_category": computed_account_category(row.get("raw_account_category"), active_contact_count, row.get("is_customer")),
        "contact_count": active_contact_count,
        "account_temparature": row.get("account_type"),
        "account_status": {
            "id": row.get("account_status_id"),
            "name": row.get("account_status_name"),
            "code": row.get("account_status_code"),
        } if row.get("account_status_id") else None,
        "status_change_date": format_datetime(row.get("status_change_date"), row.get("timezone")),
        "website": row.get("website"),
        "email": row.get("email"),
        "phone": format_phone(row.get("phone")),
        "account_description": row.get("account_description"),
        "employee_count": format_employee_count(row.get("employee_lower_range"), row.get("employee_upper_range")),
        "industry": row.get("industry"),
        "location": {
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "country": row.get("country"),
            "zipcode": row.get("zipcode"),
        },
        "social_network": social_network,
        "previous_crm_used": row.get("crm"),
        "previous_email_marketing_used": row.get("email_marketing"),
        "previous_website_analytics_used": row.get("website_analytics"),
        "owner": get_user(user_map, row.get("owner")),
        "created_by": get_user(user_map, row.get("created_by")),
        "created_date": format_datetime(row.get("created_date"), row.get("timezone")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "modified_date": format_datetime(row.get("modified_date"), row.get("timezone")),
        "assigned": build_assigned_users(row, assignments_map.get(account_id, []), user_map),
        "products": products_map.get(account_id, []),
        "notes": activity_groups.get("notes", []),
        "attachments": activity_groups.get("attachments", []),
        "activities": activity_groups.get("activities", []),
        "source": source_label(row.get("source")),
        "account_source": row.get("account_source"),
        "account_typeevent": row.get("account_typeevent"),
        "account_attendees": row.get("account_attendees"),
        "project_startdate": str(row.get("project_startdate")) if row.get("project_startdate") else None,
        "project_enddate": str(row.get("project_enddate")) if row.get("project_enddate") else None,
        "source_details": source_details,
        "dynamic_fields": dynamic_fields_map.get(account_id, {}),
        "contacts": [
            normalize_contact_row(contact_row, user_map)
            for contact_row in contact_rows_map.get(account_id, [])
        ],
    }


def _legacy_user_from_prefixed_row(row: Dict[str, Any], prefix: str) -> Optional[Dict[str, Any]]:
    user_id = to_int(row.get(prefix) or row.get(f"{prefix}_id"))
    first_name = str(row.get(f"{prefix}_first_name") or "").strip()
    middle_name = str(row.get(f"{prefix}_middle_name") or "").strip()
    last_name = str(row.get(f"{prefix}_last_name") or "").strip()
    full_name = first_non_empty(
        row.get(f"{prefix}_name"),
        " ".join([first_name, middle_name, last_name]).strip(),
    )
    email = first_non_empty(row.get(f"{prefix}_email"), row.get(f"{prefix}_user_email"))

    if user_id is None and not full_name and not email:
        return None

    return {
        "id": user_id,
        "name": full_name,
        "email": email,
    }


def normalize_account_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible account normalizer used by older imports.

    Some modules still import normalize_account_row from accounts_service.
    Keep this function available while returning the new account response naming.
    The full /accounts API uses hydrate_account_rows/build_account_item so it still includes
    assigned, products, notes, attachments, dynamic_fields, and contacts.
    """
    social_network = parse_json_value(row.get("social_network"))
    source_details = parse_json_value(row.get("source_details"))

    if not isinstance(social_network, dict):
        social_network = {}

    if not isinstance(source_details, dict):
        source_details = {}

    active_contact_count = int(row.get("active_contact_count") or row.get("contact_count") or 0)

    return {
        "account_id": row.get("account_id") or row.get("lead_id"),
        "account_name": row.get("account_name") or row.get("lead_name"),
        "account_segment": first_non_empty(row.get("account_segment"), row.get("lead_segment")),
        "account_category": computed_account_category(
            first_non_empty(row.get("raw_account_category"), row.get("account_category"), row.get("lead_category")),
            active_contact_count,
            row.get("is_customer"),
        ),
        "contact_count": active_contact_count,
        "account_temparature": first_non_empty(row.get("account_type"), row.get("lead_type")),
        "account_status": {
            "id": first_non_empty(row.get("account_status_id"), row.get("lead_status_id"), row.get("lead_persuing_status")),
            "name": first_non_empty(row.get("account_status_name"), row.get("lead_status_name")),
            "code": first_non_empty(row.get("account_status_code"), row.get("lead_status_code")),
        } if first_non_empty(row.get("account_status_id"), row.get("lead_status_id"), row.get("lead_persuing_status"), row.get("account_status_name"), row.get("lead_status_name")) else None,
        "status_change_date": format_datetime(row.get("status_change_date"), row.get("timezone")),
        "website": row.get("website"),
        "email": row.get("email"),
        "phone": format_phone(row.get("phone")),
        "account_description": first_non_empty(row.get("account_description"), row.get("lead_description")),
        "employee_count": format_employee_count(row.get("employee_lower_range"), row.get("employee_upper_range")),
        "industry": row.get("industry"),
        "location": {
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "country": row.get("country"),
            "zipcode": row.get("zipcode"),
        },
        "social_network": social_network,
        "previous_crm_used": row.get("crm"),
        "previous_email_marketing_used": row.get("email_marketing"),
        "previous_website_analytics_used": row.get("website_analytics"),
        "owner": _legacy_user_from_prefixed_row(row, "owner"),
        "created_by": _legacy_user_from_prefixed_row(row, "created_by"),
        "created_date": format_datetime(row.get("created_date"), row.get("timezone")),
        "modified_by": _legacy_user_from_prefixed_row(row, "modified_by"),
        "modified_date": format_datetime(row.get("modified_date"), row.get("timezone")),
        "assigned": [],
        "products": [],
        "notes": [],
        "attachments": [],
        "activities": [],
        "source": source_label(row.get("source")),
        "account_source": first_non_empty(row.get("account_source"), row.get("lead_source")),
        "account_typeevent": first_non_empty(row.get("account_typeevent"), row.get("lead_typeevent")),
        "account_attendees": first_non_empty(row.get("account_attendees"), row.get("lead_attendees")),
        "project_startdate": str(row.get("project_startdate")) if row.get("project_startdate") else None,
        "project_enddate": str(row.get("project_enddate")) if row.get("project_enddate") else None,
        "source_details": source_details,
        "dynamic_fields": {},
        "contacts": [],
    }


def hydrate_account_rows(connection: Any, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    account_ids = [int(row.get("account_id")) for row in rows if row.get("account_id") is not None]

    dynamic_fields_map = fetch_account_dynamic_details(connection, account_ids)
    contact_rows_map, _contact_user_ids = fetch_contacts_for_accounts(connection, account_ids)
    products_map = fetch_account_products(connection, account_ids)
    assignments_map = fetch_account_assignments(connection, account_ids)
    activity_map = fetch_account_activity_rows(connection, account_ids)
    user_map = fetch_users(connection, collect_user_ids(rows, contact_rows_map, assignments_map, activity_map))

    return [
        build_account_item(
            row=row,
            dynamic_fields_map=dynamic_fields_map,
            contact_rows_map=contact_rows_map,
            products_map=products_map,
            assignments_map=assignments_map,
            activity_map=activity_map,
            user_map=user_map,
        )
        for row in rows
    ]


# -----------------------------
# Public service functions
# -----------------------------

def base_accounts_select_sql(where_sql: str) -> str:
    return f"""
        SELECT
            lm.lead_id AS account_id,
            lm.lead_name AS account_name,
            lm.lead_segment AS account_segment,
            lm.lead_category AS raw_account_category,
            CASE WHEN cm.customer_id IS NULL THEN 0 ELSE 1 END AS is_customer,
            (
                SELECT COUNT(*)
                FROM lk_central_contacts cc_count
                WHERE cc_count.lead_id = lm.lead_id
                  AND cc_count.active_status = 'active'
            ) AS active_contact_count,
            lm.lead_type AS account_type,
            lm.lead_persuing_status AS account_status_id,
            lsm.lead_status_name AS account_status_name,
            lsm.lead_status_code AS account_status_code,
            lm.status_change_date,
            lm.website,
            lm.email,
            lm.phone,
            lm.lead_description AS account_description,
            lm.employee_lower_range,
            lm.employee_upper_range,
            lm.industry,
            lm.address,
            lm.city,
            lm.state,
            lm.country,
            lm.zipcode,
            lm.social_network,
            lm.crm,
            lm.email_marketing,
            lm.website_analytics,
            lm.owner,
            lm.created_by,
            lm.created_date,
            lm.modified_by,
            lm.modified_date,
            lm.timezone,
            lm.source,
            lm.lead_source AS account_source,
            lm.lead_typeevent AS account_typeevent,
            lm.lead_attendees AS account_attendees,
            lm.project_startdate,
            lm.project_enddate,
            lm.source_details
        FROM lk_lead_master lm
        LEFT JOIN lk_lead_status_master lsm
            ON lsm.lead_status_id = lm.lead_persuing_status
           AND lsm.active_status = 'active'
        LEFT JOIN lk_customer_master cm
            ON cm.lead_id = lm.lead_id
           AND (cm.active_status IS NULL OR cm.active_status <> 'deleted')
        WHERE {where_sql}
    """


def fetch_accounts(
    client_database: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    account_publish_status: str = "active",
    computed_account_category: str = "all",
    filters: Optional[List[Dict[str, Any]]] = None,
    # Backward-compatible names
    lead_publish_status: Optional[str] = None,
    computed_lead_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    connection = None

    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    resolved_publish_status = lead_publish_status if lead_publish_status is not None else account_publish_status
    resolved_category = computed_lead_category if computed_lead_category is not None else computed_account_category

    where_sql, params = build_where_clause(
        search=search,
        search_by=search_by,
        account_publish_status=resolved_publish_status,
        computed_account_category_value=resolved_category,
        filters=filters,
    )

    try:
        connection = get_client_connection(client_database)

        sql = base_accounts_select_sql(where_sql) + """
            ORDER BY lm.created_date ASC, lm.lead_id ASC
            LIMIT %s OFFSET %s
        """

        query_params = params + [limit, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        return hydrate_account_rows(connection, rows)

    finally:
        if connection:
            connection.close()


def count_accounts(
    client_database: str,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    account_publish_status: str = "active",
    computed_account_category: str = "all",
    filters: Optional[List[Dict[str, Any]]] = None,
    # Backward-compatible names
    lead_publish_status: Optional[str] = None,
    computed_lead_category: Optional[str] = None,
) -> int:
    connection = None

    resolved_publish_status = lead_publish_status if lead_publish_status is not None else account_publish_status
    resolved_category = computed_lead_category if computed_lead_category is not None else computed_account_category

    where_sql, params = build_where_clause(
        search=search,
        search_by=search_by,
        account_publish_status=resolved_publish_status,
        computed_account_category_value=resolved_category,
        filters=filters,
    )

    try:
        connection = get_client_connection(client_database)

        sql = f"""
            SELECT COUNT(DISTINCT lm.lead_id) AS total_records
            FROM lk_lead_master lm
            LEFT JOIN lk_lead_status_master lsm
                ON lsm.lead_status_id = lm.lead_persuing_status
               AND lsm.active_status = 'active'
            LEFT JOIN lk_customer_master cm
                ON cm.lead_id = lm.lead_id
               AND (cm.active_status IS NULL OR cm.active_status <> 'deleted')
            WHERE {where_sql}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        return int(row.get("total_records", 0))

    finally:
        if connection:
            connection.close()


def fetch_account_by_id(client_database: str, account_id: int) -> Optional[Dict[str, Any]]:
    connection = None

    try:
        connection = get_client_connection(client_database)

        where_sql = "lm.lead_id = %s AND lm.status = 'published'"
        sql = base_accounts_select_sql(where_sql) + " LIMIT 1"

        with connection.cursor() as cursor:
            cursor.execute(sql, [account_id])
            row = cursor.fetchone()

        if not row:
            return None

        items = hydrate_account_rows(connection, [row])

        if not items:
            return None

        return items[0]

    finally:
        if connection:
            connection.close()
