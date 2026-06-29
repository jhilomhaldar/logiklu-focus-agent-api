import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


TIMEZONE_NAME = "Asia/Kolkata"


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
        return value.isoformat()

    return str(value)


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


def build_where_clause(
    search: Optional[str] = None,
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
                OR fcl.city LIKE %s
                OR fcl.state LIKE %s
                OR fcl.country LIKE %s
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
            ]
        )

    if interest_level:
        where_parts.append("fcl.interest_category = %s")
        params.append(interest_level)

    if priority_label:
        where_parts.append("fcl.priority_label LIKE %s")
        params.append(f"%{priority_label.strip()}%")

    if is_shortlisted:
        where_parts.append("fcl.is_shortlisted = %s")
        params.append(is_shortlisted)

    return " AND ".join(where_parts), params


def fetch_focus_account_intelligence_list(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    search: Optional[str] = None,
    interest_level: Optional[str] = None,
    priority_label: Optional[str] = None,
    is_shortlisted: Optional[str] = None,
    include_journey: bool = False,
) -> Dict[str, Any]:
    """
    List Focus accounts with intelligence data.
    Minimum page size should be controlled by endpoint as 10.
    """

    connection = None

    page = max(page, 1)
    per_page = max(per_page, 10)
    offset = (page - 1) * per_page

    try:
        connection = get_client_connection(client_database)

        where_clause, params = build_where_clause(
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        journey_select = ""
        journey_join = ""

        if include_journey:
            journey_select = """
                fj.contacts,
                fj.journey_timeline_json,
                fj.first_visit_date,
                fj.last_visit_date,
                fj.total_visits,
                fj.total_time_spent,
            """

            journey_join = """
                LEFT JOIN lk_focus_report_company_journey fj
                    ON fj.report_company_log_id = fcl.report_company_log_id
            """

        count_sql = f"""
            SELECT COUNT(*) AS total_records
            FROM lk_focus_report_master frm

            INNER JOIN lk_focus_report_company_log fcl
                ON fcl.report_id = frm.report_id

            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = fcl.lead_id

            {journey_join}

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

                {journey_select}

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

            {journey_join}

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
    include_journey: bool = False,
) -> Dict[str, Any]:
    score_explanation = (
        safe_json_decode(row.get("score_explanation"), {})
        or safe_json_decode(row.get("final_explanation"), {})
        or safe_json_decode(row.get("explanations_json"), {})
        or {}
    )

    top_evidence_facts = build_top_evidence_facts(row)

    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])

    item = {
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
        "reporting_window": {
            "report_id": row.get("report_id"),
            "report_uid": row.get("report_uid"),
            "report_batch_uid": row.get("report_batch_uid"),
            "from_date": format_date(row.get("dataset_period_start")),
            "to_date": format_date(row.get("dataset_period_end")),
            "window_days": int(row.get("dataset_period") or 0),
            "report_period": int(row.get("report_period") or 0),
            "report_period_label": row.get("report_period_label"),
            "timezone": TIMEZONE_NAME,
        },
        "deterministic_scores": {
            "activity_score": to_number(row.get("activity_score")),
            "sustenance_score": to_number(row.get("sustenance_score")),
            "depth_score": to_number(row.get("depth_score")),
            "contextual_score": to_number(row.get("context_score")),
            "conversion_score": to_number(row.get("conversion_score")),
            "interest_score": to_number(row.get("interest_score")),
            "interest_level": row.get("interest_category"),
            "priority_score": to_number(row.get("priority_score")),
            "priority_label": row.get("priority_label"),
            "engagement_level": row.get("engagement_level"),
            "final_score": to_number(row.get("final_score")),
            "computed_at": format_datetime(row.get("company_score_created_date")),
        },
        "score_explanation": score_explanation,
        "top_evidence_facts": top_evidence_facts,
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
        journey_json = safe_json_decode(row.get("journey_timeline_json"), {})
        journey_days = []

        if isinstance(journey_json, dict):
            journey_days = journey_json.get("days", [])
        elif isinstance(journey_json, list):
            journey_days = journey_json

        contacts = safe_json_decode(row.get("contacts"), [])

        item["journey_detail"] = {
            "first_visit_date": format_datetime(row.get("first_visit_date")),
            "last_visit_date": format_datetime(row.get("last_visit_date")),
            "total_visits": int(row.get("total_visits") or 0),
            "total_time_spent_seconds": int(row.get("total_time_spent") or 0),
            "days": journey_days,
        }

        item["campaign_contact_attribution"]["contacts"] = (
            contacts if isinstance(contacts, list) else []
        )

    return item


def build_top_evidence_facts(row: Dict[str, Any]) -> list:
    top_signal_json = safe_json_decode(row.get("top_signal_json"), None)

    if isinstance(top_signal_json, list):
        return top_signal_json

    if isinstance(top_signal_json, dict):
        if isinstance(top_signal_json.get("facts"), list):
            return top_signal_json.get("facts")

        if isinstance(top_signal_json.get("signals"), list):
            return top_signal_json.get("signals")

        if isinstance(top_signal_json.get("top_signals"), list):
            return top_signal_json.get("top_signals")

        return [top_signal_json]

    facts = []

    if row.get("insight_summary"):
        facts.append(
            {
                "fact_type": "insight_summary",
                "text": row.get("insight_summary"),
            }
        )

    if row.get("account_summary_short"):
        facts.append(
            {
                "fact_type": "account_summary_short",
                "text": row.get("account_summary_short"),
            }
        )

    return facts