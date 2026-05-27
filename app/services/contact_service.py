from typing import Any, Dict, List, Optional

from app.config import settings
from app.db.client import get_client_connection, validate_database_name
from app.services.account_service import (
    normalize_contact_row,
    normalize_account_row,
    parse_json_value,
)


CONTACT_SEARCH_FIELDS = {
    "name": ["cc.first_name", "cc.last_name"],
    "first_name": ["cc.first_name"],
    "last_name": ["cc.last_name"],
    "email": ["cc.email"],
    "phone": ["cc.primary_phone"],
    "whatsapp": ["cc.whatsappno"],
    "alternative_phone": ["cc.alternative_phone"],
    "alternative_emails": ["cc.alternative_emails"],
    "address": ["cc.address"],
    "city": ["cc.city"],
    "state": ["cc.state"],
    "country": ["cc.country"],
    "zipcode": ["cc.zipcode"],
    "department": ["cc.department"],
    "designation": ["cc.designation"],
    "contact_type": ["cc.contact_type"],
    "source": ["cc.source"],
    "owner": ["cc.owner"],
    "created_by": ["cc.created_by"],
    "modified_by": ["cc.modified_by"],
}


MULTI_VALUE_CONTACT_SEARCH_FIELDS = {
    "contact_type",
    "country",
    "state",
    "city",
    "source",
    "owner",
    "created_by",
    "modified_by",
}

