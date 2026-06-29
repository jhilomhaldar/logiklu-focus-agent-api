# app/services/focus_account_service.py

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.db.client import get_client_connection


TIMEZONE_NAME = "Asia/Kolkata"


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


def build_focus_accounts_where_clause(
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

    where_clause = " AND ".join(where_parts)

    return where_clause, params


def fetch_focus_accounts(
    client_database: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    interest_level: Optional[str] = None,
    priority_label: Optional[str] = None,
    is_shortlisted: Optional[str] = None,
) -> List[Dict[str, Any]]:
    connection = None

    try:
        connection = get_client_connection(client_database)

        where_clause, params = build_focus_accounts_where_clause(
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

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
                fcl.ip AS focus_ip,
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
                fcl.insight_summary,
                fcl.account_summary_short,
                fcl.created_date AS focus_created_date,

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

            WHERE {where_clause}

            ORDER BY
                fcl.final_score DESC,
                fcl.last_visit_utc_datetime DESC,
                fcl.report_company_log_id DESC

            LIMIT %s OFFSET %s
        """

        query_params = params + [limit, offset]

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

        return [build_focus_account_list_item(row) for row in rows]

    finally:
        if connection:
            connection.close()


def count_focus_accounts(
    client_database: str,
    search: Optional[str] = None,
    interest_level: Optional[str] = None,
    priority_label: Optional[str] = None,
    is_shortlisted: Optional[str] = None,
) -> int:
    connection = None

    try:
        connection = get_client_connection(client_database)

        where_clause, params = build_focus_accounts_where_clause(
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        sql = f"""
            SELECT COUNT(*) AS total_records
            FROM lk_focus_report_master frm

            INNER JOIN lk_focus_report_company_log fcl
                ON fcl.report_id = frm.report_id

            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = fcl.lead_id

            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        return int(row.get("total_records") or 0)

    finally:
        if connection:
            connection.close()


def build_focus_account_list_item(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
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
        "focus_score": {
            "activity_score": to_number(row.get("activity_score")),
            "depth_score": to_number(row.get("depth_score")),
            "sustenance_score": to_number(row.get("sustenance_score")),
            "contextual_score": to_number(row.get("context_score")),
            "conversion_score": to_number(row.get("conversion_score")),
            "interest_score": to_number(row.get("interest_score")),
            "interest_level": row.get("interest_category"),
            "priority_score": to_number(row.get("priority_score")),
            "priority_label": row.get("priority_label"),
            "engagement_level": row.get("engagement_level"),
            "final_score": to_number(row.get("final_score")),
        },
        "focus_report": {
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
        "focus_status": {
            "is_shortlisted": row.get("is_shortlisted"),
            "shortlisted_rank": row.get("shortlisted_rank"),
            "shortlist_reason": row.get("shortlist_reason"),
            "exclusion_reason": row.get("exclusion_reason"),
        },
        "summary": {
            "insight_summary": row.get("insight_summary"),
            "account_summary_short": row.get("account_summary_short"),
        },
        "activity": {
            "last_visit_utc_datetime": format_datetime(row.get("last_visit_utc_datetime")),
            "focus_created_date": format_datetime(row.get("focus_created_date")),
        },
        "ownership": {
            "owner": row.get("owner"),
            "created_date": format_datetime(row.get("lead_created_date")),
            "modified_date": format_datetime(row.get("lead_modified_date")),
        },
    }