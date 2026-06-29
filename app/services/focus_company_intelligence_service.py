import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from app.db.client import get_client_connection


TIMEZONE_NAME = "Asia/Kolkata"
SCHEMA_VERSION = "focus_company_intelligence.v1"


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


def normalize_first_last_visit(first_visit: Any, last_visit: Any) -> tuple:
    """
    Ensures first_visit_date is never after last_visit_date.
    If DB values are reversed, swap them at API output level.
    """

    if not first_visit or not last_visit:
        return first_visit, last_visit

    try:
        first_dt = (
            first_visit
            if isinstance(first_visit, datetime)
            else datetime.fromisoformat(str(first_visit))
        )
        last_dt = (
            last_visit
            if isinstance(last_visit, datetime)
            else datetime.fromisoformat(str(last_visit))
        )

        if first_dt > last_dt:
            return last_visit, first_visit

    except Exception:
        pass

    return first_visit, last_visit


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

    first_visit_date, last_visit_date = normalize_first_last_visit(
        row.get("first_visit_date"),
        row.get("last_visit_date"),
    )

    signal_summary = build_signal_summary(
        row=row,
        journey_days=journey_days,
        normalized_last_visit_date=last_visit_date,
    )

    contacts = safe_json_decode(row.get("contacts"), [])
    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])

    return {
        "schema_version": SCHEMA_VERSION,
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
        "top_evidence_facts": build_top_evidence_facts(row),
        "journey_detail": {
            "first_visit_date": format_datetime(first_visit_date),
            "last_visit_date": format_datetime(last_visit_date),
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


def build_signal_summary(
    row: Dict[str, Any],
    journey_days: list,
    normalized_last_visit_date: Any = None,
) -> Dict[str, Any]:
    action_taken = safe_json_decode(row.get("action_taken"), {})

    track_ids = safe_json_decode(row.get("track_ids"), [])
    track_lead_ids = safe_json_decode(row.get("track_lead_ids"), [])

    session_count = 0
    page_view_count = 0
    distinct_visit_days = set()
    top_pages_map = {}

    for day in journey_days:
        if not isinstance(day, dict):
            continue

        day_date = day.get("date")

        if day_date:
            distinct_visit_days.add(day_date)

        sessions = day.get("sessions", [])

        if not isinstance(sessions, list):
            continue

        for session in sessions:
            if not isinstance(session, dict):
                continue

            session_count += 1

            pages = session.get("pages", [])

            if not isinstance(pages, list):
                continue

            for page in pages:
                if not isinstance(page, dict):
                    continue

                page_view_count += 1

                page_url = page.get("page_url") or page.get("url")
                page_title = page.get("page_title") or page.get("title")
                time_spent = to_int(
                    page.get("time_spent_seconds")
                    or page.get("time_spent")
                    or 0
                )

                if page_url:
                    if page_url not in top_pages_map:
                        top_pages_map[page_url] = {
                            "page_url": page_url,
                            "page_title": page_title,
                            "visit_count": 0,
                            "total_time_spent_seconds": 0,
                        }

                    top_pages_map[page_url]["visit_count"] += 1
                    top_pages_map[page_url]["total_time_spent_seconds"] += time_spent

    top_pages = sorted(
        top_pages_map.values(),
        key=lambda item: (
            item.get("visit_count", 0),
            item.get("total_time_spent_seconds", 0),
        ),
        reverse=True,
    )[:5]

    total_visits = to_int(
        row.get("total_visits")
        or action_taken.get("total_visits")
        or session_count
        or 0
    )

    total_time_spent = to_int(
        row.get("total_time_spent")
        or action_taken.get("total_time_spent")
        or 0
    )

    page_view_count_final = to_int(
        action_taken.get("page_visited")
        or action_taken.get("page_view_count")
        or page_view_count
        or 0
    )

    return {
        "session_count": total_visits,
        "page_view_count": page_view_count_final,
        "distinct_visit_days": len(distinct_visit_days),
        "total_time_spent_seconds": total_time_spent,
        "last_activity_at": format_datetime(
            normalized_last_visit_date
            or row.get("last_visit_date")
            or row.get("last_visit_utc_datetime")
        ),
        "asset_download_count": to_int(action_taken.get("asset_downloaded")),
        "form_submission_count": to_int(
            action_taken.get("form_submission")
            or action_taken.get("lead_form_submission")
            or action_taken.get("inner_form_submission")
        ),
        "external_link_click_count": to_int(action_taken.get("external_link_click")),
        "video_view_count": to_int(action_taken.get("video_view")),
        "known_track_id_count": len(track_ids) if isinstance(track_ids, list) else 0,
        "known_track_lead_id_count": len(track_lead_ids) if isinstance(track_lead_ids, list) else 0,
        "top_pages": top_pages,
    }


def build_top_evidence_facts(row: Dict[str, Any]) -> list:
    top_signal_json = safe_json_decode(row.get("top_signal_json"), None)
    facts = []

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

        count_value = count

        try:
            count_value = int(float(count))
        except Exception:
            pass

        facts.append(
            {
                "fact_type": item.get("fact_type") or item.get("type") or "signal",
                "count": count_value,
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