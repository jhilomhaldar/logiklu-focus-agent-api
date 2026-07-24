# app/services/focus_report_service.py

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymysql  # type: ignore
except Exception:  # pragma: no cover
    pymysql = None

from app.db.client import get_client_connection


SCHEMA_VERSION = "logiklu_focus_agent_report.v1"


class FocusReportValidationError(Exception):
    pass


class FocusReportStorageError(Exception):
    pass


class FocusReportNotFoundError(Exception):
    pass


def _cursor(connection):
    """Return a dictionary cursor for mysql-connector or PyMySQL connections."""
    try:
        return connection.cursor(dictionary=True)
    except TypeError:
        if pymysql is not None:
            try:
                return connection.cursor(pymysql.cursors.DictCursor)
            except Exception:
                pass
        return connection.cursor()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_json_value(value: Any, default: Any = None) -> Any:
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


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)

    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value.strftime("%Y-%m-%d")

    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_jsonable(item) for item in value]

    return value


def _parse_json_column(value: Any, default: Any = None) -> Any:
    return _jsonable(_safe_json_value(value, default if default is not None else {}))


def _fetch_one(cursor, sql: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return row if row else None


def _fetch_all(cursor, sql: str, params: Tuple[Any, ...]) -> List[Dict[str, Any]]:
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return list(rows or [])


def _require_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise FocusReportValidationError("Request body must be a JSON object")

    required_fields = ["report_id", "report_uid", "report_batch_uid"]

    missing = []
    for field in required_fields:
        if payload.get(field) in [None, ""]:
            missing.append(field)

    if missing:
        raise FocusReportValidationError("Missing required field(s): " + ", ".join(missing))

    report_id = _safe_int(payload.get("report_id"), 0)
    if report_id <= 0:
        raise FocusReportValidationError("report_id must be a positive integer")


def _normalize_priority_accounts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = (
        payload.get("priority_accounts")
        or payload.get("priority_accounts_list")
        or payload.get("priorityAccounts")
        or []
    )

    if not isinstance(values, list):
        raise FocusReportValidationError("priority_accounts must be an array")

    output: List[Dict[str, Any]] = []

    for index, item in enumerate(values, start=1):
        if not isinstance(item, dict):
            continue

        account_id = _safe_int(item.get("account_id") or item.get("lead_id"), 0)

        if account_id <= 0:
            continue

        final_explanation = _safe_json_value(item.get("final_explanation"), {})

        output.append(
            {
                "account_id": account_id,
                "priority_rank": _safe_int(item.get("priority_rank") or item.get("rank"), index),
                "final_explanation": final_explanation,
            }
        )

    return output


def _normalize_contacts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = (
        payload.get("contacts")
        or payload.get("interacted_contacts")
        or payload.get("contact_interactions")
        or payload.get("interactedContacts")
        or []
    )

    if not isinstance(values, list):
        raise FocusReportValidationError("contacts must be an array")

    output: List[Dict[str, Any]] = []

    for item in values:
        if not isinstance(item, dict):
            continue

        account_id = _safe_int(item.get("account_id") or item.get("lead_id"), 0)

        if account_id <= 0:
            continue

        interaction_details = _safe_json_value(
            item.get("interaction_details")
            or item.get("interaction_details_json")
            or item.get("interaction"),
            {},
        )

        output.append(
            {
                "account_id": account_id,
                "contact_id": _safe_int(item.get("contact_id"), 0),
                "name": _safe_str(item.get("name") or item.get("contact_name")),
                "email": _safe_str(item.get("email") or item.get("contact_email")),
                "phone": _safe_str(item.get("phone") or item.get("contact_phone")),
                "interaction_details": interaction_details,
                "interaction_summary": _safe_str(
                    item.get("interaction_summary")
                    or item.get("summary")
                    or (interaction_details.get("summary") if isinstance(interaction_details, dict) else "")
                ),
            }
        )

    return output


def _fetch_company_report_snapshot(
    cursor,
    source_report_id: int,
    account_id: int,
) -> Optional[Dict[str, Any]]:
    """Fetch old company report row from lk_focus_report_company.

    This row is used for account snapshot/details only.
    Source activity is generated separately from
    lk_focus_report_company_journey.journey_timeline_json.
    AI does not post source data.
    """
    sql = """
        SELECT
            report_company_id,
            report_id,
            lead_id,
            source_activity_json,
            visitors_name,
            country,
            state,
            city,
            website,
            action_taken,
            final_explanation,
            insight_summary,
            account_summary_short,
            priority_score,
            priority_label,
            engagement_level,
            final_score,
            report_rank,
            created_date
        FROM lk_focus_report_company
        WHERE report_id = %s
          AND lead_id = %s
        ORDER BY
            CASE WHEN report_rank IS NULL THEN 1 ELSE 0 END ASC,
            report_rank ASC,
            final_score DESC,
            report_company_id DESC
        LIMIT 1
    """

    return _fetch_one(
        cursor,
        sql,
        (source_report_id, account_id),
    )


def _fetch_company_journey_snapshot(
    cursor,
    source_report_id: int,
    account_id: int,
) -> Optional[Dict[str, Any]]:
    """Fetch journey row used to generate source activity.

    Business rule:
    AI will not post source activity. The API prepares source activity from
    lk_focus_report_company_journey.journey_timeline_json for the same
    report/account and stores it in lk_focus_agent_report_priority_account.source_json.
    """
    sql = """
        SELECT
            journey_id,
            report_id,
            report_uid,
            report_batch_uid,
            report_company_log_id,
            lead_id,
            visitors_name,
            companyfetch_type,
            country,
            state,
            city,
            website,
            journey_timeline_json,
            first_visit_date,
            last_visit_date,
            total_visits,
            total_time_spent,
            shortlisted_rank,
            final_score,
            created_date
        FROM lk_focus_report_company_journey
        WHERE report_id = %s
          AND lead_id = %s
        ORDER BY
            CASE WHEN is_shortlisted = 'Y' THEN 0 ELSE 1 END ASC,
            CASE WHEN shortlisted_rank IS NULL THEN 1 ELSE 0 END ASC,
            shortlisted_rank ASC,
            final_score DESC,
            journey_id DESC
        LIMIT 1
    """

    return _fetch_one(
        cursor,
        sql,
        (source_report_id, account_id),
    )


def _date_only(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    value = _safe_str(value)
    if len(value) >= 10:
        return value[:10]

    return value


def _source_label_from_source(source_data: Dict[str, Any]) -> str:
    source_type = _safe_str(source_data.get("source_type"))
    source_label = _safe_str(source_data.get("source_label"))

    if source_type:
        return source_type

    if source_label:
        lowered = source_label.lower()
        if lowered == "direct visit":
            return "Direct"
        return source_label

    return "Direct"


def _source_name_from_source(source_data: Dict[str, Any]) -> str:
    source_type = _safe_str(source_data.get("source_type")).lower()
    source_label = _safe_str(source_data.get("source_label")).lower()

    campaign_name = _safe_str(source_data.get("campaign_name"))
    campaign_subject = _safe_str(source_data.get("campaign_subject"))
    link_name = _safe_str(source_data.get("link_name"))
    provider = _safe_str(source_data.get("provider"))
    entry_page_title = _safe_str(source_data.get("entry_page_title"))

    if campaign_name:
        return campaign_name

    if campaign_subject:
        return campaign_subject

    if link_name:
        return link_name

    if provider:
        return provider

    if source_type == "direct" or source_label == "direct visit":
        return "Website Visit"

    if entry_page_title:
        return "Website Visit"

    return "Website Visit"


def _build_source_activity_from_journey(journey_report: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the source activity array from journey timeline sessions.

    Output format:
    [
        {
            "source": "Direct",
            "visited_date": "2026-06-30",
            "source_details": {
                "source_name": "Website Visit"
            }
        }
    ]
    """
    if not journey_report:
        return []

    journey_timeline = _parse_json_column(journey_report.get("journey_timeline_json"), {})
    days = []

    if isinstance(journey_timeline, dict):
        days = journey_timeline.get("days") or []
    elif isinstance(journey_timeline, list):
        days = journey_timeline

    if not isinstance(days, list):
        return []

    output: List[Dict[str, Any]] = []
    seen = set()

    for day in days:
        if not isinstance(day, dict):
            continue

        day_date = _date_only(day.get("date"))
        sessions = day.get("sessions") or []

        if not isinstance(sessions, list):
            continue

        for session in sessions:
            if not isinstance(session, dict):
                continue

            source_data = session.get("source") or {}
            if not isinstance(source_data, dict):
                source_data = {}

            source = _source_label_from_source(source_data)
            visited_date = _date_only(
                source_data.get("visited_at")
                or session.get("started_at")
                or session.get("ended_at")
                or day_date
            )

            if not visited_date:
                visited_date = day_date

            source_name = _source_name_from_source(source_data)
            unique_key = (source, visited_date, source_name)

            if unique_key in seen:
                continue

            seen.add(unique_key)
            output.append(
                {
                    "source": source,
                    "visited_date": visited_date,
                    "source_details": {
                        "source_name": source_name,
                    },
                }
            )

    return output


def _build_account_snapshot(company_report: Optional[Dict[str, Any]], account_id: int) -> Dict[str, Any]:
    if not company_report:
        return {
            "account_id": account_id,
            "account_name": None,
            "website": None,
            "location": {
                "city": None,
                "state": None,
                "country": None,
            },
        }

    return {
        "account_id": account_id,
        "account_name": company_report.get("visitors_name"),
        "website": company_report.get("website"),
        "location": {
            "city": company_report.get("city"),
            "state": company_report.get("state"),
            "country": company_report.get("country"),
        },
        "old_report": {
            "report_company_id": company_report.get("report_company_id"),
            "priority_score": company_report.get("priority_score"),
            "priority_label": company_report.get("priority_label"),
            "engagement_level": company_report.get("engagement_level"),
            "final_score": company_report.get("final_score"),
        },
    }


def _fetch_contact_snapshot(cursor, contact_id: int) -> Optional[Dict[str, Any]]:
    if contact_id <= 0:
        return None

    sql = """
        SELECT
            contact_id,
            lead_id,
            first_name,
            last_name,
            email,
            phone,
            designation,
            department,
            city,
            state,
            country,
            zipcode,
            address,
            source,
            created_date,
            modified_date
        FROM lk_central_contacts
        WHERE contact_id = %s
        LIMIT 1
    """

    try:
        return _fetch_one(cursor, sql, (contact_id,))
    except Exception:
        return None


def _contact_name_from_snapshot(snapshot: Optional[Dict[str, Any]]) -> str:
    if not snapshot:
        return ""
    return " ".join([
        _safe_str(snapshot.get("first_name")),
        _safe_str(snapshot.get("last_name")),
    ]).strip()


def _delete_current_report_rows(cursor) -> None:
    cursor.execute("DELETE FROM lk_focus_agent_report_contact_interaction")
    cursor.execute("DELETE FROM lk_focus_agent_report_priority_account")
    cursor.execute("DELETE FROM lk_focus_agent_report_master")


def _insert_master_report(
    cursor,
    source_report_id: int,
    report_uid: str,
    report_batch_uid: str,
    executive_snapshot: Dict[str, Any],
    buyer_intent_snapshot: Dict[str, Any],
    priority_account_count: int,
    interacted_contact_count: int,
    raw_payload: Dict[str, Any],
) -> int:
    sql = """
        INSERT INTO lk_focus_agent_report_master
        (
            report_slot,
            source_report_id,
            report_uid,
            report_batch_uid,
            executive_snapshot_json,
            buyer_intent_snapshot_json,
            priority_account_count,
            interacted_contact_count,
            raw_payload_json,
            created_date,
            updated_date
        )
        VALUES
        (
            'current',
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            NOW(),
            NULL
        )
    """

    cursor.execute(
        sql,
        (
            source_report_id,
            report_uid,
            report_batch_uid,
            _json_dumps(executive_snapshot),
            _json_dumps(buyer_intent_snapshot),
            priority_account_count,
            interacted_contact_count,
            _json_dumps(raw_payload),
        ),
    )

    return int(cursor.lastrowid)


def _insert_priority_account(
    cursor,
    agent_report_id: int,
    source_report_id: int,
    report_uid: str,
    report_batch_uid: str,
    item: Dict[str, Any],
    company_report: Optional[Dict[str, Any]],
    journey_report: Optional[Dict[str, Any]],
) -> None:
    account_id = _safe_int(item.get("account_id"), 0)
    final_explanation = _safe_json_value(item.get("final_explanation"), {})
    engagement_pattern = []
    why_company_matters = []
    account_insight_summary = ""

    if isinstance(final_explanation, dict):
        engagement_pattern = final_explanation.get("engagement_pattern") or []
        why_company_matters = final_explanation.get("why_company_matters") or []
        account_insight_summary = _safe_str(final_explanation.get("account_insight_summary"))

    if not account_insight_summary and company_report:
        account_insight_summary = _safe_str(company_report.get("insight_summary"))

    # Source activity is generated from the journey timeline.
    # AI-posted payload must not override or add source content.
    source_json = _build_source_activity_from_journey(journey_report)
    account_snapshot = _build_account_snapshot(company_report, account_id)

    source_company_log_id = None
    if journey_report:
        source_company_log_id = _safe_int(journey_report.get("report_company_log_id"), 0)
    elif company_report:
        source_company_log_id = _safe_int(company_report.get("report_company_id"), 0)

    if journey_report:
        source_type = "lk_focus_report_company_journey.journey_timeline_json"
        source_summary = "Source activity generated from journey timeline session sources"
    elif company_report:
        source_type = "lk_focus_report_company_journey.not_found"
        source_summary = "Company row found but journey row not found; source activity is empty"
    else:
        source_type = "not_found"
        source_summary = "Company and journey source rows not found; source activity is empty"

    sql = """
        INSERT INTO lk_focus_agent_report_priority_account
        (
            agent_report_id,
            source_report_id,
            report_uid,
            report_batch_uid,
            account_id,
            source_company_log_id,
            source_type,
            source_summary,
            source_json,
            priority_rank,
            account_name,
            website,
            country,
            state,
            city,
            final_explanation_json,
            engagement_pattern_json,
            why_company_matters_json,
            account_insight_summary,
            account_snapshot_json,
            created_date
        )
        VALUES
        (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            NOW()
        )
    """

    cursor.execute(
        sql,
        (
            agent_report_id,
            source_report_id,
            report_uid,
            report_batch_uid,
            account_id,
            source_company_log_id or None,
            source_type,
            source_summary,
            _json_dumps(source_json),
            item.get("priority_rank"),
            company_report.get("visitors_name") if company_report else None,
            company_report.get("website") if company_report else None,
            company_report.get("country") if company_report else None,
            company_report.get("state") if company_report else None,
            company_report.get("city") if company_report else None,
            _json_dumps(final_explanation),
            _json_dumps(engagement_pattern),
            _json_dumps(why_company_matters),
            account_insight_summary,
            _json_dumps(account_snapshot),
        ),
    )


def _insert_contact_interaction(
    cursor,
    agent_report_id: int,
    source_report_id: int,
    report_uid: str,
    report_batch_uid: str,
    item: Dict[str, Any],
) -> None:
    contact_id = _safe_int(item.get("contact_id"), 0)
    snapshot = _fetch_contact_snapshot(cursor, contact_id)

    contact_name = _safe_str(item.get("name")) or _contact_name_from_snapshot(snapshot)
    contact_email = _safe_str(item.get("email")) or (snapshot.get("email") if snapshot else "")
    contact_phone = _safe_str(item.get("phone")) or (snapshot.get("phone") if snapshot else "")

    contact_snapshot = {
        "posted": {
            "account_id": item.get("account_id"),
            "contact_id": contact_id or None,
            "name": item.get("name"),
            "email": item.get("email"),
            "phone": item.get("phone"),
        },
        "crm": snapshot or {},
    }

    sql = """
        INSERT INTO lk_focus_agent_report_contact_interaction
        (
            agent_report_id,
            source_report_id,
            report_uid,
            report_batch_uid,
            account_id,
            contact_id,
            contact_name,
            contact_email,
            contact_phone,
            interaction_details_json,
            interaction_summary,
            contact_snapshot_json,
            created_date
        )
        VALUES
        (
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            NOW()
        )
    """

    cursor.execute(
        sql,
        (
            agent_report_id,
            source_report_id,
            report_uid,
            report_batch_uid,
            item.get("account_id"),
            contact_id or None,
            contact_name,
            contact_email,
            contact_phone,
            _json_dumps(item.get("interaction_details") or {}),
            item.get("interaction_summary") or "",
            _json_dumps(contact_snapshot),
        ),
    )


def save_current_focus_report(client_database: str, payload: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_payload(payload)

    if not client_database:
        raise FocusReportValidationError("Client database is missing")

    source_report_id = _safe_int(payload.get("report_id"), 0)
    report_uid = _safe_str(payload.get("report_uid"))
    report_batch_uid = _safe_str(payload.get("report_batch_uid"))

    executive_snapshot = _safe_json_value(
        payload.get("executive_snapshot") or payload.get("executive_snapshot_json"),
        {},
    )
    buyer_intent_snapshot = _safe_json_value(
        payload.get("buyer_intent_snapshot_json") or payload.get("buyer_intent_snapshot"),
        {},
    )

    priority_accounts = _normalize_priority_accounts(payload)
    contacts = _normalize_contacts(payload)

    connection = None
    cursor = None

    try:
        connection = get_client_connection(client_database)
        cursor = _cursor(connection)

        connection.begin()

        _delete_current_report_rows(cursor)

        agent_report_id = _insert_master_report(
            cursor=cursor,
            source_report_id=source_report_id,
            report_uid=report_uid,
            report_batch_uid=report_batch_uid,
            executive_snapshot=executive_snapshot,
            buyer_intent_snapshot=buyer_intent_snapshot,
            priority_account_count=len(priority_accounts),
            interacted_contact_count=len(contacts),
            raw_payload=payload,
        )

        for item in priority_accounts:
            account_id = _safe_int(item.get("account_id"), 0)
            company_report = _fetch_company_report_snapshot(
                cursor=cursor,
                source_report_id=source_report_id,
                account_id=account_id,
            )
            journey_report = _fetch_company_journey_snapshot(
                cursor=cursor,
                source_report_id=source_report_id,
                account_id=account_id,
            )
            _insert_priority_account(
                cursor=cursor,
                agent_report_id=agent_report_id,
                source_report_id=source_report_id,
                report_uid=report_uid,
                report_batch_uid=report_batch_uid,
                item=item,
                company_report=company_report,
                journey_report=journey_report,
            )

        for item in contacts:
            _insert_contact_interaction(
                cursor=cursor,
                agent_report_id=agent_report_id,
                source_report_id=source_report_id,
                report_uid=report_uid,
                report_batch_uid=report_batch_uid,
                item=item,
            )

        connection.commit()

        return {
            "schema_version": SCHEMA_VERSION,
            "agent_report_id": agent_report_id,
            "source_report_id": source_report_id,
            "report_uid": report_uid,
            "report_batch_uid": report_batch_uid,
            "priority_account_count": len(priority_accounts),
            "interacted_contact_count": len(contacts),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except FocusReportValidationError:
        if connection:
            connection.rollback()
        raise

    except Exception as exc:
        if connection:
            connection.rollback()
        raise FocusReportStorageError(str(exc))

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass

        try:
            if connection:
                connection.close()
        except Exception:
            pass


def _normalize_report_master_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent_report_id": row.get("agent_report_id"),
        "source_report_id": row.get("source_report_id"),
        "report_uid": row.get("report_uid"),
        "report_batch_uid": row.get("report_batch_uid"),
        "executive_snapshot": _parse_json_column(row.get("executive_snapshot_json"), {}),
        "buyer_intent_snapshot": _parse_json_column(row.get("buyer_intent_snapshot_json"), {}),
        "priority_account_count": _safe_int(row.get("priority_account_count"), 0),
        "interacted_contact_count": _safe_int(row.get("interacted_contact_count"), 0),
        "created_date": _jsonable(row.get("created_date")),
        "updated_date": _jsonable(row.get("updated_date")),
    }


def _normalize_priority_account_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent_report_account_id": row.get("agent_report_account_id"),
        "account_id": row.get("account_id"),
        "priority_rank": row.get("priority_rank"),
        "account": {
            "account_id": row.get("account_id"),
            "name": row.get("account_name"),
            "website": row.get("website"),
            "location": {
                "city": row.get("city"),
                "state": row.get("state"),
                "country": row.get("country"),
            },
            "snapshot": _parse_json_column(row.get("account_snapshot_json"), {}),
        },
        # source is the source activity array generated from
        # lk_focus_report_company_journey.journey_timeline_json.
        "source": _parse_json_column(row.get("source_json"), []),
        "source_reference": {
            "source_company_id": row.get("source_company_log_id"),
            "source_type": row.get("source_type"),
            "source_summary": row.get("source_summary"),
        },
        "final_explanation": _parse_json_column(row.get("final_explanation_json"), {}),
        "engagement_pattern": _parse_json_column(row.get("engagement_pattern_json"), []),
        "why_company_matters": _parse_json_column(row.get("why_company_matters_json"), []),
        "account_insight_summary": row.get("account_insight_summary"),
        "created_date": _jsonable(row.get("created_date")),
    }


def _normalize_contact_interaction_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent_report_contact_id": row.get("agent_report_contact_id"),
        "account_id": row.get("account_id"),
        "contact_id": row.get("contact_id"),
        "name": row.get("contact_name"),
        "email": row.get("contact_email"),
        "phone": row.get("contact_phone"),
        "interaction_details": _parse_json_column(row.get("interaction_details_json"), {}),
        "interaction_summary": row.get("interaction_summary"),
        "contact_snapshot": _parse_json_column(row.get("contact_snapshot_json"), {}),
        "created_date": _jsonable(row.get("created_date")),
    }


def get_current_focus_report(client_database: str, auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not client_database:
        raise FocusReportValidationError("Client database is missing")

    connection = None
    cursor = None

    try:
        connection = get_client_connection(client_database)
        cursor = _cursor(connection)

        master_row = _fetch_one(
            cursor,
            """
            SELECT
                agent_report_id,
                source_report_id,
                report_uid,
                report_batch_uid,
                executive_snapshot_json,
                buyer_intent_snapshot_json,
                priority_account_count,
                interacted_contact_count,
                raw_payload_json,
                created_date,
                updated_date
            FROM lk_focus_agent_report_master
            WHERE report_slot = 'current'
            ORDER BY agent_report_id DESC
            LIMIT 1
            """,
            (),
        )

        if not master_row:
            raise FocusReportNotFoundError("No current Focus report found")

        agent_report_id = _safe_int(master_row.get("agent_report_id"), 0)

        account_rows = _fetch_all(
            cursor,
            """
            SELECT
                agent_report_account_id,
                agent_report_id,
                source_report_id,
                report_uid,
                report_batch_uid,
                account_id,
                source_company_log_id,
                source_type,
                source_summary,
                source_json,
                priority_rank,
                account_name,
                website,
                country,
                state,
                city,
                final_explanation_json,
                engagement_pattern_json,
                why_company_matters_json,
                account_insight_summary,
                account_snapshot_json,
                created_date
            FROM lk_focus_agent_report_priority_account
            WHERE agent_report_id = %s
            ORDER BY
                CASE WHEN priority_rank IS NULL THEN 1 ELSE 0 END ASC,
                priority_rank ASC,
                agent_report_account_id ASC
            """,
            (agent_report_id,),
        )

        contact_rows = _fetch_all(
            cursor,
            """
            SELECT
                agent_report_contact_id,
                agent_report_id,
                source_report_id,
                report_uid,
                report_batch_uid,
                account_id,
                contact_id,
                contact_name,
                contact_email,
                contact_phone,
                interaction_details_json,
                interaction_summary,
                contact_snapshot_json,
                created_date
            FROM lk_focus_agent_report_contact_interaction
            WHERE agent_report_id = %s
            ORDER BY account_id ASC, contact_name ASC, agent_report_contact_id ASC
            """,
            (agent_report_id,),
        )

        priority_accounts = [_normalize_priority_account_row(row) for row in account_rows]
        interacted_contacts = [_normalize_contact_interaction_row(row) for row in contact_rows]

        contacts_by_account: Dict[str, List[Dict[str, Any]]] = {}
        for contact in interacted_contacts:
            key = str(contact.get("account_id") or 0)
            contacts_by_account.setdefault(key, []).append(contact)

        report = _normalize_report_master_row(master_row)
        report.update(
            {
                "schema_version": SCHEMA_VERSION,
                "priority_accounts": priority_accounts,
                "interacted_contacts": interacted_contacts,
                "contacts_by_account": contacts_by_account,
                "raw_payload": _parse_json_column(master_row.get("raw_payload_json"), {}),
            }
        )

        return report

    except FocusReportNotFoundError:
        raise

    except FocusReportValidationError:
        raise

    except Exception as exc:
        raise FocusReportStorageError(str(exc))

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass

        try:
            if connection:
                connection.close()
        except Exception:
            pass
