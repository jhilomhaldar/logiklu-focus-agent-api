import json
import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_deal.v1"
DEFAULT_MASTER_USER_TABLE = "logiklu0_leadactuator.zp_users"
DEFAULT_ATTACHMENT_BASE_URL = "https://logiklu.com/app/v1/"


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
    """Return contact phone as '+CC number' when stored as JSON."""
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
    """originalname may be a string or an upload-object JSON."""
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

    # Old data may store absolute paths like /var/www/html/app/v1/attachments/...
    marker = "app/v1/"
    if marker in path:
        path = path.split(marker, 1)[1]

    if "attachments/" in path:
        path = path[path.find("attachments/"):]

    base_url = get_attachment_base_url()
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
    ids = []

    for item in split_csv_values(value):
        try:
            ids.append(int(float(item)))
        except Exception:
            pass

    return ids


def unique_ints(values: List[Any]) -> List[int]:
    output = []
    seen = set()

    for value in values:
        int_value = to_int(value)

        if int_value is None or int_value <= 0 or int_value in seen:
            continue

        seen.add(int_value)
        output.append(int_value)

    return output


def get_master_user_table() -> str:
    # Deal user lookup must use the LogiKlu actuator user table.
    return DEFAULT_MASTER_USER_TABLE


def get_attachment_base_url() -> str:
    base_url = str(getattr(settings, "ATTACHMENT_BASE_URL", DEFAULT_ATTACHMENT_BASE_URL) or DEFAULT_ATTACHMENT_BASE_URL).strip()

    if not base_url:
        base_url = DEFAULT_ATTACHMENT_BASE_URL

    return base_url.rstrip("/") + "/"


def make_placeholders(values: List[Any]) -> str:
    return ", ".join(["%s"] * len(values))


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

    placeholders = make_placeholders(tokens)
    where_parts.append(f"{expression} IN ({placeholders})")
    params.extend(tokens)


def append_integer_filter(where_parts: List[str], params: List[Any], expression: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    if len(ids) == 1:
        where_parts.append(f"{expression} = %s")
        params.append(ids[0])
        return

    placeholders = make_placeholders(ids)
    where_parts.append(f"{expression} IN ({placeholders})")
    params.extend(ids)


def append_number_range_filter(
    where_parts: List[str],
    params: List[Any],
    expression: str,
    min_value: Any = None,
    max_value: Any = None,
) -> None:
    if clean_filter_value(min_value) is not None:
        try:
            where_parts.append(f"{expression} >= %s")
            params.append(float(min_value))
        except Exception:
            pass

    if clean_filter_value(max_value) is not None:
        try:
            where_parts.append(f"{expression} <= %s")
            params.append(float(max_value))
        except Exception:
            pass


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


def append_contact_id_filter(where_parts: List[str], params: List[Any], value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    clauses = []

    for contact_id in ids:
        clauses.append("(o.lead_contact_id = %s OR FIND_IN_SET(%s, REPLACE(IFNULL(o.contact_ids, ''), ' ', '')) > 0)")
        params.extend([contact_id, str(contact_id)])

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_assigned_user_filter(where_parts: List[str], params: List[Any], value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    clauses = []

    for user_id in ids:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_opportunity_assign oa_filter
                WHERE oa_filter.opportunity_id = o.opportunity_id
                  AND oa_filter.user_id = %s
            )
            """
        )
        params.append(user_id)

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_assign_by_filter(where_parts: List[str], params: List[Any], value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    clauses = []

    for user_id in ids:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_opportunity_assign oa_filter
                WHERE oa_filter.opportunity_id = o.opportunity_id
                  AND oa_filter.assign_by = %s
            )
            """
        )
        params.append(user_id)

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_product_like_filter(where_parts: List[str], params: List[Any], value: Any) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_opportunity_product op_filter
                WHERE op_filter.opportunity_id = o.opportunity_id
                  AND op_filter.product_name LIKE %s
            )
            """
        )
        params.append(f"%{token}%")

        # Fallback when old product JSON is used but lk_opportunity_product has no row.
        clauses.append("o.products LIKE %s")
        params.append(f"%{token}%")
        clauses.append("o.opportunity_amount LIKE %s")
        params.append(f"%{token}%")

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_product_integer_filter(where_parts: List[str], params: List[Any], field: str, value: Any) -> None:
    ids = split_id_values(value)

    if not ids:
        return

    column_map = {
        "product_category_id": "op_filter.product_category_id",
        "product_id": "op_filter.product_category_id",
        "page_id": "op_filter.page_id",
    }
    column = column_map.get(field)

    if not column:
        return

    clauses = []

    for item_id in ids:
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM lk_opportunity_product op_filter
                WHERE op_filter.opportunity_id = o.opportunity_id
                  AND {column} = %s
            )
            """
        )
        params.append(item_id)

    where_parts.append("(" + " OR ".join(clauses) + ")")


