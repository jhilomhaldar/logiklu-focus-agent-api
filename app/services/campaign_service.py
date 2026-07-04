import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_campaign.v1"


CAMPAIGN_SEARCH_FIELDS = {
    "id": "campaign_id",
    "campaign_id": "campaign_id",
    "campaign_provider_id": "campaign_provider_id",

    "campaign_name": "campaign_name",
    "campaignname": "campaign_name",
    "name": "campaign_name",

    "campaign_subject": "campaign_subject",
    "subject": "campaign_subject",

    "campaign_content": "campaign_content",
    "content": "campaign_content",

    "campaign_sender": "campaign_sender",
    "sender": "campaign_sender",

    "list_id": "list_id",
    "list_name": "list_id",
    "search_by_list_name": "list_id",

    "contact": "contact",
    "search_by_contact": "contact",

    "status": "status",
    "active_status": "active_status",
    "created_by": "created_by",
    "updated_by": "updated_by",
    "created_date": "created_date",
    "created_at": "created_date",
    "updated_date": "updated_date",
    "updated_at": "updated_date",
    "scheduled_date": "scheduled_date",
    "sent_date": "sent_date",

    "total_recipients": "total_recipients",
    "delivered": "delivered",
    "not_opened": "not_opened",
    "opened": "opened",
    "clicked": "clicked",
    "hard_bounced": "hard_bounced",
    "soft_bounced": "soft_bounced",
    "total_bounced": "total_bounced",
    "unsubscribed": "unsubscribed",
}


EXACT_FIELDS = {
    "id",
    "campaign_id",
    "status",
    "active_status",
    "created_by",
    "updated_by",
}


DATE_FIELDS = {
    "created_date": "c.created_at",
    "updated_date": "c.updated_at",
    "scheduled_date": "c.scheduled_date",
}


EVENT_ALIASES = {
    "delivered": "not_opened",

    "open": "opened",
    "opened": "opened",

    "click": "clicked",
    "clicked": "clicked",

    "hard_bounce": "hard_bounced",
    "hard_bounced": "hard_bounced",
    "hardbounce": "hard_bounced",

    "soft_bounce": "soft_bounced",
    "soft_bounced": "soft_bounced",
    "softbounce": "soft_bounced",

    "unsubscribe": "unsubscribed",
    "unsubscribed": "unsubscribed",
}


STAT_FIELD_COLUMNS = {
    "total_recipients": "COALESCE(crs.total_recipients, 0)",
    "delivered": "COALESCE(crs.delivered, 0)",
    "not_opened": "COALESCE(crs.not_opened, 0)",
    "opened": "COALESCE(crs.opened, 0)",
    "clicked": "COALESCE(crs.clicked, 0)",
    "hard_bounced": "COALESCE(crs.hard_bounced, 0)",
    "soft_bounced": "COALESCE(crs.soft_bounced, 0)",
    "total_bounced": "(COALESCE(crs.hard_bounced, 0) + COALESCE(crs.soft_bounced, 0))",
    "unsubscribed": "COALESCE(crs.unsubscribed, 0)",
}


SORT_FIELDS = {
    "campaign_id": "c.campaign_id",
    "campaign_name": "c.campaign_name",
    "campaignname": "c.campaign_name",
    "subject": "c.campaign_subject",
    "campaign_subject": "c.campaign_subject",
    "created_date": "c.created_at",
    "created_at": "c.created_at",
    "sent_date": "COALESCE(c.scheduled_date, c.updated_at)",
    "total_recipients": STAT_FIELD_COLUMNS["total_recipients"],
    "delivered": STAT_FIELD_COLUMNS["delivered"],
    "not_opened": STAT_FIELD_COLUMNS["not_opened"],
    "opened": STAT_FIELD_COLUMNS["opened"],
    "clicked": STAT_FIELD_COLUMNS["clicked"],
    "hard_bounced": STAT_FIELD_COLUMNS["hard_bounced"],
    "soft_bounced": STAT_FIELD_COLUMNS["soft_bounced"],
    "total_bounced": STAT_FIELD_COLUMNS["total_bounced"],
    "unsubscribed": STAT_FIELD_COLUMNS["unsubscribed"],
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


def parse_campaign_sender(value: Any) -> Dict[str, Any]:
    decoded = safe_json_decode(value, None)

    if isinstance(decoded, dict):
        return {
            "name": decoded.get("name", ""),
            "email": decoded.get("email", ""),
        }

    return {
        "name": "",
        "email": str(value or ""),
    }


def calculate_rate(value: Any, total: Any) -> float:
    value_int = to_int(value)
    total_int = to_int(total)

    if total_int <= 0:
        return 0.0

    return round((float(value_int) / float(total_int)) * 100, 2)


def normalize_event_value(value: Any) -> str:
    value_string = str(value or "").strip().lower()
    value_string = value_string.replace("-", "_").replace(" ", "_")

    return EVENT_ALIASES.get(value_string, value_string)


def get_empty_detailed_stat() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "delivered": [],
        "not_opened": [],
        "opened": [],
        "clicked": [],
        "hard_bounced": [],
        "soft_bounced": [],
        "total_bounced": [],
        "unsubscribed": [],
    }


