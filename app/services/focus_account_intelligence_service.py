import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


TIMEZONE_NAME = "Asia/Kolkata"
SCHEMA_VERSION = "logiklu_focus_account_intelligence.v1"


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


def parse_datetime_loose(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    value_str = str(value).strip()

    if not value_str:
        return None

    value_str = value_str.replace("Z", "").replace("T", " ")

    known_formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in known_formats:
        try:
            return datetime.strptime(value_str, fmt)
        except Exception:
            pass

    try:
        return datetime.fromisoformat(value_str)
    except Exception:
        return None


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and str(value).strip() != "":
            return value

    return None


def normalize_json_list(value: Any) -> list:
    decoded = safe_json_decode(value, [])

    if isinstance(decoded, list):
        return decoded

    if isinstance(decoded, dict):
        return [decoded]

    return []


def extract_journey_days(journey_json: Any) -> list:
    decoded = safe_json_decode(journey_json, {})

    if isinstance(decoded, dict):
        days = decoded.get("days", [])
        return days if isinstance(days, list) else []

    if isinstance(decoded, list):
        return decoded

    return []


def normalize_first_last_visit(first_visit: Any, last_visit: Any) -> tuple:
    if not first_visit or not last_visit:
        return first_visit, last_visit

    first_dt = parse_datetime_loose(first_visit)
    last_dt = parse_datetime_loose(last_visit)

    if first_dt and last_dt and first_dt > last_dt:
        return last_visit, first_visit

    return first_visit, last_visit


def get_page_url(page: Dict[str, Any]) -> Any:
    return first_non_empty(
        page.get("page_url"),
        page.get("url"),
        page.get("page_link"),
        page.get("link"),
    )


def get_page_title(page: Dict[str, Any]) -> Any:
    return first_non_empty(
        page.get("page_title"),
        page.get("title"),
        page.get("name"),
    )


def get_page_visit_time(page: Dict[str, Any]) -> Any:
    return first_non_empty(
        page.get("visited_at"),
        page.get("visit_at"),
        page.get("visited_datetime"),
        page.get("visit_datetime"),
        page.get("track_datetime"),
        page.get("track_date_time"),
        page.get("created_at"),
        page.get("created_date"),
        page.get("time"),
        page.get("datetime"),
    )


def get_action_type(action: Dict[str, Any]) -> str:
    raw_type = first_non_empty(
        action.get("action_type"),
        action.get("type"),
        action.get("event_type"),
        action.get("event"),
        action.get("label"),
        action.get("name"),
        action.get("action"),
        action.get("title"),
        "",
    )

    return str(raw_type or "").strip().lower().replace("-", "_").replace(" ", "_")


def get_action_time(action: Dict[str, Any]) -> Any:
    return first_non_empty(
        action.get("action_time"),
        action.get("action_at"),
        action.get("created_at"),
        action.get("created_date"),
        action.get("visited_at"),
        action.get("visit_datetime"),
        action.get("track_datetime"),
        action.get("track_date_time"),
        action.get("time"),
        action.get("datetime"),
        action.get("timestamp"),
    )


def classify_action(action: Dict[str, Any]) -> str:
    action_type = get_action_type(action)

    action_text = " ".join(
        [
            str(action.get("label") or ""),
            str(action.get("title") or ""),
            str(action.get("name") or ""),
            str(action.get("summary") or ""),
            str(action.get("description") or ""),
            str(action.get("text") or ""),
            str(action.get("action") or ""),
            str(action.get("action_type") or ""),
            str(action.get("type") or ""),
        ]
    ).lower()

    combined = f"{action_type} {action_text}"

    if "lead_form" in combined or "leadform" in combined or "lead form" in combined:
        return "lead_form_submission"

    if "inner_form" in combined or "innerform" in combined or "inner form" in combined:
        return "inner_form_submission"

    if "external" in combined or "outbound" in combined:
        return "external_link_click"

    if "asset" in combined or "download" in combined or "pdf" in combined:
        return "asset_download"

    if "video" in combined or "youtube" in combined:
        return "video_view"

    if "form" in combined and "submit" in combined:
        return "form_submission"

    if "link" in combined and "click" in combined:
        return "external_link_click"

    return "other"


def get_page_actions(page: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions = page.get("actions", [])

    if isinstance(actions, list):
        return [action for action in actions if isinstance(action, dict)]

    if isinstance(actions, dict):
        return [actions]

    return []



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


def append_like_filter(
    where_parts: List[str],
    params: List[Any],
    expressions: List[str],
    value: Any,
) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        for expression in expressions:
            clauses.append(f"{expression} LIKE %s")
            params.append(f"%{token}%")

    if clauses:
        where_parts.append("(" + " OR ".join(clauses) + ")")


def append_exact_filter(
    where_parts: List[str],
    params: List[Any],
    expression: str,
    value: Any,
) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    if len(tokens) == 1:
        where_parts.append(f"{expression} = %s")
        params.append(tokens[0])
        return

    placeholders = ", ".join(["%s"] * len(tokens))
    where_parts.append(f"{expression} IN ({placeholders})")
    params.extend(tokens)


def append_integer_filter(
    where_parts: List[str],
    params: List[Any],
    expression: str,
    value: Any,
) -> None:
    tokens = split_csv_values(value)
    numbers = []

    for token in tokens:
        try:
            numbers.append(int(token))
        except Exception:
            pass

    if not numbers:
        return

    if len(numbers) == 1:
        where_parts.append(f"{expression} = %s")
        params.append(numbers[0])
        return

    placeholders = ", ".join(["%s"] * len(numbers))
    where_parts.append(f"{expression} IN ({placeholders})")
    params.extend(numbers)


def append_bool_shortlist_filter(
    where_parts: List[str],
    params: List[Any],
    value: Any,
) -> None:
    value = clean_filter_value(value)

    if not value:
        return

    value_lower = value.lower()

    if value_lower in ["1", "true", "yes", "y"]:
        where_parts.append(
            """
            (
                fcl.is_shortlisted = %s
                OR fcl.is_shortlisted = %s
                OR LOWER(CAST(fcl.is_shortlisted AS CHAR)) = %s
                OR LOWER(CAST(fcl.is_shortlisted AS CHAR)) = %s
            )
            """
        )
        params.extend(["Y", "1", "true", "yes"])
        return

    if value_lower in ["0", "false", "no", "n"]:
        where_parts.append(
            """
            (
                fcl.is_shortlisted = %s
                OR fcl.is_shortlisted = %s
                OR fcl.is_shortlisted IS NULL
                OR LOWER(CAST(fcl.is_shortlisted AS CHAR)) = %s
                OR LOWER(CAST(fcl.is_shortlisted AS CHAR)) = %s
            )
            """
        )
        params.extend(["N", "0", "false", "no"])
        return

    where_parts.append("fcl.is_shortlisted = %s")
    params.append(value)


def append_score_range_filter(
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


def append_contact_filter(
    where_parts: List[str],
    params: List[Any],
    value: Any,
    field: str = "any",
) -> None:
    tokens = split_csv_values(value)

    if not tokens:
        return

    clauses = []

    for token in tokens:
        like_value = f"%{token}%"

        if field == "email":
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_central_contacts cc
                    WHERE cc.lead_id = fcl.lead_id
                      AND cc.email LIKE %s
                )
                """
            )
            params.append(like_value)

        elif field == "phone":
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_central_contacts cc
                    WHERE cc.lead_id = fcl.lead_id
                      AND cc.phone LIKE %s
                )
                """
            )
            params.append(like_value)

        elif field == "name":
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_central_contacts cc
                    WHERE cc.lead_id = fcl.lead_id
                      AND (
                            cc.first_name LIKE %s
                            OR cc.last_name LIKE %s
                            OR CONCAT_WS(' ', cc.first_name, cc.last_name) LIKE %s
                      )
                )
                """
            )
            params.extend([like_value, like_value, like_value])

        else:
            clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM lk_central_contacts cc
                    WHERE cc.lead_id = fcl.lead_id
                      AND (
                            cc.first_name LIKE %s
                            OR cc.last_name LIKE %s
                            OR CONCAT_WS(' ', cc.first_name, cc.last_name) LIKE %s
                            OR cc.email LIKE %s
                            OR cc.phone LIKE %s
                      )
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value, like_value])

        # Fallback: contacts are also stored as JSON/text inside journey table.
        clauses.append("fj.contacts LIKE %s")
        params.append(like_value)

    if clauses:
        where_parts.append("(" + " OR ".join(clauses) + ")")


TEXT_FILTER_MAP = {
    "lead_name": ["lm.lead_name", "fcl.visitors_name"],
    "account_name": ["lm.lead_name", "fcl.visitors_name"],
    "company_name": ["lm.lead_name", "fcl.visitors_name"],
    "visitors_name": ["fcl.visitors_name"],
    "website": ["lm.website", "fcl.website"],
    "company_domain": ["lm.website", "fcl.website"],
    "domain": ["lm.website", "fcl.website"],
    "industry": ["lm.industry"],
    "city": ["lm.city", "fcl.city"],
    "state": ["lm.state", "fcl.state"],
    "country": ["lm.country", "fcl.country"],
    "email": ["lm.email"],
    "phone": ["lm.phone"],
    "lead_category": ["lm.lead_category"],
    "lead_type": ["lm.lead_type"],
    "lead_status": ["lm.status"],
    "active_status": ["lm.active_status"],
    "interest_level": ["fcl.interest_category"],
    "interest_category": ["fcl.interest_category"],
    "priority_label": ["fcl.priority_label"],
    "priority_level": ["fcl.priority_label"],
    "engagement_level": ["fcl.engagement_level"],
}

EXACT_FILTER_MAP = {
    "account_id": "fcl.lead_id",
    "lead_id": "fcl.lead_id",
    "company_id": "fcl.lead_id",
    "report_company_log_id": "fcl.report_company_log_id",
    "owner": "lm.owner",
}

SCORE_FILTER_MAP = {
    "activity_score": "fcl.activity_score",
    "depth_score": "fcl.depth_score",
    "sustenance_score": "fcl.sustenance_score",
    "sustainment_score": "fcl.sustenance_score",
    "context_score": "fcl.context_score",
    "contextual_score": "fcl.context_score",
    "conversion_score": "fcl.conversion_score",
    "interest_score": "fcl.interest_score",
    "priority_score": "fcl.priority_score",
    "final_score": "fcl.final_score",
    "total_score": "fcl.final_score",
}


def append_named_filter(
    where_parts: List[str],
    params: List[Any],
    field_name: str,
    value: Any,
) -> None:
    field_name = str(field_name or "").strip().lower()

    if not field_name:
        return

    if field_name in ["contact_email", "contact_emails"]:
        append_contact_filter(where_parts, params, value, "email")
        return

    if field_name in ["contact_name", "contact_names"]:
        append_contact_filter(where_parts, params, value, "name")
        return

    if field_name in ["contact_phone", "contact_mobile"]:
        append_contact_filter(where_parts, params, value, "phone")
        return

    if field_name in ["contact", "contacts"]:
        append_contact_filter(where_parts, params, value, "any")
        return

    if field_name == "is_shortlisted":
        append_bool_shortlist_filter(where_parts, params, value)
        return

    if field_name in EXACT_FILTER_MAP:
        append_integer_filter(where_parts, params, EXACT_FILTER_MAP[field_name], value)
        return

    if field_name in TEXT_FILTER_MAP:
        append_like_filter(where_parts, params, TEXT_FILTER_MAP[field_name], value)
        return

    if field_name in SCORE_FILTER_MAP:
        append_score_range_filter(where_parts, params, SCORE_FILTER_MAP[field_name], value, value)
        return


def append_advanced_filters(
    where_parts: List[str],
    params: List[Any],
    filters: Optional[str] = None,
) -> None:
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

        if field_name in SCORE_FILTER_MAP:
            expression = SCORE_FILTER_MAP[field_name]

            if operator in ["gte", ">="]:
                append_score_range_filter(where_parts, params, expression, min_value=value)
            elif operator in ["lte", "<="]:
                append_score_range_filter(where_parts, params, expression, max_value=value)
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
                append_score_range_filter(where_parts, params, expression, value[0], value[1])
            else:
                append_score_range_filter(where_parts, params, expression, value, value)

            continue

        # For non-score filters, keep field names whitelisted through append_named_filter.
        append_named_filter(where_parts, params, field_name, value)


def build_where_clause(
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
    interest_level: Optional[str] = None,
    priority_label: Optional[str] = None,
    is_shortlisted: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    where_parts = [
        "frm.is_current = 'Y'",
        "frm.report_status = 'active'",
    ]

    params: List[Any] = []

    if search:
        if search_by:
            append_named_filter(where_parts, params, search_by, search)
        else:
            search_value = f"%{search.strip()}%"

            where_parts.append(
                """
                (
                    lm.lead_name LIKE %s
                    OR fcl.visitors_name LIKE %s
                    OR lm.website LIKE %s
                    OR fcl.website LIKE %s
                    OR lm.industry LIKE %s
                    OR lm.city LIKE %s
                    OR lm.state LIKE %s
                    OR lm.country LIKE %s
                    OR lm.email LIKE %s
                    OR lm.phone LIKE %s
                    OR fcl.city LIKE %s
                    OR fcl.state LIKE %s
                    OR fcl.country LIKE %s
                    OR fcl.interest_category LIKE %s
                    OR fcl.priority_label LIKE %s
                    OR fcl.engagement_level LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM lk_central_contacts cc
                        WHERE cc.lead_id = fcl.lead_id
                          AND (
                                cc.first_name LIKE %s
                                OR cc.last_name LIKE %s
                                OR CONCAT_WS(' ', cc.first_name, cc.last_name) LIKE %s
                                OR cc.email LIKE %s
                                OR cc.phone LIKE %s
                          )
                    )
                    OR fj.contacts LIKE %s
                )
                """
            )

            params.extend(
                [
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
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                    search_value,
                ]
            )

    # Backward-compatible parameters already used by the endpoint.
    if interest_level:
        append_named_filter(where_parts, params, "interest_level", interest_level)

    if priority_label:
        append_named_filter(where_parts, params, "priority_label", priority_label)

    if is_shortlisted:
        append_bool_shortlist_filter(where_parts, params, is_shortlisted)

    filter_params = filter_params or {}

    for field_name, value in filter_params.items():
        append_named_filter(where_parts, params, field_name, value)

    for score_name, expression in SCORE_FILTER_MAP.items():
        min_key = f"{score_name}_min"
        max_key = f"{score_name}_max"

        min_value = filter_params.get(min_key)
        max_value = filter_params.get(max_key)

        append_score_range_filter(where_parts, params, expression, min_value, max_value)

    append_advanced_filters(where_parts, params, filters)

    return " AND ".join(where_parts), params



def build_reporting_window(report_row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not report_row:
        return None

    return {
        "report_id": report_row.get("report_id"),
        "report_uid": report_row.get("report_uid"),
        "report_batch_uid": report_row.get("report_batch_uid"),
        "from_date": format_date(report_row.get("dataset_period_start")),
        "to_date": format_date(report_row.get("dataset_period_end")),
        "window_days": int(report_row.get("dataset_period") or 0),
        "report_period": int(report_row.get("report_period") or 0),
        "report_period_label": report_row.get("report_period_label"),
        "timezone": TIMEZONE_NAME,
    }


def fetch_current_focus_report(connection: Any) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            report_id,
            report_uid,
            report_batch_uid,
            dataset_period,
            report_period,
            report_period_label,
            dataset_period_start,
            dataset_period_end,
            track_date,
            created_date
        FROM lk_focus_report_master
        WHERE is_current = 'Y'
          AND report_status = 'active'
        ORDER BY
            track_date DESC,
            report_id DESC
        LIMIT 1
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()



def fetch_focus_account_intelligence_list(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[str] = None,
    filter_params: Optional[Dict[str, Any]] = None,
    interest_level: Optional[str] = None,
    priority_label: Optional[str] = None,
    is_shortlisted: Optional[str] = None,
    include_journey: bool = False,
) -> Dict[str, Any]:
    connection = None

    try:
        page = int(page)
    except Exception:
        page = 1

    try:
        per_page = int(per_page)
    except Exception:
        per_page = 10

    page = max(page, 1)
    per_page = max(per_page, 1)
    offset = (page - 1) * per_page

    try:
        connection = get_client_connection(client_database)

        current_report = fetch_current_focus_report(connection)
        reporting_window = build_reporting_window(current_report)

        if not current_report:
            return {
                "items": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "offset": offset,
                    "record_count": 0,
                    "total_records": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": page > 1,
                },
            }

        where_clause, params = build_where_clause(
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        where_clause = "frm.report_id = %s AND " + where_clause
        params = [int(current_report.get("report_id"))] + params

        count_sql = f"""
            SELECT COUNT(*) AS total_records
            FROM lk_focus_report_master frm

            INNER JOIN lk_focus_report_company_log fcl
                ON fcl.report_id = frm.report_id

            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = fcl.lead_id

            LEFT JOIN lk_focus_report_company_journey fj
                ON fj.report_company_log_id = fcl.report_company_log_id

            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            count_row = cursor.fetchone()

        total_records = int(count_row.get("total_records") or 0)
        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0

        sql = f"""
            SELECT
                frm.report_id,
                frm.report_uid,
                frm.report_batch_uid,
                frm.dataset_period,
                frm.report_period,
                frm.report_period_label,
                frm.dataset_period_start,
                frm.dataset_period_end,

                fcl.report_company_log_id,
                fcl.lead_id,
                fcl.visitors_name,
                fcl.country AS focus_country,
                fcl.state AS focus_state,
                fcl.city AS focus_city,
                fcl.website AS focus_website,
                fcl.track_ids,
                fcl.track_lead_ids,
                fcl.action_taken,
                fcl.last_visit_utc_datetime,

                fcl.activity_score,
                fcl.depth_score,
                fcl.sustenance_score,
                fcl.context_score,
                fcl.conversion_score,
                fcl.interest_score,
                fcl.interest_category,
                fcl.priority_score,
                fcl.priority_label,
                fcl.engagement_level,
                fcl.final_score,

                fcl.is_shortlisted,
                fcl.shortlisted_rank,
                fcl.shortlist_reason,
                fcl.exclusion_reason,

                fcl.score_explanation,
                fcl.final_explanation,
                fcl.explanations_json,
                fcl.top_signal_json,
                fcl.insight_summary,
                fcl.account_summary_short,
                fcl.created_date AS company_score_created_date,

                fj.contacts,
                fj.journey_timeline_json,
                fj.first_visit_date,
                fj.last_visit_date,
                fj.total_visits,
                fj.total_time_spent,

                lm.lead_name,
                lm.website AS lead_website,
                lm.lead_category,
                lm.lead_type,
                lm.status AS lead_status,
                lm.active_status,
                lm.industry,
                lm.country,
                lm.state,
                lm.city,
                lm.email,
                lm.phone,
                lm.owner,
                lm.created_date AS lead_created_date,
                lm.modified_date AS lead_modified_date

            FROM lk_focus_report_master frm

            INNER JOIN lk_focus_report_company_log fcl
                ON fcl.report_id = frm.report_id

            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = fcl.lead_id

            LEFT JOIN lk_focus_report_company_journey fj
                ON fj.report_company_log_id = fcl.report_company_log_id

            WHERE {where_clause}

            ORDER BY
                fcl.final_score DESC,
                fcl.last_visit_utc_datetime DESC,
                fcl.report_company_log_id DESC

            LIMIT %s OFFSET %s
        """

        query_params = params + [per_page, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        items = [
            build_focus_account_intelligence_item(
                row=row,
                reporting_window=reporting_window,
                include_journey=include_journey,
            )
            for row in rows
        ]

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


def build_focus_account_intelligence_item(
    row: Dict[str, Any],
    reporting_window: Optional[Dict[str, Any]] = None,
    include_journey: bool = False,
) -> Dict[str, Any]:
    score_explanation = (
        safe_json_decode(row.get("score_explanation"), {})
        or safe_json_decode(row.get("final_explanation"), {})
        or safe_json_decode(row.get("explanations_json"), {})
        or {}
    )

    journey_days = extract_journey_days(row.get("journey_timeline_json"))

    db_first_visit_date, db_last_visit_date = normalize_first_last_visit(
        row.get("first_visit_date"),
        row.get("last_visit_date"),
    )

    signal_summary = build_signal_summary(
        row=row,
        journey_days=journey_days,
        normalized_first_visit_date=db_first_visit_date,
        normalized_last_visit_date=db_last_visit_date,
    )

    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])
    contacts = safe_json_decode(row.get("contacts"), [])

    first_visit_at = signal_summary.get("first_activity_at") or format_datetime(db_first_visit_date)
    last_visit_at = signal_summary.get("last_activity_at") or format_datetime(db_last_visit_date)

    item = {
        "schema_version": SCHEMA_VERSION,
        "reporting_window": reporting_window or build_reporting_window(row),
        "account": {
            "account_id": row.get("lead_id"),
            "company_id": row.get("lead_id"),
            "report_company_log_id": row.get("report_company_log_id"),
            "company_name": first_non_empty(
                row.get("lead_name"),
                row.get("visitors_name"),
            ),
            "company_domain": first_non_empty(
                row.get("lead_website"),
                row.get("focus_website"),
            ),
            "account_status": first_non_empty(
                row.get("lead_category"),
                row.get("lead_status"),
            ),
            "lead_type": row.get("lead_type"),
            "lead_publish_status": row.get("lead_status"),
            "active_status": row.get("active_status"),
            "is_identified_company": bool(
                row.get("lead_id") and int(row.get("lead_id")) > 0
            ),
            "contact": {
                "email": row.get("email"),
                "phone": row.get("phone"),
            },
            "location": {
                "country": first_non_empty(row.get("country"), row.get("focus_country")),
                "state": first_non_empty(row.get("state"), row.get("focus_state")),
                "city": first_non_empty(row.get("city"), row.get("focus_city")),
            },
            "industry": row.get("industry"),
        },
        "deterministic_scores": {
            "score_components": {
                "activity": to_number(row.get("activity_score")),
                "sustenance": to_number(row.get("sustenance_score")),
                "depth": to_number(row.get("depth_score")),
                "contextual": to_number(row.get("context_score")),
                "conversion": to_number(row.get("conversion_score")),
                "priority": to_number(row.get("priority_score")),
            },
            "interest_score": to_number(row.get("interest_score")),
            "interest_level": row.get("interest_category"),
            "priority_label": row.get("priority_label"),
            "engagement_level": row.get("engagement_level"),
            "final_score": to_number(row.get("final_score")),
            "computed_at": format_datetime(row.get("company_score_created_date")),
        },
        "score_explanation": score_explanation,
        "signal_summary": signal_summary,
        "top_evidence_facts": build_top_evidence_facts(row, signal_summary),
        "focus_status": {
            "is_shortlisted": row.get("is_shortlisted"),
            "shortlisted_rank": row.get("shortlisted_rank"),
            "shortlist_reason": row.get("shortlist_reason"),
            "exclusion_reason": row.get("exclusion_reason"),
        },
        "focus_summary": {
            "insight_summary": row.get("insight_summary"),
            "account_summary_short": row.get("account_summary_short"),
            "last_visit_utc_datetime": format_datetime(row.get("last_visit_utc_datetime")),
        },
        "campaign_contact_attribution": {
            "track_ids": track_ids if isinstance(track_ids, list) else [],
            "track_lead_ids": track_lead_ids if isinstance(track_lead_ids, list) else [],
        },
    }

    if include_journey:
        item["journey_detail"] = {
            "first_visit_date": first_visit_at,
            "first_visit_at": first_visit_at,
            "last_visit_date": last_visit_at,
            "last_visit_at": last_visit_at,
            "total_visits": signal_summary.get("session_count") or int(row.get("total_visits") or 0),
            "total_time_spent_seconds": signal_summary.get("total_time_spent_seconds") or int(row.get("total_time_spent") or 0),
            "days": journey_days,
        }

        item["campaign_contact_attribution"]["contacts"] = (
            contacts if isinstance(contacts, list) else []
        )

    return item