def append_product_number_range_filter(
    where_parts: List[str],
    params: List[Any],
    expression: str,
    min_value: Any = None,
    max_value: Any = None,
) -> None:
    sub_parts = ["op_filter.opportunity_id = o.opportunity_id"]
    sub_params: List[Any] = []

    if clean_filter_value(min_value) is not None:
        try:
            sub_parts.append(f"{expression} >= %s")
            sub_params.append(float(min_value))
        except Exception:
            pass

    if clean_filter_value(max_value) is not None:
        try:
            sub_parts.append(f"{expression} <= %s")
            sub_params.append(float(max_value))
        except Exception:
            pass

    if len(sub_parts) <= 1:
        return

    where_parts.append(
        """
        EXISTS (
            SELECT 1
            FROM lk_opportunity_product op_filter
            WHERE {sub_where}
        )
        """.format(sub_where=" AND ".join(sub_parts))
    )
    params.extend(sub_params)


TEXT_FILTER_MAP = {
    "deal_name": ["o.opportunity_name"],
    "opportunity_name": ["o.opportunity_name"],
    "deal_description": ["o.opportunity_description"],
    "opportunity_description": ["o.opportunity_description"],
    "account_name": ["lm.lead_name"],
    "lead_name": ["lm.lead_name"],
    "note": ["o.note"],
    "competitors": ["o.competitors"],
    "currency": ["o.currency"],
    "country": ["lm.country"],
    "state": ["lm.state"],
    "city": ["lm.city"],
    "lead_type": ["lm.lead_type"],
}

EXACT_INTEGER_FILTER_MAP = {
    "deal_id": "o.opportunity_id",
    "opportunity_id": "o.opportunity_id",
    "account_id": "o.lead_id",
    "lead_id": "o.lead_id",
    "company_id": "o.company_id",
    "customer_id": "o.customer_id",
    "owner": "o.owner",
    "created_by": "o.created_by",
    "modified_by": "o.modified_by",
    "closed_by": "o.closed_by",
    "channel_partner": "o.channel_partner",
    "opportunity_status_id": "o.opportunity_status_id",
    "status_id": "o.opportunity_status_id",
    "next_stage": "o.next_stage",
}

EXACT_TEXT_FILTER_MAP = {
    "status": "o.status",
    "deal_status": "o.oportunity_status",
    "opportunity_status": "o.oportunity_status",
    "oportunity_status": "o.oportunity_status",
    "opportunity_type": "o.opportunity_type",
    "deal_type": "o.opportunity_type",
    "active_status": "o.active_status",
    "is_important": "o.is_important",
    "pre_deal": "o.pre_deal",
    "converted_customer_deal": "o.converted_customer_deal",
    "situational_barometer": "o.situational_barometer",
    "closed_state": "oc.closed_state",
    "closed_currency": "oc.currency",
}

DATE_RANGE_FILTER_MAP = {
    "closing_date": "o.closingdate",
    "closingdate": "o.closingdate",
    "created_date": "o.created_date",
    "modified_date": "o.modified_date",
    "closed_date": "o.closed_date",
    "official_closed_date": "oc.closed_date",
}

NUMBER_RANGE_FILTER_MAP = {
    "revenue": "o.revenue",
    "confidencelevel": "o.confidencelevel",
    "confidence_level": "o.confidencelevel",
    "closed_amount": "oc.opportunity_amount",
}