def split_contact_search_values(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    value_string = str(value).strip()

    if not value_string:
        return []

    try:
        import json
        parsed = json.loads(value_string)

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass

    return [item.strip() for item in value_string.split(",") if item.strip()]


def build_contact_in_condition(
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


def normalize_numeric_values(values: List[str]) -> List[int]:
    numeric_values = []

    for value in values:
        try:
            numeric_values.append(int(value))
        except Exception:
            pass

    return numeric_values

def build_contact_search_condition(
    search: Optional[str],
    search_by: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not search:
        return

    search_by_value = str(search_by or "").strip().lower()
    search_value = f"%{search}%"

    # General search if search_by is not provided
    if not search_by_value:
        where_clauses.append(
            """
            (
                cc.first_name LIKE %s
                OR cc.last_name LIKE %s
                OR CONCAT(COALESCE(cc.first_name, ''), ' ', COALESCE(cc.last_name, '')) LIKE %s
                OR cc.email LIKE %s
                OR cc.primary_phone LIKE %s
                OR cc.whatsappno LIKE %s
                OR cc.alternative_phone LIKE %s
                OR cc.alternative_emails LIKE %s
                OR cc.address LIKE %s
                OR cc.city LIKE %s
                OR cc.state LIKE %s
                OR cc.country LIKE %s
                OR cc.zipcode LIKE %s
                OR cc.department LIKE %s
                OR cc.designation LIKE %s
                OR cc.contact_type LIKE %s
                OR cc.source LIKE %s
            )
            """
        )

        params.extend([search_value] * 17)
        return

    if search_by_value not in CONTACT_SEARCH_FIELDS:
        return

    values = split_contact_search_values(search)

    if not values:
        return

    # Name search
    if search_by_value == "name":
        where_clauses.append(
            """
            (
                cc.first_name LIKE %s
                OR cc.last_name LIKE %s
                OR CONCAT(COALESCE(cc.first_name, ''), ' ', COALESCE(cc.last_name, '')) LIKE %s
            )
            """
        )
        params.extend([f"%{values[0]}%", f"%{values[0]}%", f"%{values[0]}%"])
        return

    # Owner / Created By / Modified By: one or multiple user IDs
    if search_by_value in ["owner", "created_by", "modified_by"]:
        numeric_values = normalize_numeric_values(values)

        if not numeric_values:
            return

        column = CONTACT_SEARCH_FIELDS[search_by_value][0]
        build_contact_in_condition(column, numeric_values, where_clauses, params)
        return

    # Multi-value exact fields
    if search_by_value in MULTI_VALUE_CONTACT_SEARCH_FIELDS:
        column = CONTACT_SEARCH_FIELDS[search_by_value][0]
        build_contact_in_condition(column, values, where_clauses, params)
        return

    # Single field text search
    columns = CONTACT_SEARCH_FIELDS[search_by_value]

    column_conditions = []

    for column in columns:
        column_conditions.append(f"{column} LIKE %s")
        params.append(f"%{values[0]}%")

    where_clauses.append("(" + " OR ".join(column_conditions) + ")")


def normalize_contact_with_account(row: Dict[str, Any]) -> Dict[str, Any]:
    contact = normalize_contact_row(row)

    contact["contact_type"] = row.get("contact_type")

    account_row = {
        "account_id": row.get("account_id"),
        "account_name": row.get("account_name"),
        "lead_segment": row.get("account_lead_segment"),
        "lead_category": row.get("account_lead_category"),
        "active_contact_count": row.get("account_active_contact_count"),
        "lead_type": row.get("account_lead_type"),
        "lead_status_name": row.get("account_lead_status_name"),
        "status_change_date": row.get("account_status_change_date"),
        "website": row.get("account_website"),
        "email": row.get("account_email"),
        "phone": row.get("account_phone"),
        "lead_description": row.get("account_lead_description"),
        "employee_lower_range": row.get("account_employee_lower_range"),
        "employee_upper_range": row.get("account_employee_upper_range"),
        "industry": row.get("account_industry"),
        "address": row.get("account_address"),
        "city": row.get("account_city"),
        "state": row.get("account_state"),
        "country": row.get("account_country"),
        "zipcode": row.get("account_zipcode"),
        "social_network": row.get("account_social_network"),
        "crm": row.get("account_crm"),
        "email_marketing": row.get("account_email_marketing"),
        "website_analytics": row.get("account_website_analytics"),
        "timezone": row.get("account_timezone"),
        "source": row.get("account_source"),
        "lead_source": row.get("account_lead_source"),
        "lead_typeevent": row.get("account_lead_typeevent"),
        "lead_attendees": row.get("account_lead_attendees"),
        "project_startdate": row.get("account_project_startdate"),
        "project_enddate": row.get("account_project_enddate"),
        "source_details": row.get("account_source_details"),

        "owner_first_name": row.get("account_owner_first_name"),
        "owner_last_name": row.get("account_owner_last_name"),
        "owner_email": row.get("account_owner_email"),

        "created_by_first_name": row.get("account_created_by_first_name"),
        "created_by_last_name": row.get("account_created_by_last_name"),
        "created_by_email": row.get("account_created_by_email"),

        "created_date": row.get("account_created_date"),

        "modified_by_first_name": row.get("account_modified_by_first_name"),
        "modified_by_last_name": row.get("account_modified_by_last_name"),
        "modified_by_email": row.get("account_modified_by_email"),

        "modified_date": row.get("account_modified_date"),
    }

    contact["account"] = normalize_account_row(account_row) if row.get("account_id") else None

    return contact


def fetch_contact_dynamic_details(
    client_database: str,
    contact_ids: List[int],
) -> Dict[int, Dict[str, Any]]:
    if not contact_ids:
        return {}

    connection = None

    try:
        connection = get_client_connection(client_database)
        placeholders = ",".join(["%s"] * len(contact_ids))

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    contact_id,
                    field_type,
                    field_name,
                    field_details
                FROM lk_central_contacts_details
                WHERE contact_id IN ({placeholders})
                  AND field_name IS NOT NULL
                  AND field_name <> ''
            """
            cursor.execute(sql, tuple(contact_ids))
            rows = cursor.fetchall()

        details: Dict[int, Dict[str, Any]] = {}

        for row in rows:
            contact_id = int(row.get("contact_id"))
            field_name = row.get("field_name")
            field_details = row.get("field_details")

            if contact_id not in details:
                details[contact_id] = {}

            details[contact_id][field_name] = parse_json_value(field_details)

        return details

    finally:
        if connection:
            connection.close()


def fetch_contacts(
    client_database: str,
    limit: int = 50,
    offset: int = 0,
    account_id: Optional[int] = None,
    account_search: Optional[str] = None,
    associated_accounts_only: bool = False,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    where_clauses = [
        "cc.active_status = 'active'"
    ]

    params: List[Any] = []

    if account_id:
        where_clauses.append("cc.lead_id = %s")
        params.append(account_id)

    if associated_accounts_only:
        where_clauses.append("cc.lead_id IS NOT NULL")
        where_clauses.append("cc.lead_id > 0")

    if account_search:
        where_clauses.append(
            """
            (
                lm.lead_id = %s
                OR lm.lead_name LIKE %s
                OR lm.website LIKE %s
            )
            """
        )

        account_search_like = f"%{account_search}%"

        try:
            account_search_id = int(account_search)
        except Exception:
            account_search_id = 0

        params.extend([
            account_search_id,
            account_search_like,
            account_search_like,
        ])

    build_contact_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    cc.contact_id,
                    cc.lead_id,
                    cc.contact_type,
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
                    modified_user.email AS modified_by_email,

                    lm.lead_id AS account_id,
                    lm.lead_name AS account_name,
                    lm.lead_segment AS account_lead_segment,
                    lm.lead_category AS account_lead_category,
                    (
                        SELECT COUNT(*)
                        FROM lk_central_contacts cc_count
                        WHERE cc_count.lead_id = lm.lead_id
                          AND cc_count.active_status = 'active'
                    ) AS account_active_contact_count,
                    lm.lead_type AS account_lead_type,
                    lsm.lead_status_name AS account_lead_status_name,
                    lm.status_change_date AS account_status_change_date,
                    lm.website AS account_website,
                    lm.email AS account_email,
                    lm.phone AS account_phone,
                    lm.lead_description AS account_lead_description,
                    lm.employee_lower_range AS account_employee_lower_range,
                    lm.employee_upper_range AS account_employee_upper_range,
                    lm.industry AS account_industry,
                    lm.address AS account_address,
                    lm.city AS account_city,
                    lm.state AS account_state,
                    lm.country AS account_country,
                    lm.zipcode AS account_zipcode,
                    lm.social_network AS account_social_network,
                    lm.crm AS account_crm,
                    lm.email_marketing AS account_email_marketing,
                    lm.website_analytics AS account_website_analytics,
                    lm.timezone AS account_timezone,
                    lm.source AS account_source,
                    lm.lead_source AS account_lead_source,
                    lm.lead_typeevent AS account_lead_typeevent,
                    lm.lead_attendees AS account_lead_attendees,
                    lm.project_startdate AS account_project_startdate,
                    lm.project_enddate AS account_project_enddate,
                    lm.source_details AS account_source_details,
                    lm.created_date AS account_created_date,
                    lm.modified_date AS account_modified_date,

                    account_owner.first_name AS account_owner_first_name,
                    account_owner.last_name AS account_owner_last_name,
                    account_owner.email AS account_owner_email,

                    account_created_user.first_name AS account_created_by_first_name,
                    account_created_user.last_name AS account_created_by_last_name,
                    account_created_user.email AS account_created_by_email,

                    account_modified_user.first_name AS account_modified_by_first_name,
                    account_modified_user.last_name AS account_modified_by_last_name,
                    account_modified_user.email AS account_modified_by_email

                FROM lk_central_contacts cc

                LEFT JOIN lk_lead_master lm
                    ON lm.lead_id = cc.lead_id

                LEFT JOIN lk_lead_status_master lsm
                    ON lsm.lead_status_id = lm.lead_persuing_status
                   AND lsm.active_status = 'active'

                LEFT JOIN `{master_database}`.zp_users owner_user
                    ON owner_user.id = cc.owner

                LEFT JOIN `{master_database}`.zp_users created_user
                    ON created_user.id = cc.created_by

                LEFT JOIN `{master_database}`.zp_users modified_user
                    ON modified_user.id = cc.modified_by

                LEFT JOIN `{master_database}`.zp_users account_owner
                    ON account_owner.id = lm.owner

                LEFT JOIN `{master_database}`.zp_users account_created_user
                    ON account_created_user.id = lm.created_by

                LEFT JOIN `{master_database}`.zp_users account_modified_user
                    ON account_modified_user.id = lm.modified_by

                WHERE {where_sql}

                ORDER BY cc.modified_date DESC, cc.created_date DESC
                LIMIT %s OFFSET %s
            """

            params.extend([limit, offset])
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        contacts = [normalize_contact_with_account(row) for row in rows]

        contact_ids = [
            int(contact["contact_id"])
            for contact in contacts
            if contact.get("contact_id")
        ]

        dynamic_details = fetch_contact_dynamic_details(
            client_database=client_database,
            contact_ids=contact_ids,
        )

        for contact in contacts:
            contact_id = int(contact["contact_id"])
            contact["dynamic_fields"] = dynamic_details.get(contact_id, {})

        return contacts

    finally:
        if connection:
            connection.close()


def count_contacts(
    client_database: str,
    account_id: Optional[int] = None,
    account_search: Optional[str] = None,
    associated_accounts_only: bool = False,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
) -> int:
    connection = None

    where_clauses = [
        "cc.active_status = 'active'"
    ]

    params: List[Any] = []

    if account_id:
        where_clauses.append("cc.lead_id = %s")
        params.append(account_id)

    if associated_accounts_only:
        where_clauses.append("cc.lead_id IS NOT NULL")
        where_clauses.append("cc.lead_id > 0")

    if account_search:
        where_clauses.append(
            """
            (
                lm.lead_id = %s
                OR lm.lead_name LIKE %s
                OR lm.website LIKE %s
            )
            """
        )

        account_search_like = f"%{account_search}%"

        try:
            account_search_id = int(account_search)
        except Exception:
            account_search_id = 0

        params.extend([
            account_search_id,
            account_search_like,
            account_search_like,
        ])

    build_contact_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT COUNT(*) AS total_records
                FROM lk_central_contacts cc

                LEFT JOIN lk_lead_master lm
                    ON lm.lead_id = cc.lead_id

                WHERE {where_sql}
            """

            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        return int(row.get("total_records", 0))

    finally:
        if connection:
            connection.close()

def fetch_contact_by_id(
    client_database: str,
    contact_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    cc.contact_id,
                    cc.lead_id,
                    cc.contact_type,
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
                    modified_user.email AS modified_by_email,

                    lm.lead_id AS account_id,
                    lm.lead_name AS account_name,
                    lm.lead_segment AS account_lead_segment,
                    lm.lead_category AS account_lead_category,
                    (
                        SELECT COUNT(*)
                        FROM lk_central_contacts cc_count
                        WHERE cc_count.lead_id = lm.lead_id
                          AND cc_count.active_status = 'active'
                    ) AS account_active_contact_count,
                    lm.lead_type AS account_lead_type,
                    lsm.lead_status_name AS account_lead_status_name,
                    lm.status_change_date AS account_status_change_date,
                    lm.website AS account_website,
                    lm.email AS account_email,
                    lm.phone AS account_phone,
                    lm.lead_description AS account_lead_description,
                    lm.employee_lower_range AS account_employee_lower_range,
                    lm.employee_upper_range AS account_employee_upper_range,
                    lm.industry AS account_industry,
                    lm.address AS account_address,
                    lm.city AS account_city,
                    lm.state AS account_state,
                    lm.country AS account_country,
                    lm.zipcode AS account_zipcode,
                    lm.social_network AS account_social_network,
                    lm.crm AS account_crm,
                    lm.email_marketing AS account_email_marketing,
                    lm.website_analytics AS account_website_analytics,
                    lm.timezone AS account_timezone,
                    lm.source AS account_source,
                    lm.lead_source AS account_lead_source,
                    lm.lead_typeevent AS account_lead_typeevent,
                    lm.lead_attendees AS account_lead_attendees,
                    lm.project_startdate AS account_project_startdate,
                    lm.project_enddate AS account_project_enddate,
                    lm.source_details AS account_source_details,
                    lm.created_date AS account_created_date,
                    lm.modified_date AS account_modified_date,

                    account_owner.first_name AS account_owner_first_name,
                    account_owner.last_name AS account_owner_last_name,
                    account_owner.email AS account_owner_email,

                    account_created_user.first_name AS account_created_by_first_name,
                    account_created_user.last_name AS account_created_by_last_name,
                    account_created_user.email AS account_created_by_email,

                    account_modified_user.first_name AS account_modified_by_first_name,
                    account_modified_user.last_name AS account_modified_by_last_name,
                    account_modified_user.email AS account_modified_by_email

                FROM lk_central_contacts cc

                LEFT JOIN lk_lead_master lm
                    ON lm.lead_id = cc.lead_id

                LEFT JOIN lk_lead_status_master lsm
                    ON lsm.lead_status_id = lm.lead_persuing_status
                   AND lsm.active_status = 'active'

                LEFT JOIN `{master_database}`.zp_users owner_user
                    ON owner_user.id = cc.owner

                LEFT JOIN `{master_database}`.zp_users created_user
                    ON created_user.id = cc.created_by

                LEFT JOIN `{master_database}`.zp_users modified_user
                    ON modified_user.id = cc.modified_by

                LEFT JOIN `{master_database}`.zp_users account_owner
                    ON account_owner.id = lm.owner

                LEFT JOIN `{master_database}`.zp_users account_created_user
                    ON account_created_user.id = lm.created_by

                LEFT JOIN `{master_database}`.zp_users account_modified_user
                    ON account_modified_user.id = lm.modified_by

                WHERE cc.contact_id = %s
                  AND cc.active_status = 'active'

                LIMIT 1
            """

            cursor.execute(sql, (contact_id,))
            row = cursor.fetchone()

        if not row:
            return None

        contact = normalize_contact_with_account(row)

        dynamic_details = fetch_contact_dynamic_details(
            client_database=client_database,
            contact_ids=[contact_id],
        )

        contact["dynamic_fields"] = dynamic_details.get(contact_id, {})

        return contact

    finally:
        if connection:
            connection.close()