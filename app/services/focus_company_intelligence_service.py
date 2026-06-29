import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

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


def fetch_focus_company_intelligence(
    client_database: str,
    lead_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Fetch current active Focus company intelligence for one company/account.

    Used by:
    1. Public demo endpoint
    2. Protected API endpoint

    client_database must be passed by endpoint.
    """

    connection = None

    try:
        connection = get_client_connection(client_database)

        sql = """
            SELECT
                frm.report_id,
                frm.report_uid,
                frm.report_batch_uid,
                frm.dataset_period,
                frm.report_period,
                frm.report_period_label,
                frm.dataset_period_start,
                frm.dataset_period_end,
                frm.created_date AS report_created_date,

                fcl.report_company_log_id,
                fcl.lead_id,
                fcl.visitors_name,
                fcl.country,
                fcl.state,
                fcl.city,
                fcl.ip,
                fcl.website,
                fcl.track_ids,
                fcl.track_lead_ids,

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

                fcl.score_explanation,
                fcl.final_explanation,
                fcl.explanations_json,
                fcl.top_signal_json,
                fcl.insight_summary,
                fcl.account_summary_short,
                fcl.created_date AS company_score_created_date,

                fj.journey_id,
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
                lm.industry AS lead_industry,
                lm.country AS lead_country,
                lm.state AS lead_state,
                lm.city AS lead_city

            FROM lk_focus_report_master frm

            INNER JOIN lk_focus_report_company_log fcl
                ON fcl.report_id = frm.report_id

            LEFT JOIN lk_focus_report_company_journey fj
                ON fj.report_company_log_id = fcl.report_company_log_id

            LEFT JOIN lk_lead_master lm
                ON lm.lead_id = fcl.lead_id

            WHERE frm.is_current = 'Y'
              AND frm.report_status = 'active'
              AND fcl.lead_id = %s

            ORDER BY frm.report_id DESC, fcl.final_score DESC
            LIMIT 1
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, (lead_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return build_focus_company_intelligence_response(row)

    finally:
        if connection:
            connection.close()


def build_focus_company_intelligence_response(row: Dict[str, Any]) -> Dict[str, Any]:
    score_explanation = (
        safe_json_decode(row.get("score_explanation"), {})
        or safe_json_decode(row.get("final_explanation"), {})
        or safe_json_decode(row.get("explanations_json"), {})
        or {}
    )

    journey_json = safe_json_decode(row.get("journey_timeline_json"), {})
    journey_days = []

    if isinstance(journey_json, dict):
        journey_days = journey_json.get("days", [])
    elif isinstance(journey_json, list):
        journey_days = journey_json

    contacts = safe_json_decode(row.get("contacts"), [])
    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])

    return {
        "account": {
            "account_id": str(row.get("lead_id")) if row.get("lead_id") is not None else None,
            "company_id": str(row.get("lead_id")) if row.get("lead_id") is not None else None,
            "company_name": first_non_empty(
                row.get("lead_name"),
                row.get("visitors_name"),
            ),
            "company_domain": first_non_empty(
                row.get("lead_website"),
                row.get("website"),
            ),
            "account_status": first_non_empty(
                row.get("lead_category"),
                row.get("lead_status"),
            ),
            "lead_type": row.get("lead_type"),
            "is_identified_company": bool(
                row.get("lead_id") and int(row.get("lead_id")) > 0
            ),
            "location": {
                "country": first_non_empty(
                    row.get("lead_country"),
                    row.get("country"),
                ),
                "state": first_non_empty(
                    row.get("lead_state"),
                    row.get("state"),
                ),
                "city": first_non_empty(
                    row.get("lead_city"),
                    row.get("city"),
                ),
            },
            "industry": row.get("lead_industry"),
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
        "top_evidence_facts": build_top_evidence_facts(row),
        "journey_detail": {
            "first_visit_date": format_datetime(row.get("first_visit_date")),
            "last_visit_date": format_datetime(row.get("last_visit_date")),
            "total_visits": int(row.get("total_visits") or 0),
            "total_time_spent_seconds": int(row.get("total_time_spent") or 0),
            "days": journey_days,
        },
        "campaign_contact_attribution": {
            "contacts": contacts if isinstance(contacts, list) else [],
            "track_ids": track_ids if isinstance(track_ids, list) else [],
            "track_lead_ids": track_lead_ids if isinstance(track_lead_ids, list) else [],
        },
    }


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