def append_named_filter(where_parts: List[str], params: List[Any], field_name: str, value: Any) -> None:
    field_name = str(field_name or "").strip().lower()

    if not field_name:
        return

    if field_name in TEXT_FILTER_MAP:
        append_like_filter(where_parts, params, TEXT_FILTER_MAP[field_name], value)
        return

    if field_name in EXACT_INTEGER_FILTER_MAP:
        append_integer_filter(where_parts, params, EXACT_INTEGER_FILTER_MAP[field_name], value)
        return

    if field_name in EXACT_TEXT_FILTER_MAP:
        append_string_exact_filter(where_parts, params, EXACT_TEXT_FILTER_MAP[field_name], value)
        return

    if field_name in ["contact_id", "lead_contact_id"]:
        append_contact_id_filter(where_parts, params, value)
        return

    if field_name in ["assigned_to", "assigned_user_id", "assigned"]:
        append_assigned_user_filter(where_parts, params, value)
        return

    if field_name in ["assign_by", "assigned_by"]:
        append_assign_by_filter(where_parts, params, value)
        return

    if field_name == "product_name":
        append_product_like_filter(where_parts, params, value)
        return

    if field_name in ["product_category_id", "product_id", "page_id"]:
        append_product_integer_filter(where_parts, params, field_name, value)
        return


