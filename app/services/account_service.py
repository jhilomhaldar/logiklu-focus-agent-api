import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.config import settings
from app.db.client import get_client_connection, validate_database_name


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
    "account_id": "lm.lead_id",
    "lead_name": "lm.lead_name",
    "lead_segment": "lm.lead_segment",
    "lead_category": "lm.lead_category",
    "lead_type": "lm.lead_type",
    "lead_status_id": "lm.lead_persuing_status",
    "lead_status_name": "lsm.lead_status_name",
    "website": "lm.website",
    "email": "lm.email",
    "phone": "lm.phone",
    "industry": "lm.industry",
    "city": "lm.city",
    "state": "lm.state",
    "country": "lm.country",
    "zipcode": "lm.zipcode",
    "source": "lm.source",
    "lead_source": "lm.lead_source",
    "owner": "lm.owner",
    "created_by": "lm.created_by",
    "modified_by": "lm.modified_by",
    "created_date": "lm.created_date",
    "modified_date": "lm.modified_date",
    "status_change_date": "lm.status_change_date",
}


def parse_json_value(value: Any) -> Any:
    if value is None or value == "":
        return None

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return value


def format_phone(phone_value: Any) -> str:
    parsed = parse_json_value(phone_value)

    if isinstance(parsed, dict):
        country_code = str(
            parsed.get("country_code")
            or parsed.get("counyry_code")
            or ""
        ).strip()

        phone = str(parsed.get("phone") or "").strip()

        if country_code and phone:
            return f"{country_code} {phone}"

        return phone or country_code

    return str(phone_value or "").strip()


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


def convert_datetime_to_utc(value: Any, timezone_name: Optional[str]) -> Optional[str]:
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


def user_full_name(row: Dict[str, Any], prefix: str) -> str:
    first_name = str(row.get(f"{prefix}_first_name") or "").strip()
    last_name = str(row.get(f"{prefix}_last_name") or "").strip()

    return f"{first_name} {last_name}".strip()


def user_info(row: Dict[str, Any], prefix: str) -> Dict[str, str]:
    return {
        "name": user_full_name(row, prefix),
        "email": str(row.get(f"{prefix}_email") or "").strip(),
    }


def computed_lead_category(raw_category: Any, active_contact_count: int) -> str:
    category = str(raw_category or "").strip().lower()

    if category == "customer":
        return "Customer"

    if category == "lead":
        if active_contact_count > 0:
            return "Lead"

        return "Potential Lead"

    if category == "suspect":
        return "Potential Lead"

    return category[:1].upper() + category[1:] if category else ""


def build_computed_lead_category_condition(
    computed_category: str,
    where_clauses: List[str],
) -> None:
    category = str(computed_category or "all").strip().lower()

    if category == "all":
        return

    if category == "lead":
        where_clauses.append("lm.lead_category = 'lead'")
        where_clauses.append(
            """
            (
                SELECT COUNT(*)
                FROM lk_central_contacts cc_lead
                WHERE cc_lead.lead_id = lm.lead_id
                  AND cc_lead.active_status = 'active'
            ) > 0
            """
        )
        return

    if category == "potential_lead":
        where_clauses.append(
            """
            (
                lm.lead_category = 'suspect'
                OR
                (
                    lm.lead_category = 'lead'
                    AND
                    (
                        SELECT COUNT(*)
                        FROM lk_central_contacts cc_potential
                        WHERE cc_potential.lead_id = lm.lead_id
                          AND cc_potential.active_status = 'active'
                    ) = 0
                )
            )
            """
        )
        return

    if category == "customer":
        where_clauses.append("lm.lead_category = 'customer'")
        return


def normalize_contact_row(row: Dict[str, Any]) -> Dict[str, Any]:
    social_network = parse_json_value(row.get("social_network"))
    source_details = parse_json_value(row.get("source_details"))

    if not isinstance(social_network, dict):
        social_network = {}

    return {
        "contact_id": row.get("contact_id"),
        "name": f"{str(row.get('first_name') or '').strip()} {str(row.get('last_name') or '').strip()}".strip(),
        "email": row.get("email"),
        "phone": format_phone(row.get("primary_phone")),
        "whatsapp": format_phone(row.get("whatsappno")),
        "alternative_phone": format_phone(row.get("alternative_phone")),
        "alternative_emails": row.get("alternative_emails"),
        "social_network": social_network,
        "address": row.get("address"),
        "city": row.get("city"),
        "state": row.get("state"),
        "country": row.get("country"),
        "zipcode": row.get("zipcode"),
        "avatar": row.get("avater_url"),
        "department": row.get("department"),
        "designation": row.get("designation"),
        "source": source_label(row.get("source")),
        "source_details": source_details,
        "owner": user_info(row, "owner"),
        "created_by": user_info(row, "created_by"),
        "created_date": convert_datetime_to_utc(
            row.get("created_date"),
            row.get("timezone"),
        ),
        "modified_by": user_info(row, "modified_by"),
        "modified_date": convert_datetime_to_utc(
            row.get("modified_date"),
            row.get("timezone"),
        ),
        "notes": row.get("notes"),
    }