def build_signal_summary(
    row: Dict[str, Any],
    journey_days: list,
    normalized_first_visit_date: Any = None,
    normalized_last_visit_date: Any = None,
) -> Dict[str, Any]:
    action_taken = safe_json_decode(row.get("action_taken"), {})

    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])

    session_count = 0
    page_view_count = 0
    total_action_count = 0

    asset_download_count = 0
    external_link_click_count = 0
    lead_form_submission_count = 0
    inner_form_submission_count = 0
    generic_form_submission_count = 0
    video_view_count = 0

    distinct_visit_days = set()
    unique_pages = set()
    top_pages_map = {}

    first_activity_dt = None
    last_activity_dt = None

    def register_activity_time(value: Any):
        nonlocal first_activity_dt, last_activity_dt

        activity_dt = parse_datetime_loose(value)

        if not activity_dt:
            return

        if first_activity_dt is None or activity_dt < first_activity_dt:
            first_activity_dt = activity_dt

        if last_activity_dt is None or activity_dt > last_activity_dt:
            last_activity_dt = activity_dt

    for day in journey_days:
        if not isinstance(day, dict):
            continue

        day_date = first_non_empty(day.get("date"), day.get("track_date"))

        if day_date:
            distinct_visit_days.add(str(day_date))

        sessions = day.get("sessions", [])

        if not isinstance(sessions, list):
            continue

        for session in sessions:
            if not isinstance(session, dict):
                continue

            session_count += 1

            register_activity_time(
                first_non_empty(
                    session.get("started_at"),
                    session.get("start_time"),
                    session.get("visited_at"),
                    session.get("visit_datetime"),
                )
            )

            register_activity_time(
                first_non_empty(
                    session.get("ended_at"),
                    session.get("end_time"),
                    session.get("last_activity_at"),
                )
            )

            pages = session.get("pages", [])

            if not isinstance(pages, list):
                continue

            for page in pages:
                if not isinstance(page, dict):
                    continue

                page_view_count += 1

                page_url = get_page_url(page)
                page_title = get_page_title(page)
                page_visit_time = get_page_visit_time(page)

                register_activity_time(page_visit_time)

                time_spent = to_int(
                    page.get("time_spent_seconds")
                    or page.get("time_spent")
                    or page.get("duration")
                    or 0
                )

                if page_url:
                    unique_pages.add(str(page_url))

                    if page_url not in top_pages_map:
                        top_pages_map[page_url] = {
                            "page_url": page_url,
                            "page_title": page_title,
                            "visit_count": 0,
                            "total_time_spent_seconds": 0,
                        }

                    top_pages_map[page_url]["visit_count"] += 1
                    top_pages_map[page_url]["total_time_spent_seconds"] += time_spent

                actions = get_page_actions(page)

                for action in actions:
                    total_action_count += 1

                    register_activity_time(get_action_time(action))

                    action_class = classify_action(action)

                    if action_class == "asset_download":
                        asset_download_count += 1
                    elif action_class == "external_link_click":
                        external_link_click_count += 1
                    elif action_class == "lead_form_submission":
                        lead_form_submission_count += 1
                    elif action_class == "inner_form_submission":
                        inner_form_submission_count += 1
                    elif action_class == "form_submission":
                        generic_form_submission_count += 1
                    elif action_class == "video_view":
                        video_view_count += 1

    journey_has_data = bool(journey_days)

    if not journey_has_data:
        session_count = to_int(action_taken.get("total_visits"))
        page_view_count = to_int(
            action_taken.get("page_view_count")
            or action_taken.get("page_views")
            or action_taken.get("page_visited")
        )
        asset_download_count = to_int(action_taken.get("asset_downloaded"))
        external_link_click_count = to_int(action_taken.get("external_link_click"))
        lead_form_submission_count = to_int(
            action_taken.get("lead_form_submission")
            or action_taken.get("leadform_submission")
        )
        inner_form_submission_count = to_int(
            action_taken.get("inner_form_submission")
            or action_taken.get("innerform_submission")
        )
        generic_form_submission_count = to_int(action_taken.get("form_submission"))
        video_view_count = to_int(action_taken.get("video_view"))

    form_submission_count = (
        lead_form_submission_count
        + inner_form_submission_count
        + generic_form_submission_count
    )

    total_time_spent = to_int(
        row.get("total_time_spent")
        or action_taken.get("total_time_spent")
        or 0
    )

    top_pages = sorted(
        top_pages_map.values(),
        key=lambda item: (
            item.get("visit_count", 0),
            item.get("total_time_spent_seconds", 0),
        ),
        reverse=True,
    )[:5]

    first_activity_at = format_datetime(
        first_activity_dt
        or parse_datetime_loose(normalized_first_visit_date)
        or parse_datetime_loose(row.get("first_visit_date"))
    )

    last_activity_at = format_datetime(
        last_activity_dt
        or parse_datetime_loose(normalized_last_visit_date)
        or parse_datetime_loose(row.get("last_visit_date"))
        or parse_datetime_loose(row.get("last_visit_utc_datetime"))
    )

    return {
        "session_count": session_count,
        "page_view_count": page_view_count,
        "unique_page_count": len(unique_pages),
        "distinct_visit_days": len(distinct_visit_days),
        "total_action_count": total_action_count,
        "total_time_spent_seconds": total_time_spent,
        "first_activity_at": first_activity_at,
        "last_activity_at": last_activity_at,
        "asset_download_count": asset_download_count,
        "external_link_click_count": external_link_click_count,
        "lead_form_submission_count": lead_form_submission_count,
        "inner_form_submission_count": inner_form_submission_count,
        "form_submission_count": form_submission_count,
        "video_view_count": video_view_count,
        "known_track_id_count": len(track_ids) if isinstance(track_ids, list) else 0,
        "known_track_lead_id_count": len(track_lead_ids) if isinstance(track_lead_ids, list) else 0,
        "top_pages": top_pages,
    }