def append_advanced_filters(where_parts: List[str], params: List[Any], filters: Optional[str] = None) -> None:
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

        if field_name in NUMBER_RANGE_FILTER_MAP:
            expression = NUMBER_RANGE_FILTER_MAP[field_name]

            if operator in ["gte", ">="]:
                append_number_range_filter(where_parts, params, expression, min_value=value)
            elif operator in ["lte", "<="]:
                append_number_range_filter(where_parts, params, expression, max_value=value)
            elif operator in ["gt", ">"]:
                try:
                    where_parts.append(f"{expression} > %s")
                    params.append(float(value))
                except Exception:
                    pass
            elif operator in ["lt", "<"]:
                try:
                    where_parts.append(f"{expression} < %s")
                    params.append(float(value))
                except Exception:
                    pass
            elif operator in ["between", "range"] and isinstance(value, list) and len(value) >= 2:
                append_number_range_filter(where_parts, params, expression, value[0], value[1])
            else:
                append_number_range_filter(where_parts, params, expression, value, value)

            continue

        if field_name in DATE_RANGE_FILTER_MAP:
            expression = DATE_RANGE_FILTER_MAP[field_name]

            if operator in ["from", "gte", ">="]:
                append_date_range_filter(where_parts, params, expression, from_value=value)
            elif operator in ["to", "lte", "<="]:
                append_date_range_filter(where_parts, params, expression, to_value=value)
            elif operator in ["between", "range"] and isinstance(value, list) and len(value) >= 2:
                append_date_range_filter(where_parts, params, expression, value[0], value[1])
            else:
                append_date_range_filter(where_parts, params, expression, value, value)

            continue

        append_named_filter(where_parts, params, field_name, value)


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Any]]:
    where_parts = ["1=1"]
    params: List[Any] = []

    if search:
        if search_by:
            append_named_filter(where_parts, params, search_by, search)
        else:
            search_value = f"%{search.strip()}%"
            where_parts.append(
                """
                (
                    o.opportunity_name LIKE %s
                    OR o.opportunity_description LIKE %s
                    OR o.note LIKE %s
                    OR o.competitors LIKE %s
                    OR o.currency LIKE %s
                    OR o.status LIKE %s
                    OR o.oportunity_status LIKE %s
                    OR o.opportunity_type LIKE %s
                    OR lm.lead_name LIKE %s
                    OR lm.lead_type LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM lk_central_contacts cc_filter
                        WHERE (
                                cc_filter.contact_id = o.lead_contact_id
                                OR FIND_IN_SET(CAST(cc_filter.contact_id AS CHAR), REPLACE(IFNULL(o.contact_ids, ''), ' ', '')) > 0
                              )
                          AND (
                                cc_filter.first_name LIKE %s
                                OR cc_filter.last_name LIKE %s
                                OR CONCAT_WS(' ', cc_filter.first_name, cc_filter.last_name) LIKE %s
                                OR cc_filter.email LIKE %s
                                OR cc_filter.phone LIKE %s
                              )
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM lk_opportunity_product op_filter
                        WHERE op_filter.opportunity_id = o.opportunity_id
                          AND op_filter.product_name LIKE %s
                    )
                    OR o.products LIKE %s
                    OR o.opportunity_amount LIKE %s
                )
                """
            )
            params.extend([search_value] * 18)

    filter_params = filter_params or {}

    for field_name, value in filter_params.items():
        field_name = str(field_name or "").strip().lower()

        if field_name.endswith("_min") or field_name.endswith("_max") or field_name.endswith("_from") or field_name.endswith("_to"):
            continue

        append_named_filter(where_parts, params, field_name, value)

    for field_name, expression in NUMBER_RANGE_FILTER_MAP.items():
        append_number_range_filter(
            where_parts,
            params,
            expression,
            min_value=filter_params.get(f"{field_name}_min"),
            max_value=filter_params.get(f"{field_name}_max"),
        )

    for field_name, expression in DATE_RANGE_FILTER_MAP.items():
        append_date_range_filter(
            where_parts,
            params,
            expression,
            from_value=filter_params.get(f"{field_name}_from"),
            to_value=filter_params.get(f"{field_name}_to"),
        )

    append_product_number_range_filter(
        where_parts,
        params,
        "op_filter.total_amount",
        filter_params.get("product_total_min"),
        filter_params.get("product_total_max"),
    )
    append_product_number_range_filter(
        where_parts,
        params,
        "op_filter.product_base_price",
        filter_params.get("product_base_price_min"),
        filter_params.get("product_base_price_max"),
    )
    append_product_number_range_filter(
        where_parts,
        params,
        "op_filter.qty",
        filter_params.get("qty_min"),
        filter_params.get("qty_max"),
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
        # User lookup must not break the deal API. Return IDs with blank name/email if master table is not accessible.
        return fallback


def get_user(user_map: Dict[int, Dict[str, Any]], user_id: Any) -> Optional[Dict[str, Any]]:
    parsed_id = to_int(user_id)

    if parsed_id is None or parsed_id <= 0:
        return None

    return user_map.get(parsed_id) or {"id": parsed_id, "name": None, "email": None}


def fetch_products(connection: Any, deal_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not deal_ids:
        return {}

    sql = f"""
        SELECT
            op.opportunity_id,
            op.product_category_id,
            op.product_name,
            op.page_id,
            op.product_base_price,
            op.currency,
            op.product_price,
            op.deal_for,
            op.payment_for,
            op.qty,
            op.tax_base_price,
            op.tax_type,
            op.tax_amount,
            op.total_amount
        FROM lk_opportunity_product op
        WHERE op.opportunity_id IN ({make_placeholders(deal_ids)})
        ORDER BY op.opportunity_id ASC, op.product_name ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, deal_ids)
        rows = cursor.fetchall()

    for row in rows:
        deal_id = int(row.get("opportunity_id"))

        output.setdefault(deal_id, []).append(
            {
                "id": row.get("product_category_id"),
                "name": row.get("product_name"),
                "page_id": row.get("page_id"),
                "product_base_price": to_number(row.get("product_base_price")),
                "currency": row.get("currency"),
                "product_price": safe_json_decode(row.get("product_price"), None),
                "deal_for": row.get("deal_for"),
                "payment_for": row.get("payment_for"),
                "qty": to_number(row.get("qty")),
                "tax_base_price": to_number(row.get("tax_base_price")),
                "tax_type": row.get("tax_type"),
                "tax_amount": to_number(row.get("tax_amount")),
                "total_amount": to_number(row.get("total_amount")),
            }
        )

    return output


def build_fallback_products(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    products = safe_json_decode(row.get("products"), [])

    if not isinstance(products, list) or not products:
        opportunity_amount = safe_json_decode(row.get("opportunity_amount"), {})

        if isinstance(opportunity_amount, dict):
            products = opportunity_amount.get("products") or []

    if not isinstance(products, list):
        return []

    output = []

    for product in products:
        if not isinstance(product, dict):
            continue

        output.append(
            {
                "id": product.get("product_category_id") or product.get("id"),
                "name": product.get("product_name") or product.get("name"),
                "page_id": product.get("page_id"),
                "product_base_price": to_number(product.get("product_base_price")),
                "currency": product.get("currency"),
                "product_price": product.get("product_price"),
                "deal_for": product.get("deal_for"),
                "payment_for": product.get("payment_for"),
                "qty": to_number(product.get("qty")),
                "tax_base_price": to_number(product.get("tax_base_price")),
                "tax_type": product.get("tax_type"),
                "tax_amount": to_number(product.get("tax_amount")),
                "total_amount": to_number(product.get("total_amount")),
            }
        )

    return output


def fetch_assignments(connection: Any, deal_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not deal_ids:
        return {}

    sql = f"""
        SELECT
            oa.opportunity_id,
            oa.group_id,
            oa.user_id,
            oa.assign_by,
            oa.assign_date,
            oa.visible
        FROM lk_opportunity_assign oa
        WHERE oa.opportunity_id IN ({make_placeholders(deal_ids)})
        ORDER BY oa.opportunity_id ASC, oa.assign_date ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, deal_ids)
        rows = cursor.fetchall()

    for row in rows:
        deal_id = int(row.get("opportunity_id"))
        output.setdefault(deal_id, []).append(row)

    return output


def fetch_contacts(connection: Any, contact_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    contact_ids = unique_ints(contact_ids)

    if not contact_ids:
        return {}

    try:
        sql = f"""
            SELECT *
            FROM lk_central_contacts cc
            WHERE cc.contact_id IN ({make_placeholders(contact_ids)})
              AND (cc.active_status IS NULL OR cc.active_status <> 'deleted')
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, contact_ids)
            rows = cursor.fetchall()

    except Exception:
        sql = f"""
            SELECT *
            FROM lk_central_contacts cc
            WHERE cc.contact_id IN ({make_placeholders(contact_ids)})
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, contact_ids)
            rows = cursor.fetchall()

    output = {}

    for row in rows:
        contact_id = to_int(row.get("contact_id") or row.get("id"))

        if contact_id is None:
            continue

        name = first_non_empty(
            row.get("name"),
            row.get("full_name"),
            " ".join(
                [
                    str(row.get("first_name") or "").strip(),
                    str(row.get("last_name") or "").strip(),
                ]
            ).strip(),
        )

        output[contact_id] = {
            "contact_id": contact_id,
            "name": name,
            "email": first_non_empty(row.get("email"), row.get("primary_email")),
            "phone": format_contact_phone(
                first_non_empty(row.get("primary_phone"), row.get("phone"), row.get("mobile"))
            ),
        }

    return output


def get_deal_contact_ids(row: Dict[str, Any]) -> List[int]:
    ids = []

    lead_contact_id = to_int(row.get("lead_contact_id"))

    if lead_contact_id is not None:
        ids.append(lead_contact_id)

    ids.extend(split_id_values(row.get("contact_ids")))

    return unique_ints(ids)


def fetch_inputs(connection: Any, deal_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not deal_ids:
        return {}

    sql = f"""
        SELECT
            oi.input_id,
            oi.opportunity_id,
            oi.input_source_id,
            oi.input_value,
            oi.input_additional_value,
            oi.created_by,
            oi.created_date,
            oi.modified_by,
            oi.modified_date,
            oi.input_section,
            sa.id AS source_id,
            sa.title AS source_title,
            sa.color AS source_color
        FROM lk_opportunity_inputs oi
        LEFT JOIN jos_setting_sales_executive_action sa
            ON sa.id = oi.input_source_id
           AND oi.input_source_id IS NOT NULL
           AND oi.input_source_id <> 0
        WHERE oi.opportunity_id IN ({make_placeholders(deal_ids)})
        ORDER BY oi.opportunity_id ASC, oi.created_date ASC, oi.input_id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, deal_ids)
        rows = cursor.fetchall()

    for row in rows:
        deal_id = int(row.get("opportunity_id"))
        output.setdefault(deal_id, []).append(row)

    return output


def fetch_activity_rows(connection: Any, deal_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not deal_ids:
        return {}

    sql = f"""
        SELECT
            lao.opportunity_id,
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
            las.timezone,
            las.status,
            las.active_status
        FROM lk_activity_opportunities lao
        INNER JOIN lk_activity_schedule las
            ON las.activity_id = lao.activity_id
        WHERE lao.opportunity_id IN ({make_placeholders(deal_ids)})
          AND (las.active_status IS NULL OR las.active_status <> 'deleted')
        ORDER BY lao.opportunity_id ASC, las.created_date ASC, las.activity_id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, deal_ids)
        rows = cursor.fetchall()

    for row in rows:
        deal_id = int(row.get("opportunity_id"))
        output.setdefault(deal_id, []).append(row)

    return output


def fetch_revenue_generated(connection: Any, revenue_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    revenue_ids = unique_ints(revenue_ids)

    if not revenue_ids:
        return {}

    sql = f"""
        SELECT *
        FROM lk_revenue_generated rg
        WHERE rg.revenue_generate_id IN ({make_placeholders(revenue_ids)})
        ORDER BY rg.track_date ASC, rg.revenue_generate_id ASC
    """

    output = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, revenue_ids)
        rows = cursor.fetchall()

    for row in rows:
        revenue_id = to_int(row.get("revenue_generate_id"))

        if revenue_id is not None:
            output[revenue_id] = row

    return output


# -----------------------------
# Row builders
# -----------------------------

def build_user_id_list(
    rows: List[Dict[str, Any]],
    assignments_map: Dict[int, List[Dict[str, Any]]],
    inputs_map: Dict[int, List[Dict[str, Any]]],
    activity_map: Dict[int, List[Dict[str, Any]]],
    revenue_map: Dict[int, Dict[str, Any]],
) -> List[Any]:
    user_ids: List[Any] = []

    for row in rows:
        user_ids.extend(
            [
                row.get("owner"),
                row.get("created_by"),
                row.get("modified_by"),
                row.get("closed_by"),
                row.get("closed_summary_closed_by"),
            ]
        )

    for assignments in assignments_map.values():
        for assignment in assignments:
            user_ids.extend([assignment.get("user_id"), assignment.get("assign_by")])

    for inputs in inputs_map.values():
        for item in inputs:
            user_ids.extend([item.get("created_by"), item.get("modified_by")])

    for activities in activity_map.values():
        for activity in activities:
            user_ids.extend([activity.get("owner"), activity.get("created_by"), activity.get("modified_by")])

    for revenue in revenue_map.values():
        user_ids.append(revenue.get("user_id"))

    return user_ids


def build_deal_inputs(raw_inputs: List[Dict[str, Any]], user_map: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    output = []

    for item in raw_inputs:
        source = None

        if item.get("source_id"):
            source = {
                "id": item.get("source_id"),
                "title": item.get("source_title"),
                "color": item.get("source_color"),
            }

        output.append(
            {
                "id": item.get("input_id"),
                "section": item.get("input_section"),
                "source": source,
                "value": safe_json_decode(item.get("input_value"), item.get("input_value")),
                "additional_value": safe_json_decode(item.get("input_additional_value"), item.get("input_additional_value")),
                "created_by": get_user(user_map, item.get("created_by")),
                "created_date": format_datetime(item.get("created_date")),
                "modified_by": get_user(user_map, item.get("modified_by")),
                "modified_date": format_datetime(item.get("modified_date")),
            }
        )

    return output


def build_deal_activities(raw_activities: List[Dict[str, Any]], user_map: Dict[int, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
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
                    "originalname": extract_original_filename(
                        first_non_empty(details.get("originalname"), details.get("original_name"))
                    ),
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


def build_closed_summary(
    row: Dict[str, Any],
    revenue_map: Dict[int, Dict[str, Any]],
    user_map: Dict[int, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    closed_id = row.get("closed_summary_id")

    if not closed_id:
        return None

    revenue_ids = split_id_values(row.get("revenue_generated_ids"))
    revenue_generated = []

    for revenue_id in revenue_ids:
        revenue = revenue_map.get(revenue_id)

        if not revenue:
            continue

        revenue_generated.append(
            {
                "id": revenue.get("revenue_generate_id"),
                "track_date": format_date(revenue.get("track_date")),
                "user": get_user(user_map, revenue.get("user_id")),
                "continent": revenue.get("continent"),
                "country": revenue.get("country"),
                "state": revenue.get("state"),
                "city": revenue.get("city"),
                "product_id": revenue.get("product_id"),
                "currency": revenue.get("currency"),
                "amount": to_number(revenue.get("revenue_amount")),
            }
        )

    return {
        "id": closed_id,
        "account_id": row.get("closed_summary_lead_id"),
        "closed_state": row.get("closed_state"),
        "closed_by": get_user(user_map, row.get("closed_summary_closed_by")),
        "closed_date": format_datetime(row.get("closed_summary_closed_date")),
        "currency": row.get("closed_summary_currency"),
        "amount": to_number(row.get("closed_summary_amount")),
        "continent": row.get("closed_summary_continent"),
        "country": row.get("closed_summary_country"),
        "state": row.get("closed_summary_state"),
        "city": row.get("closed_summary_city"),
        "products": safe_json_decode(row.get("closed_summary_products"), []),
        "revenue_generated": revenue_generated,
    }


def build_assigned_users(
    row: Dict[str, Any],
    assignments: List[Dict[str, Any]],
    user_map: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
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


def build_status_object(row: Dict[str, Any], prefix: str) -> Optional[Dict[str, Any]]:
    status_id = row.get(f"{prefix}_id")

    if not status_id:
        return None

    return {
        "id": status_id,
        "title": row.get(f"{prefix}_title"),
        "color": row.get(f"{prefix}_color"),
    }


def build_deal_item(
    row: Dict[str, Any],
    products_map: Dict[int, List[Dict[str, Any]]],
    assignments_map: Dict[int, List[Dict[str, Any]]],
    contacts_map: Dict[int, Dict[str, Any]],
    inputs_map: Dict[int, List[Dict[str, Any]]],
    activity_map: Dict[int, List[Dict[str, Any]]],
    revenue_map: Dict[int, Dict[str, Any]],
    user_map: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    deal_id = int(row.get("deal_id"))
    products = products_map.get(deal_id, [])

    if not products:
        products = build_fallback_products(row)

    contact_ids = get_deal_contact_ids(row)
    contacts = [contacts_map[contact_id] for contact_id in contact_ids if contact_id in contacts_map]
    activity_groups = build_deal_activities(activity_map.get(deal_id, []), user_map)

    return {
        "deal_id": row.get("deal_id"),
        "deal_name": row.get("deal_name"),
        "deal_description": row.get("deal_description"),
        "deal_temparature": row.get("deal_type"),
        "account": {
            "account_id": row.get("account_id"),
            "name": row.get("account_name"),
            "account_type": row.get("account_lead_type"),
            "location": {
                "city": row.get("account_city"),
                "state": row.get("account_state"),
                "country": row.get("account_country"),
            },
        },
        "contacts": contacts,
        "deal_stage": build_status_object(row, "opportunity_status"),
        "status": row.get("status"),
        "deal_status": row.get("deal_status"),
        "next_stage": build_status_object(row, "next_stage"),
        "revenue": to_number(row.get("revenue")),
        "currency": row.get("currency"),
        "closing_date": format_date(row.get("closing_date")),
        "situational_barometer": row.get("situational_barometer"),
        "confidence_level": to_number(row.get("confidence_level")),
        "competitors": row.get("competitors"),
        "channel_partner": row.get("channel_partner"),
        "note": row.get("note"),
        "owner": get_user(user_map, row.get("owner")),
        "created_by": get_user(user_map, row.get("created_by")),
        "modified_by": get_user(user_map, row.get("modified_by")),
        "assigned": build_assigned_users(row, assignments_map.get(deal_id, []), user_map),
        "products": products,
        "deal_inputs": build_deal_inputs(inputs_map.get(deal_id, []), user_map),
        "notes": activity_groups.get("notes", []),
        "attachments": activity_groups.get("attachments", []),
        "activities": activity_groups.get("activities", []),
        "closed_summary": build_closed_summary(row, revenue_map, user_map),
        "active_status": row.get("active_status"),
        "is_important": row.get("is_important"),
        "pre_deal": row.get("pre_deal"),
        "converted_customer_deal": row.get("converted_customer_deal"),
        "created_date": format_datetime(row.get("created_date")),
        "modified_date": format_datetime(row.get("modified_date")),
    }


def hydrate_deal_rows(connection: Any, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    deal_ids = [int(row.get("deal_id")) for row in rows if row.get("deal_id") is not None]

    products_map = fetch_products(connection, deal_ids)
    assignments_map = fetch_assignments(connection, deal_ids)
    inputs_map = fetch_inputs(connection, deal_ids)
    activity_map = fetch_activity_rows(connection, deal_ids)

    contact_ids: List[int] = []

    for row in rows:
        contact_ids.extend(get_deal_contact_ids(row))

    contacts_map = fetch_contacts(connection, contact_ids)

    revenue_ids: List[int] = []

    for row in rows:
        revenue_ids.extend(split_id_values(row.get("revenue_generated_ids")))

    revenue_map = fetch_revenue_generated(connection, revenue_ids)
    user_ids = build_user_id_list(rows, assignments_map, inputs_map, activity_map, revenue_map)
    user_map = fetch_users(connection, user_ids)

    return [
        build_deal_item(
            row=row,
            products_map=products_map,
            assignments_map=assignments_map,
            contacts_map=contacts_map,
            inputs_map=inputs_map,
            activity_map=activity_map,
            revenue_map=revenue_map,
            user_map=user_map,
        )
        for row in rows
    ]


# -----------------------------
# Public service functions
# -----------------------------

def fetch_deals_list(
    client_database: str,
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
        where_clause, params = build_where_clause(
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

        count_sql = f"""
            SELECT COUNT(DISTINCT o.opportunity_id) AS total_records
            FROM lk_opportunities o
            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = o.lead_id
            LEFT JOIN lk_opportunity_closed oc
                ON oc.opportunity_id = o.opportunity_id
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            count_row = cursor.fetchone()

        total_records = int(count_row.get("total_records") or 0)
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0

        sql = f"""
            SELECT
                o.opportunity_id AS deal_id,
                o.company_id,
                o.lead_contact_id,
                o.customer_id,
                o.lead_id,
                o.contact_ids,
                o.opportunity_name AS deal_name,
                o.opportunity_description AS deal_description,
                o.opportunity_type AS deal_type,
                o.revenue,
                o.currency,
                o.products,
                o.opportunity_amount,
                o.closingdate AS closing_date,
                o.situational_barometer,
                o.confidencelevel AS confidence_level,
                o.competitors,
                o.channel_partner,
                o.note,
                o.owner,
                o.created_by,
                o.created_date,
                o.modified_by,
                o.modified_date,
                o.timezone,
                o.status,
                o.oportunity_status AS deal_status,
                o.visible,
                o.closed_by,
                o.closed_date,
                o.opportunity_closed_status_id,
                o.closed_reason_id,
                o.closed_reason_value,
                o.closed_reason_additial_comment,
                o.active_status,
                o.is_important,
                o.pre_deal,
                o.converted_customer_deal,

                lm.lead_id AS account_id,
                lm.lead_name AS account_name,
                lm.lead_type AS account_lead_type,
                lm.city AS account_city,
                lm.state AS account_state,
                lm.country AS account_country,

                status_action.id AS opportunity_status_id,
                status_action.title AS opportunity_status_title,
                status_action.color AS opportunity_status_color,

                next_stage_action.id AS next_stage_id,
                next_stage_action.title AS next_stage_title,
                next_stage_action.color AS next_stage_color,

                oc.opportunity_closed_id AS closed_summary_id,
                oc.lead_id AS closed_summary_lead_id,
                oc.continent AS closed_summary_continent,
                oc.country AS closed_summary_country,
                oc.state AS closed_summary_state,
                oc.city AS closed_summary_city,
                oc.products AS closed_summary_products,
                oc.currency AS closed_summary_currency,
                oc.opportunity_amount AS closed_summary_amount,
                oc.closed_by AS closed_summary_closed_by,
                oc.closed_date AS closed_summary_closed_date,
                oc.closed_state,
                oc.revenue_generated_ids

            FROM lk_opportunities o
            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = o.lead_id
            LEFT JOIN jos_setting_sales_executive_action status_action
                ON status_action.id = o.opportunity_status_id
               AND status_action.section = 'STATUS'
            LEFT JOIN jos_setting_sales_executive_action next_stage_action
                ON next_stage_action.id = o.next_stage
               AND next_stage_action.section = 'NEXTSTAGE'
            LEFT JOIN lk_opportunity_closed oc
                ON oc.opportunity_id = o.opportunity_id
            WHERE {where_clause}
            ORDER BY o.created_date ASC, o.opportunity_id ASC
            LIMIT %s OFFSET %s
        """

        query_params = params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        items = hydrate_deal_rows(connection, rows)

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


def fetch_deal_detail(client_database: str, deal_id: int) -> Optional[Dict[str, Any]]:
    result = fetch_deals_list(
        client_database=client_database,
        page=1,
        per_page=10,
        filter_params={"deal_id": deal_id},
    )

    items = result.get("items") or []

    if not items:
        return None

    return items[0]