def recipient_key_sql(alias: str = "r") -> str:
    return f"""
        CASE
            WHEN {alias}.contact_id IS NOT NULL AND {alias}.contact_id > 0
                THEN CONCAT('ID:', {alias}.contact_id)

            WHEN {alias}.contact_email IS NOT NULL
                 AND TRIM({alias}.contact_email) <> ''
                THEN CONCAT('EMAIL:', LOWER(TRIM({alias}.contact_email)))

            ELSE NULL
        END
    """


def normalized_event_sql(alias: str = "r") -> str:
    return f"""
        REPLACE(
            REPLACE(
                LOWER(TRIM(IFNULL({alias}.event, ''))),
                '-',
                '_'
            ),
            ' ',
            '_'
        )
    """


def build_campaign_report_summary_subquery() -> str:
    recipient_key = recipient_key_sql("r")
    event_expr = normalized_event_sql("r")

    return f"""
        SELECT
            r.campaign_id,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN (
                    'delivered',
                    'opened',
                    'open',
                    'clicked',
                    'click',
                    'hard_bounce',
                    'hard_bounced',
                    'hardbounce',
                    'soft_bounce',
                    'soft_bounced',
                    'softbounce',
                    'unsubscribed',
                    'unsubscribe'
                )
                    THEN {recipient_key}
            END) AS total_recipients,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('delivered', 'opened', 'open', 'clicked', 'click')
                    THEN {recipient_key}
            END) AS delivered,

            COUNT(DISTINCT CASE
                WHEN {event_expr} = 'delivered'
                    THEN {recipient_key}
            END) AS not_opened,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('opened', 'open')
                    THEN {recipient_key}
            END) AS opened,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('clicked', 'click')
                    THEN {recipient_key}
            END) AS clicked,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('hard_bounce', 'hard_bounced', 'hardbounce')
                    THEN {recipient_key}
            END) AS hard_bounced,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('soft_bounce', 'soft_bounced', 'softbounce')
                    THEN {recipient_key}
            END) AS soft_bounced,

            COUNT(DISTINCT CASE
                WHEN {event_expr} IN ('unsubscribed', 'unsubscribe')
                    THEN {recipient_key}
            END) AS unsubscribed

        FROM lk_emailclient_campaign_report r

        GROUP BY r.campaign_id
    """


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