def build_top_evidence_facts(
    row: Dict[str, Any],
    signal_summary: Optional[Dict[str, Any]] = None,
) -> list:
    signal_summary = signal_summary or {}

    facts = []

    lead_form_count = to_int(signal_summary.get("lead_form_submission_count"))
    inner_form_count = to_int(signal_summary.get("inner_form_submission_count"))
    asset_download_count = to_int(signal_summary.get("asset_download_count"))
    external_link_click_count = to_int(signal_summary.get("external_link_click_count"))
    video_view_count = to_int(signal_summary.get("video_view_count"))
    distinct_visit_days = to_int(signal_summary.get("distinct_visit_days"))
    page_view_count = to_int(signal_summary.get("page_view_count"))

    if lead_form_count > 0:
        facts.append(
            {
                "fact_type": "conversion",
                "count": lead_form_count,
                "summary": f"Submitted lead forms {lead_form_count} time{'s' if lead_form_count != 1 else ''}.",
                "source": "journey_detail",
                "contributes_to": "conversion",
            }
        )

    if inner_form_count > 0:
        facts.append(
            {
                "fact_type": "conversion",
                "count": inner_form_count,
                "summary": f"Submitted inner forms {inner_form_count} time{'s' if inner_form_count != 1 else ''}.",
                "source": "journey_detail",
                "contributes_to": "conversion",
            }
        )

    if asset_download_count > 0:
        facts.append(
            {
                "fact_type": "asset_download",
                "count": asset_download_count,
                "summary": f"Downloaded assets {asset_download_count} time{'s' if asset_download_count != 1 else ''}.",
                "source": "journey_detail",
                "contributes_to": "depth",
            }
        )

    if external_link_click_count > 0:
        facts.append(
            {
                "fact_type": "external_link_click",
                "count": external_link_click_count,
                "summary": f"Clicked external links {external_link_click_count} time{'s' if external_link_click_count != 1 else ''}.",
                "source": "journey_detail",
                "contributes_to": "depth",
            }
        )

    if video_view_count > 0:
        facts.append(
            {
                "fact_type": "video_view",
                "count": video_view_count,
                "summary": f"Viewed videos {video_view_count} time{'s' if video_view_count != 1 else ''}.",
                "source": "journey_detail",
                "contributes_to": "depth",
            }
        )

    if distinct_visit_days > 1:
        facts.append(
            {
                "fact_type": "repeat_engagement",
                "count": distinct_visit_days,
                "summary": f"Returned across {distinct_visit_days} distinct days.",
                "source": "journey_detail",
                "contributes_to": "sustenance",
            }
        )

    if page_view_count > 0:
        facts.append(
            {
                "fact_type": "page_engagement",
                "count": page_view_count,
                "summary": f"Viewed {page_view_count} pages during the reporting window.",
                "source": "journey_detail",
                "contributes_to": "activity",
            }
        )

    if facts:
        return facts

    top_signal_json = safe_json_decode(row.get("top_signal_json"), None)
    raw_items = []

    if isinstance(top_signal_json, list):
        raw_items = top_signal_json
    elif isinstance(top_signal_json, dict):
        if isinstance(top_signal_json.get("facts"), list):
            raw_items = top_signal_json.get("facts")
        elif isinstance(top_signal_json.get("signals"), list):
            raw_items = top_signal_json.get("signals")
        elif isinstance(top_signal_json.get("top_signals"), list):
            raw_items = top_signal_json.get("top_signals")
        else:
            raw_items = [top_signal_json]

    for item in raw_items:
        if not isinstance(item, dict):
            facts.append(
                {
                    "fact_type": "signal",
                    "count": 1,
                    "summary": str(item),
                    "source": "top_signal_json",
                }
            )
            continue

        label = first_non_empty(
            item.get("label"),
            item.get("title"),
            item.get("signal"),
            item.get("name"),
            item.get("text"),
            item.get("summary"),
        )

        count = first_non_empty(
            item.get("count"),
            item.get("matched_count"),
            item.get("visit_count"),
            item.get("action_count"),
            1,
        )

        summary = first_non_empty(
            item.get("summary"),
            item.get("text"),
            item.get("description"),
            label,
        )

        facts.append(
            {
                "fact_type": item.get("fact_type") or item.get("type") or "signal",
                "count": to_int(count) or 1,
                "summary": summary,
                "label": label,
                "source": "top_signal_json",
                "contributes_to": item.get("contributes_to"),
            }
        )

    if not facts and row.get("insight_summary"):
        facts.append(
            {
                "fact_type": "insight_summary",
                "count": 1,
                "summary": row.get("insight_summary"),
                "source": "insight_summary",
            }
        )

    if not facts and row.get("account_summary_short"):
        facts.append(
            {
                "fact_type": "account_summary_short",
                "count": 1,
                "summary": row.get("account_summary_short"),
                "source": "account_summary_short",
            }
        )

    return facts