def fetch_contacts_for_accounts(
    client_database: str,
    account_ids: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    if not account_ids:
        return {}

    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    try:
        connection = get_client_connection(client_database)

        placeholders = ",".join(["%s"] * len(account_ids))

        with connection.cursor() as cursor:
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
                    cc.notes,

                    owner_user.first_name AS owner_first_name,
                    owner_user.last_name AS owner_last_name,
                    owner_user.email AS owner_email,

                    created_user.first_name AS created_by_first_name,
                    created_user.last_name AS created_by_last_name,
                    created_user.email AS created_by_email,

                    modified_user.first_name AS modified_by_first_name,
                    modified_user.last_name AS modified_by_last_name,
                    modified_user.email AS modified_by_email

                FROM lk_central_contacts cc

                LEFT JOIN `{master_database}`.zp_users owner_user
                    ON owner_user.id = cc.owner

                LEFT JOIN `{master_database}`.zp_users created_user
                    ON created_user.id = cc.created_by

                LEFT JOIN `{master_database}`.zp_users modified_user
                    ON modified_user.id = cc.modified_by

                WHERE cc.lead_id IN ({placeholders})
                  AND cc.active_status = 'active'

                ORDER BY cc.modified_date DESC, cc.created_date DESC
            """

            cursor.execute(sql, tuple(account_ids))
            rows = cursor.fetchall()

        contacts_by_account: Dict[int, List[Dict[str, Any]]] = {}

        for row in rows:
            lead_id = int(row.get("lead_id"))

            if lead_id not in contacts_by_account:
                contacts_by_account[lead_id] = []

            contacts_by_account[lead_id].append(normalize_contact_row(row))

        return contacts_by_account

    finally:
        if connection:
            connection.close()


def normalize_account_row(row: Dict[str, Any]) -> Dict[str, Any]:
    social_network = parse_json_value(row.get("social_network"))
    source_details = parse_json_value(row.get("source_details"))

    if not isinstance(social_network, dict):
        social_network = {}

    active_contact_count = int(row.get("active_contact_count") or 0)

    return {
        "account_id": row.get("account_id"),
        "account_name": row.get("account_name"),
        "lead_segment": row.get("lead_segment"),
        "lead_category": computed_lead_category(
            row.get("lead_category"),
            active_contact_count,
        ),
        "contact_count": active_contact_count,
        "lead_type": row.get("lead_type"),
        "lead_status": row.get("lead_status_name"),
        "status_change_date": convert_datetime_to_utc(
            row.get("status_change_date"),
            row.get("timezone"),
        ),
        "website": row.get("website"),
        "email": row.get("email"),
        "phone": format_phone(row.get("phone")),
        "lead_description": row.get("lead_description"),
        "employee_count": format_employee_count(
            row.get("employee_lower_range"),
            row.get("employee_upper_range"),
        ),
        "industry": row.get("industry"),
        "address": row.get("address"),
        "city": row.get("city"),
        "state": row.get("state"),
        "country": row.get("country"),
        "zipcode": row.get("zipcode"),
        "social_network": social_network,
        "previous_crm_used": row.get("crm"),
        "previous_email_marketing_used": row.get("email_marketing"),
        "previous_website_analytics_used": row.get("website_analytics"),
        "owner": user_info(row, "owner"),
        "created_by": user_info(row, "created_by"),
        "created_date": convert_datetime_to_utc(
            row.get("created_date"),
            row.get("timezone"),
        ),
        "modified_by": user_info(row, "modified_by"),
        "modified_date": convert_datetime_to_utc(
            row.get("modified_date"),
            row.get("timezone"),
        ),
        "source": source_label(row.get("source")),
        "lead_source": row.get("lead_source"),
        "lead_typeevent": row.get("lead_typeevent"),
        "lead_attendees": row.get("lead_attendees"),
        "project_startdate": str(row.get("project_startdate")) if row.get("project_startdate") else None,
        "project_enddate": str(row.get("project_enddate")) if row.get("project_enddate") else None,
        "source_details": source_details,
        "timezone": row.get("timezone"),
    }


def build_publish_status_condition(
    lead_publish_status: str,
    where_clauses: List[str],
) -> None:
    status_value = str(lead_publish_status or "active").strip().lower()

    if status_value == "all":
        return

    if status_value == "archive":
        where_clauses.append("lm.active_status = 'archived'")
        return

    where_clauses.append("lm.active_status = 'active'")


def build_dynamic_filters(filters: Optional[List[Dict[str, Any]]]) -> Tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []

    if not filters:
        return where_clauses, params

    for item in filters:
        field = str(item.get("field") or "").strip()
        operator = str(item.get("operator") or "eq").strip().lower()
        value = item.get("value")

        if field not in ALLOWED_FILTER_FIELDS:
            continue

        column = ALLOWED_FILTER_FIELDS[field]

        if operator == "eq":
            where_clauses.append(f"{column} = %s")
            params.append(value)

        elif operator == "neq":
            where_clauses.append(f"{column} <> %s")
            params.append(value)

        elif operator == "like":
            where_clauses.append(f"{column} LIKE %s")
            params.append(f"%{value}%")

        elif operator == "starts_with":
            where_clauses.append(f"{column} LIKE %s")
            params.append(f"{value}%")

        elif operator == "ends_with":
            where_clauses.append(f"{column} LIKE %s")
            params.append(f"%{value}")

        elif operator == "in" and isinstance(value, list) and value:
            placeholders = ",".join(["%s"] * len(value))
            where_clauses.append(f"{column} IN ({placeholders})")
            params.extend(value)

        elif operator == "from":
            where_clauses.append(f"{column} >= %s")
            params.append(value)

        elif operator == "to":
            where_clauses.append(f"{column} <= %s")
            params.append(value)

    return where_clauses, params


def fetch_account_dynamic_details(
    client_database: str,
    account_ids: List[int],
) -> Dict[int, Dict[str, Any]]:
    if not account_ids:
        return {}

    connection = None

    try:
        connection = get_client_connection(client_database)

        placeholders = ",".join(["%s"] * len(account_ids))

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    lead_id,
                    field_name,
                    field_value
                FROM lk_lead_details
                WHERE lead_id IN ({placeholders})
                  AND field_name IS NOT NULL
                  AND field_name <> ''
            """

            cursor.execute(sql, tuple(account_ids))
            rows = cursor.fetchall()

        details: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            lead_id = int(row.get("lead_id"))
            field_name = row.get("field_name")
            field_value = row.get("field_value")

            if lead_id not in details:
                details[lead_id] = {}

            details[lead_id][field_name] = field_value

        return details

    finally:
        if connection:
            connection.close()


def fetch_accounts(
    client_database: str,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    lead_publish_status: str = "active",
    computed_lead_category: str = "all",
    filters: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    connection = None

    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    master_database = validate_database_name(settings.MASTER_DB_NAME)

    where_clauses = [
        "lm.status = 'published'"
    ]

    params: List[Any] = []

    build_publish_status_condition(lead_publish_status, where_clauses)
    build_computed_lead_category_condition(computed_lead_category, where_clauses)

    if search:
        where_clauses.append(
            """
            (
                lm.lead_name LIKE %s
                OR lm.website LIKE %s
                OR lm.email LIKE %s
                OR lm.phone LIKE %s
                OR lm.industry LIKE %s
                OR lm.city LIKE %s
                OR lm.state LIKE %s
                OR lm.country LIKE %s
                OR lm.lead_source LIKE %s
            )
            """
        )

        search_value = f"%{search}%"
        params.extend([search_value] * 9)

    dynamic_where, dynamic_params = build_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    lm.lead_id AS account_id,
                    lm.lead_name AS account_name,
                    lm.lead_segment,
                    lm.lead_category,
                    (
                        SELECT COUNT(*)
                        FROM lk_central_contacts cc_count
                        WHERE cc_count.lead_id = lm.lead_id
                          AND cc_count.active_status = 'active'
                    ) AS active_contact_count,
                    lm.lead_type,
                    lm.lead_persuing_status AS lead_status_id,
                    lsm.lead_status_name,
                    lsm.lead_status_code,
                    lm.status_change_date,
                    lm.website,
                    lm.email,
                    lm.phone,
                    lm.lead_description,
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
                    lm.lead_source,
                    lm.lead_typeevent,
                    lm.lead_attendees,
                    lm.project_startdate,
                    lm.project_enddate,
                    lm.source_details,

                    owner_user.first_name AS owner_first_name,
                    owner_user.last_name AS owner_last_name,
                    owner_user.email AS owner_email,

                    created_user.first_name AS created_by_first_name,
                    created_user.last_name AS created_by_last_name,
                    created_user.email AS created_by_email,

                    modified_user.first_name AS modified_by_first_name,
                    modified_user.last_name AS modified_by_last_name,
                    modified_user.email AS modified_by_email

                FROM lk_lead_master lm

                LEFT JOIN lk_lead_status_master lsm
                    ON lsm.lead_status_id = lm.lead_persuing_status
                   AND lsm.active_status = 'active'

                LEFT JOIN `{master_database}`.zp_users owner_user
                    ON owner_user.id = lm.owner

                LEFT JOIN `{master_database}`.zp_users created_user
                    ON created_user.id = lm.created_by

                LEFT JOIN `{master_database}`.zp_users modified_user
                    ON modified_user.id = lm.modified_by

                WHERE {where_sql}

                ORDER BY lm.modified_date DESC, lm.created_date DESC
                LIMIT %s OFFSET %s
            """

            params.extend([limit, offset])
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        return [normalize_account_row(row) for row in rows]

    finally:
        if connection:
            connection.close()


def count_accounts(
    client_database: str,
    search: Optional[str] = None,
    lead_publish_status: str = "active",
    computed_lead_category: str = "all",
    filters: Optional[List[Dict[str, Any]]] = None,
) -> int:
    connection = None

    where_clauses = [
        "lm.status = 'published'"
    ]

    params: List[Any] = []

    build_publish_status_condition(lead_publish_status, where_clauses)
    build_computed_lead_category_condition(computed_lead_category, where_clauses)

    if search:
        where_clauses.append(
            """
            (
                lm.lead_name LIKE %s
                OR lm.website LIKE %s
                OR lm.email LIKE %s
                OR lm.phone LIKE %s
                OR lm.industry LIKE %s
                OR lm.city LIKE %s
                OR lm.state LIKE %s
                OR lm.country LIKE %s
                OR lm.lead_source LIKE %s
            )
            """
        )

        search_value = f"%{search}%"
        params.extend([search_value] * 9)

    dynamic_where, dynamic_params = build_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT COUNT(*) AS total_records
                FROM lk_lead_master lm

                LEFT JOIN lk_lead_status_master lsm
                    ON lsm.lead_status_id = lm.lead_persuing_status
                   AND lsm.active_status = 'active'

                WHERE {where_sql}
            """

            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        return int(row.get("total_records", 0))

    finally:
        if connection:
            connection.close()

def fetch_account_by_id(
    client_database: str,
    account_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    lm.lead_id AS account_id,
                    lm.lead_name AS account_name,
                    lm.lead_segment,
                    lm.lead_category,
                    (
                        SELECT COUNT(*)
                        FROM lk_central_contacts cc_count
                        WHERE cc_count.lead_id = lm.lead_id
                          AND cc_count.active_status = 'active'
                    ) AS active_contact_count,
                    lm.lead_type,
                    lm.lead_persuing_status AS lead_status_id,
                    lsm.lead_status_name,
                    lsm.lead_status_code,
                    lm.status_change_date,
                    lm.website,
                    lm.email,
                    lm.phone,
                    lm.lead_description,
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
                    lm.lead_source,
                    lm.lead_typeevent,
                    lm.lead_attendees,
                    lm.project_startdate,
                    lm.project_enddate,
                    lm.source_details,

                    owner_user.first_name AS owner_first_name,
                    owner_user.last_name AS owner_last_name,
                    owner_user.email AS owner_email,

                    created_user.first_name AS created_by_first_name,
                    created_user.last_name AS created_by_last_name,
                    created_user.email AS created_by_email,

                    modified_user.first_name AS modified_by_first_name,
                    modified_user.last_name AS modified_by_last_name,
                    modified_user.email AS modified_by_email

                FROM lk_lead_master lm

                LEFT JOIN lk_lead_status_master lsm
                    ON lsm.lead_status_id = lm.lead_persuing_status
                   AND lsm.active_status = 'active'

                LEFT JOIN `{master_database}`.zp_users owner_user
                    ON owner_user.id = lm.owner

                LEFT JOIN `{master_database}`.zp_users created_user
                    ON created_user.id = lm.created_by

                LEFT JOIN `{master_database}`.zp_users modified_user
                    ON modified_user.id = lm.modified_by

                WHERE lm.lead_id = %s
                  AND lm.status = 'published'
                LIMIT 1
            """

            cursor.execute(sql, (account_id,))
            row = cursor.fetchone()

        if not row:
            return None

        account = normalize_account_row(row)

        dynamic_details = fetch_account_dynamic_details(
            client_database=client_database,
            account_ids=[account_id],
        )

        contacts_by_account = fetch_contacts_for_accounts(
            client_database=client_database,
            account_ids=[account_id],
        )

        account["dynamic_fields"] = dynamic_details.get(account_id, {})
        account["contacts"] = contacts_by_account.get(account_id, [])

        return account

    finally:
        if connection:
            connection.close()