def apply_numeric_condition(
    column: str,
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
        add_in_condition(column, numeric_values, where_clauses, params)
    elif operator == "neq":
        where_clauses.append(f"{column} <> %s")
        params.append(numeric_values[0])
    elif operator in ["gt", "after"]:
        where_clauses.append(f"{column} > %s")
        params.append(numeric_values[0])
    elif operator in ["gte", "from"]:
        where_clauses.append(f"{column} >= %s")
        params.append(numeric_values[0])
    elif operator in ["lt", "before"]:
        where_clauses.append(f"{column} < %s")
        params.append(numeric_values[0])
    elif operator in ["lte", "to"]:
        where_clauses.append(f"{column} <= %s")
        params.append(numeric_values[0])
    else:
        where_clauses.append(f"{column} = %s")
        params.append(numeric_values[0])


def apply_text_condition(
    column: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    values = split_filter_values(value)

    if not values:
        return

    if operator == "in" or len(values) > 1:
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


def apply_date_condition(
    column: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if operator in ["from", "gte", "after"]:
        normalized = normalize_start_datetime(value)

        if normalized:
            where_clauses.append(f"{column} >= %s")
            params.append(normalized)

        return

    if operator in ["to", "lte", "before"]:
        normalized = normalize_end_datetime(value)

        if normalized:
            where_clauses.append(f"{column} <= %s")
            params.append(normalized)

        return

    if operator == "between" and isinstance(value, list) and len(value) >= 2:
        start_value = normalize_start_datetime(value[0])
        end_value = normalize_end_datetime(value[1])

        if start_value and end_value:
            where_clauses.append(f"{column} BETWEEN %s AND %s")
            params.extend([start_value, end_value])

        return

    normalized = normalize_start_datetime(value)

    if normalized:
        where_clauses.append(f"{column} = %s")
        params.append(normalized)


def build_contact_search_exists_condition(
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    values = split_filter_values(value)

    if not values:
        return

    contact_groups: List[str] = []

    for item in values:
        search_value = str(item or "").strip()

        if not search_value:
            continue

        like_value = f"%{search_value}%"

        contact_groups.append(
            """
            (
                rcs.contact_email LIKE %s
                OR cc.email LIKE %s
                OR cc.first_name LIKE %s
                OR cc.last_name LIKE %s
                OR CONCAT(COALESCE(cc.first_name, ''), ' ', COALESCE(cc.last_name, '')) LIKE %s
                OR cc.primary_phone LIKE %s
                OR cc.whatsappno LIKE %s
            )
            """
        )
        params.extend([like_value] * 7)

    if not contact_groups:
        return

    where_clauses.append(
        f"""
        EXISTS (
            SELECT 1
            FROM lk_emailclient_campaign_report rcs
            LEFT JOIN lk_central_contacts cc
                ON cc.contact_id = rcs.contact_id
            WHERE rcs.campaign_id = c.campaign_id
              AND ({' OR '.join(contact_groups)})
        )
        """
    )


def apply_single_field_condition(
    field: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    field = str(field or "").strip().lower()
    operator = str(operator or "eq").strip().lower()

    mapped_field = CAMPAIGN_SEARCH_FIELDS.get(field)

    if not mapped_field:
        return

    if mapped_field == "campaign_id":
        apply_numeric_condition(
            column="c.campaign_id",
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    if mapped_field in ["created_by", "updated_by"]:
        apply_numeric_condition(
            column=f"c.{mapped_field}",
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    if mapped_field in ["status", "active_status"]:
        apply_text_condition(
            column=f"c.{mapped_field}",
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    if mapped_field in ["created_date", "updated_date", "scheduled_date"]:
        column = DATE_FIELDS.get(mapped_field)

        if column:
            apply_date_condition(
                column=column,
                operator=operator,
                value=value,
                where_clauses=where_clauses,
                params=params,
            )

        return

    if mapped_field == "sent_date":
        apply_date_condition(
            column="COALESCE(c.scheduled_date, c.updated_at)",
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    if mapped_field == "contact":
        build_contact_search_exists_condition(
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    if mapped_field in STAT_FIELD_COLUMNS:
        apply_numeric_condition(
            column=STAT_FIELD_COLUMNS[mapped_field],
            operator=operator,
            value=value,
            where_clauses=where_clauses,
            params=params,
        )
        return

    text_columns = {
        "campaign_provider_id": "c.campaign_provider_id",
        "campaign_name": "c.campaign_name",
        "campaign_subject": "c.campaign_subject",
        "campaign_content": "c.campaign_content",
        "campaign_sender": "c.campaign_sender",
        "list_id": "c.list_id",
    }

    column = text_columns.get(mapped_field)

    if not column:
        return

    apply_text_condition(
        column=column,
        operator=operator,
        value=value,
        where_clauses=where_clauses,
        params=params,
    )


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

    if search_by_value == "searchby":
        search_by_value = ""

    if not search_by_value:
        search_value = f"%{search_value_raw}%"

        where_clauses.append(
            """
            (
                c.campaign_name LIKE %s
                OR c.campaign_subject LIKE %s
                OR c.campaign_content LIKE %s
                OR c.campaign_sender LIKE %s
                OR c.campaign_provider_id LIKE %s
                OR c.list_id LIKE %s
                OR EXISTS (
                    SELECT 1
                    FROM lk_emailclient_campaign_report rcs
                    WHERE rcs.campaign_id = c.campaign_id
                      AND rcs.contact_email LIKE %s
                )
            )
            """
        )

        params.extend([search_value] * 7)
        return

    if search_by_value not in CAMPAIGN_SEARCH_FIELDS:
        return

    apply_single_field_condition(
        field=search_by_value,
        operator="like",
        value=search_value_raw,
        where_clauses=where_clauses,
        params=params,
    )


def build_date_range_condition(
    column: str,
    date_from: Optional[str],
    date_to: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    start_value = normalize_start_datetime(date_from)
    end_value = normalize_end_datetime(date_to)

    if start_value:
        where_clauses.append(f"{column} >= %s")
        params.append(start_value)

    if end_value:
        where_clauses.append(f"{column} <= %s")
        params.append(end_value)


def add_stat_range_condition(
    column: str,
    min_value: Optional[int],
    max_value: Optional[int],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if min_value is not None:
        where_clauses.append(f"{column} >= %s")
        params.append(int(min_value))

    if max_value is not None:
        where_clauses.append(f"{column} <= %s")
        params.append(int(max_value))


def build_stat_range_conditions(
    total_recipients_min: Optional[int] = None,
    total_recipients_max: Optional[int] = None,
    delivered_min: Optional[int] = None,
    delivered_max: Optional[int] = None,
    not_opened_min: Optional[int] = None,
    not_opened_max: Optional[int] = None,
    opened_min: Optional[int] = None,
    opened_max: Optional[int] = None,
    clicked_min: Optional[int] = None,
    clicked_max: Optional[int] = None,
    hard_bounced_min: Optional[int] = None,
    hard_bounced_max: Optional[int] = None,
    soft_bounced_min: Optional[int] = None,
    soft_bounced_max: Optional[int] = None,
    total_bounced_min: Optional[int] = None,
    total_bounced_max: Optional[int] = None,
    unsubscribed_min: Optional[int] = None,
    unsubscribed_max: Optional[int] = None,
) -> Tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []

    add_stat_range_condition(STAT_FIELD_COLUMNS["total_recipients"], total_recipients_min, total_recipients_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["delivered"], delivered_min, delivered_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["not_opened"], not_opened_min, not_opened_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["opened"], opened_min, opened_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["clicked"], clicked_min, clicked_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["hard_bounced"], hard_bounced_min, hard_bounced_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["soft_bounced"], soft_bounced_min, soft_bounced_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["total_bounced"], total_bounced_min, total_bounced_max, where_clauses, params)
    add_stat_range_condition(STAT_FIELD_COLUMNS["unsubscribed"], unsubscribed_min, unsubscribed_max, where_clauses, params)

    return where_clauses, params


def build_order_by_clause(
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
) -> str:
    sort_key = str(sort_by or "").strip().lower()
    order_value = str(sort_order or "asc").strip().lower()

    if order_value not in ["asc", "desc"]:
        order_value = "asc"

    if sort_key.startswith("highest_"):
        sort_key = sort_key.replace("highest_", "", 1)
        order_value = "desc"

    if sort_key == "most_clicked":
        sort_key = "clicked"
        order_value = "desc"

    if sort_key == "most_opened":
        sort_key = "opened"
        order_value = "desc"

    if sort_key == "most_delivered":
        sort_key = "delivered"
        order_value = "desc"

    column = SORT_FIELDS.get(sort_key)

    if not column:
        return "c.created_at ASC, c.campaign_id ASC"

    return f"{column} {order_value.upper()}, c.created_at ASC, c.campaign_id ASC"


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    created_date_from: Optional[str] = None,
    created_date_to: Optional[str] = None,
    sent_date_from: Optional[str] = None,
    sent_date_to: Optional[str] = None,
    total_recipients_min: Optional[int] = None,
    total_recipients_max: Optional[int] = None,
    delivered_min: Optional[int] = None,
    delivered_max: Optional[int] = None,
    not_opened_min: Optional[int] = None,
    not_opened_max: Optional[int] = None,
    opened_min: Optional[int] = None,
    opened_max: Optional[int] = None,
    clicked_min: Optional[int] = None,
    clicked_max: Optional[int] = None,
    hard_bounced_min: Optional[int] = None,
    hard_bounced_max: Optional[int] = None,
    soft_bounced_min: Optional[int] = None,
    soft_bounced_max: Optional[int] = None,
    total_bounced_min: Optional[int] = None,
    total_bounced_max: Optional[int] = None,
    unsubscribed_min: Optional[int] = None,
    unsubscribed_max: Optional[int] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[Any]]:
    where_clauses = [
        "(c.status IS NULL OR c.status <> 'deleted')"
    ]

    params: List[Any] = []

    build_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    build_date_range_condition(
        column="c.created_at",
        date_from=created_date_from,
        date_to=created_date_to,
        where_clauses=where_clauses,
        params=params,
    )

    build_date_range_condition(
        column="COALESCE(c.scheduled_date, c.updated_at)",
        date_from=sent_date_from,
        date_to=sent_date_to,
        where_clauses=where_clauses,
        params=params,
    )

    dynamic_where, dynamic_params = build_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    stat_where, stat_params = build_stat_range_conditions(
        total_recipients_min=total_recipients_min,
        total_recipients_max=total_recipients_max,
        delivered_min=delivered_min,
        delivered_max=delivered_max,
        not_opened_min=not_opened_min,
        not_opened_max=not_opened_max,
        opened_min=opened_min,
        opened_max=opened_max,
        clicked_min=clicked_min,
        clicked_max=clicked_max,
        hard_bounced_min=hard_bounced_min,
        hard_bounced_max=hard_bounced_max,
        soft_bounced_min=soft_bounced_min,
        soft_bounced_max=soft_bounced_max,
        total_bounced_min=total_bounced_min,
        total_bounced_max=total_bounced_max,
        unsubscribed_min=unsubscribed_min,
        unsubscribed_max=unsubscribed_max,
    )
    where_clauses.extend(stat_where)
    params.extend(stat_params)

    return " AND ".join(where_clauses), params


def build_contact_lookup_sql(cursor) -> Tuple[str, str, str]:
    """
    Dynamic contact lookup so the API does not break if contact name columns
    differ between client databases.
    """

    try:
        cursor.execute("SHOW COLUMNS FROM lk_central_contacts")
        rows = cursor.fetchall()
    except Exception:
        return "", "r.contact_email", "r.contact_email"

    columns = set()

    for row in rows:
        if "Field" in row:
            columns.add(row["Field"])

    if "contact_id" not in columns:
        return "", "r.contact_email", "r.contact_email"

    join_sql = "LEFT JOIN lk_central_contacts cc ON cc.contact_id = r.contact_id"

    name_parts = []

    if "full_name" in columns:
        name_parts.append("NULLIF(TRIM(cc.full_name), '')")

    if "name" in columns:
        name_parts.append("NULLIF(TRIM(cc.name), '')")

    if "contact_name" in columns:
        name_parts.append("NULLIF(TRIM(cc.contact_name), '')")

    if "contactname" in columns:
        name_parts.append("NULLIF(TRIM(cc.contactname), '')")

    if "first_name" in columns and "last_name" in columns:
        name_parts.append(
            "NULLIF(TRIM(CONCAT(IFNULL(cc.first_name, ''), ' ', IFNULL(cc.last_name, ''))), '')"
        )

    if "firstname" in columns and "lastname" in columns:
        name_parts.append(
            "NULLIF(TRIM(CONCAT(IFNULL(cc.firstname, ''), ' ', IFNULL(cc.lastname, ''))), '')"
        )

    if len(name_parts) > 0:
        contact_name_expr = "COALESCE(" + ", ".join(name_parts) + ", r.contact_email)"
    else:
        contact_name_expr = "r.contact_email"

    if "email" in columns:
        contact_email_expr = "COALESCE(NULLIF(TRIM(cc.email), ''), r.contact_email)"
    elif "contact_email" in columns:
        contact_email_expr = "COALESCE(NULLIF(TRIM(cc.contact_email), ''), r.contact_email)"
    elif "emailid" in columns:
        contact_email_expr = "COALESCE(NULLIF(TRIM(cc.emailid), ''), r.contact_email)"
    else:
        contact_email_expr = "r.contact_email"

    return join_sql, contact_name_expr, contact_email_expr


def normalize_campaign_row(row: Dict[str, Any]) -> Dict[str, Any]:
    total_recipients = to_int(row.get("total_recipients"))

    delivered = to_int(row.get("delivered"))
    not_opened = to_int(row.get("not_opened"))
    opened = to_int(row.get("opened"))
    clicked = to_int(row.get("clicked"))

    hard_bounced = to_int(row.get("hard_bounced"))
    soft_bounced = to_int(row.get("soft_bounced"))
    total_bounced = hard_bounced + soft_bounced

    unsubscribed = to_int(row.get("unsubscribed"))

    return {
        "campaign_id": row.get("campaign_id"),
        "campaign_provider_id": row.get("campaign_provider_id"),
        "campaign_name": row.get("campaign_name"),
        "campaign_subject": row.get("campaign_subject"),
        "campaign_sender": parse_campaign_sender(row.get("campaign_sender")),
        "created_date": format_datetime(row.get("created_date")),
        "sent_date": format_datetime(row.get("sent_date")),
        "stats": {
            "total_recipients": total_recipients,
            "delivered": delivered,
            "not_opened": not_opened,
            "opened": opened,
            "clicked": clicked,
            "hard_bounced": hard_bounced,
            "soft_bounced": soft_bounced,
            "total_bounced": total_bounced,
            "unsubscribed": unsubscribed,
            "open_rate": calculate_rate(opened, delivered),
            "click_rate": calculate_rate(clicked, delivered),
            "bounce_rate": calculate_rate(total_bounced, total_recipients),
            "unsubscribed_rate": calculate_rate(unsubscribed, total_recipients),
        },
        "detailed_stat": get_empty_detailed_stat(),
    }


def normalize_detailed_stat_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event_name = normalize_event_value(row.get("event_name"))

    allowed_events = {
        "not_opened",
        "opened",
        "clicked",
        "hard_bounced",
        "soft_bounced",
        "unsubscribed",
    }

    if event_name not in allowed_events:
        return None

    contact_id = row.get("contact_id")
    contact_email = row.get("contact_email") or ""

    if contact_id is None and not contact_email:
        return None

    return {
        "campaign_id": row.get("campaign_id"),
        "event_name": event_name,
        "contact": {
            "contact_id": contact_id,
            "name": row.get("contact_name") or "",
            "email": contact_email,
        },
    }


def append_contact_to_detailed_group(
    grouped: Dict[int, Dict[str, List[Dict[str, Any]]]],
    duplicate_tracker: Dict[str, bool],
    campaign_id: int,
    group_name: str,
    contact: Dict[str, Any],
) -> None:
    if campaign_id not in grouped:
        grouped[campaign_id] = get_empty_detailed_stat()

    if group_name not in grouped[campaign_id]:
        return

    contact_id = contact.get("contact_id")
    contact_email = str(contact.get("email") or "").strip().lower()

    duplicate_key = f"{campaign_id}:{group_name}:"

    if contact_id:
        duplicate_key += f"ID:{contact_id}"
    else:
        duplicate_key += f"EMAIL:{contact_email}"

    if duplicate_tracker.get(duplicate_key):
        return

    duplicate_tracker[duplicate_key] = True
    grouped[campaign_id][group_name].append(contact)


def fetch_campaign_detailed_stats(
    client_database: str,
    campaign_ids: List[int],
) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    if not campaign_ids:
        return {}

    connection = None

    try:
        connection = get_client_connection(client_database)

        placeholders = ",".join(["%s"] * len(campaign_ids))
        event_expr = normalized_event_sql("r")

        with connection.cursor() as cursor:
            contact_join_sql, contact_name_expr, contact_email_expr = build_contact_lookup_sql(cursor)

            sql = f"""
                SELECT
                    r.campaign_id,
                    r.contact_id,

                    {event_expr} AS event_name,

                    {contact_name_expr} AS contact_name,
                    {contact_email_expr} AS contact_email

                FROM lk_emailclient_campaign_report r

                {contact_join_sql}

                WHERE r.campaign_id IN ({placeholders})
                  AND {event_expr} IN (
                        'delivered',
                        'opened',
                        'open',
                        'clicked',
                        'click',
                        'hard_bounce',
                        'hard_bounced',
                        'hardbounce',
                        'soft_bounce',
                        'soft_bounced',
                        'softbounce',
                        'unsubscribed',
                        'unsubscribe'
                  )

                ORDER BY
                    r.campaign_id ASC,
                    event_name ASC,
                    contact_name ASC
            """

            cursor.execute(sql, tuple(campaign_ids))
            rows = cursor.fetchall()

        grouped: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        duplicate_tracker: Dict[str, bool] = {}

        for row in rows:
            normalized = normalize_detailed_stat_row(row)

            if not normalized:
                continue

            campaign_id = int(normalized.get("campaign_id") or 0)
            event_name = normalized.get("event_name")
            contact = normalized.get("contact")

            if campaign_id <= 0:
                continue

            # Total delivered users = not_opened + opened + clicked
            if event_name in ["not_opened", "opened", "clicked"]:
                append_contact_to_detailed_group(
                    grouped=grouped,
                    duplicate_tracker=duplicate_tracker,
                    campaign_id=campaign_id,
                    group_name="delivered",
                    contact=contact,
                )

            # Not opened / opened / clicked individual buckets
            if event_name in ["not_opened", "opened", "clicked", "unsubscribed"]:
                append_contact_to_detailed_group(
                    grouped=grouped,
                    duplicate_tracker=duplicate_tracker,
                    campaign_id=campaign_id,
                    group_name=event_name,
                    contact=contact,
                )

            # Bounce individual + total bounce buckets
            if event_name in ["hard_bounced", "soft_bounced"]:
                append_contact_to_detailed_group(
                    grouped=grouped,
                    duplicate_tracker=duplicate_tracker,
                    campaign_id=campaign_id,
                    group_name=event_name,
                    contact=contact,
                )

                append_contact_to_detailed_group(
                    grouped=grouped,
                    duplicate_tracker=duplicate_tracker,
                    campaign_id=campaign_id,
                    group_name="total_bounced",
                    contact=contact,
                )

        return grouped

    finally:
        if connection:
            connection.close()


def select_campaigns_sql(campaign_report_summary_subquery: str, where_clause: str, order_by_clause: str) -> str:
    return f"""
        SELECT
            c.campaign_id,
            c.campaign_provider_id,
            c.campaign_name,
            c.campaign_subject,
            c.campaign_sender,
            c.created_at AS created_date,

            CASE
                WHEN c.status = 'sent'
                    THEN COALESCE(c.scheduled_date, c.updated_at)
                ELSE NULL
            END AS sent_date,

            COALESCE(crs.total_recipients, 0) AS total_recipients,
            COALESCE(crs.delivered, 0) AS delivered,
            COALESCE(crs.not_opened, 0) AS not_opened,
            COALESCE(crs.opened, 0) AS opened,
            COALESCE(crs.clicked, 0) AS clicked,
            COALESCE(crs.hard_bounced, 0) AS hard_bounced,
            COALESCE(crs.soft_bounced, 0) AS soft_bounced,
            COALESCE(crs.unsubscribed, 0) AS unsubscribed

        FROM lk_emailclient_campaign c

        LEFT JOIN (
            {campaign_report_summary_subquery}
        ) crs
            ON crs.campaign_id = c.campaign_id

        WHERE {where_clause}

        ORDER BY {order_by_clause}

        LIMIT %s OFFSET %s
    """


def count_campaigns_sql(campaign_report_summary_subquery: str, where_clause: str) -> str:
    return f"""
        SELECT COUNT(*) AS total_records

        FROM lk_emailclient_campaign c

        LEFT JOIN (
            {campaign_report_summary_subquery}
        ) crs
            ON crs.campaign_id = c.campaign_id

        WHERE {where_clause}
    """


def fetch_campaigns(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    include_details: bool = True,
    created_date_from: Optional[str] = None,
    created_date_to: Optional[str] = None,
    sent_date_from: Optional[str] = None,
    sent_date_to: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    total_recipients_min: Optional[int] = None,
    total_recipients_max: Optional[int] = None,
    delivered_min: Optional[int] = None,
    delivered_max: Optional[int] = None,
    not_opened_min: Optional[int] = None,
    not_opened_max: Optional[int] = None,
    opened_min: Optional[int] = None,
    opened_max: Optional[int] = None,
    clicked_min: Optional[int] = None,
    clicked_max: Optional[int] = None,
    hard_bounced_min: Optional[int] = None,
    hard_bounced_max: Optional[int] = None,
    soft_bounced_min: Optional[int] = None,
    soft_bounced_max: Optional[int] = None,
    total_bounced_min: Optional[int] = None,
    total_bounced_max: Optional[int] = None,
    unsubscribed_min: Optional[int] = None,
    unsubscribed_max: Optional[int] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    connection = None

    page = max(int(page), 1)
    per_page = max(1, min(int(per_page), 100))
    offset = (page - 1) * per_page

    where_clause, where_params = build_where_clause(
        search=search,
        search_by=search_by,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        sent_date_from=sent_date_from,
        sent_date_to=sent_date_to,
        total_recipients_min=total_recipients_min,
        total_recipients_max=total_recipients_max,
        delivered_min=delivered_min,
        delivered_max=delivered_max,
        not_opened_min=not_opened_min,
        not_opened_max=not_opened_max,
        opened_min=opened_min,
        opened_max=opened_max,
        clicked_min=clicked_min,
        clicked_max=clicked_max,
        hard_bounced_min=hard_bounced_min,
        hard_bounced_max=hard_bounced_max,
        soft_bounced_min=soft_bounced_min,
        soft_bounced_max=soft_bounced_max,
        total_bounced_min=total_bounced_min,
        total_bounced_max=total_bounced_max,
        unsubscribed_min=unsubscribed_min,
        unsubscribed_max=unsubscribed_max,
        filters=filters,
    )

    campaign_report_summary_subquery = build_campaign_report_summary_subquery()
    order_by_clause = build_order_by_clause(sort_by=sort_by, sort_order=sort_order)

    try:
        connection = get_client_connection(client_database)

        sql = select_campaigns_sql(
            campaign_report_summary_subquery=campaign_report_summary_subquery,
            where_clause=where_clause,
            order_by_clause=order_by_clause,
        )

        query_params = where_params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(query_params))
            rows = cursor.fetchall()

        campaigns = [normalize_campaign_row(row) for row in rows]

        campaign_ids = [
            int(campaign.get("campaign_id"))
            for campaign in campaigns
            if campaign.get("campaign_id")
        ]

        if include_details:
            detailed_stats = fetch_campaign_detailed_stats(
                client_database=client_database,
                campaign_ids=campaign_ids,
            )

            for campaign in campaigns:
                campaign_id = int(campaign.get("campaign_id") or 0)
                campaign["detailed_stat"] = detailed_stats.get(
                    campaign_id,
                    get_empty_detailed_stat(),
                )

        return campaigns

    finally:
        if connection:
            connection.close()


def count_campaigns(
    client_database: str,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    created_date_from: Optional[str] = None,
    created_date_to: Optional[str] = None,
    sent_date_from: Optional[str] = None,
    sent_date_to: Optional[str] = None,
    total_recipients_min: Optional[int] = None,
    total_recipients_max: Optional[int] = None,
    delivered_min: Optional[int] = None,
    delivered_max: Optional[int] = None,
    not_opened_min: Optional[int] = None,
    not_opened_max: Optional[int] = None,
    opened_min: Optional[int] = None,
    opened_max: Optional[int] = None,
    clicked_min: Optional[int] = None,
    clicked_max: Optional[int] = None,
    hard_bounced_min: Optional[int] = None,
    hard_bounced_max: Optional[int] = None,
    soft_bounced_min: Optional[int] = None,
    soft_bounced_max: Optional[int] = None,
    total_bounced_min: Optional[int] = None,
    total_bounced_max: Optional[int] = None,
    unsubscribed_min: Optional[int] = None,
    unsubscribed_max: Optional[int] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> int:
    connection = None

    where_clause, where_params = build_where_clause(
        search=search,
        search_by=search_by,
        created_date_from=created_date_from,
        created_date_to=created_date_to,
        sent_date_from=sent_date_from,
        sent_date_to=sent_date_to,
        total_recipients_min=total_recipients_min,
        total_recipients_max=total_recipients_max,
        delivered_min=delivered_min,
        delivered_max=delivered_max,
        not_opened_min=not_opened_min,
        not_opened_max=not_opened_max,
        opened_min=opened_min,
        opened_max=opened_max,
        clicked_min=clicked_min,
        clicked_max=clicked_max,
        hard_bounced_min=hard_bounced_min,
        hard_bounced_max=hard_bounced_max,
        soft_bounced_min=soft_bounced_min,
        soft_bounced_max=soft_bounced_max,
        total_bounced_min=total_bounced_min,
        total_bounced_max=total_bounced_max,
        unsubscribed_min=unsubscribed_min,
        unsubscribed_max=unsubscribed_max,
        filters=filters,
    )

    campaign_report_summary_subquery = build_campaign_report_summary_subquery()

    try:
        connection = get_client_connection(client_database)

        sql = count_campaigns_sql(
            campaign_report_summary_subquery=campaign_report_summary_subquery,
            where_clause=where_clause,
        )

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(where_params))
            row = cursor.fetchone()

        return int(row.get("total_records") or 0)

    finally:
        if connection:
            connection.close()


def fetch_campaign_by_id(
    client_database: str,
    campaign_id: int,
    include_details: bool = True,
) -> Optional[Dict[str, Any]]:
    connection = None

    campaign_report_summary_subquery = build_campaign_report_summary_subquery()

    try:
        connection = get_client_connection(client_database)

        sql = f"""
            SELECT
                c.campaign_id,
                c.campaign_provider_id,
                c.campaign_name,
                c.campaign_subject,
                c.campaign_sender,
                c.created_at AS created_date,

                CASE
                    WHEN c.status = 'sent'
                        THEN COALESCE(c.scheduled_date, c.updated_at)
                    ELSE NULL
                END AS sent_date,

                COALESCE(crs.total_recipients, 0) AS total_recipients,
                COALESCE(crs.delivered, 0) AS delivered,
                COALESCE(crs.not_opened, 0) AS not_opened,
                COALESCE(crs.opened, 0) AS opened,
                COALESCE(crs.clicked, 0) AS clicked,
                COALESCE(crs.hard_bounced, 0) AS hard_bounced,
                COALESCE(crs.soft_bounced, 0) AS soft_bounced,
                COALESCE(crs.unsubscribed, 0) AS unsubscribed

            FROM lk_emailclient_campaign c

            LEFT JOIN (
                {campaign_report_summary_subquery}
            ) crs
                ON crs.campaign_id = c.campaign_id

            WHERE c.campaign_id = %s
              AND (c.status IS NULL OR c.status <> 'deleted')

            LIMIT 1
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, tuple([campaign_id]))
            row = cursor.fetchone()

        if not row:
            return None

        campaign = normalize_campaign_row(row)

        if include_details:
            detailed_stats = fetch_campaign_detailed_stats(
                client_database=client_database,
                campaign_ids=[int(campaign_id)],
            )

            campaign["detailed_stat"] = detailed_stats.get(
                int(campaign_id),
                get_empty_detailed_stat(),
            )

        return campaign

    finally:
        if connection:
            connection.close()
