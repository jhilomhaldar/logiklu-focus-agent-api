from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection, validate_database_name
from app.services.accounts_service import (
    normalize_contact_row,
    normalize_account_row,
    parse_json_value,
    fetch_users,
    fetch_account_assignments,
    build_assigned_users,
    build_account_activities,
    get_user,
    format_datetime,
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


def build_contact_dynamic_filters(
    filters: Optional[List[Dict[str, Any]]],
) -> Tuple[List[str], List[Any]]:
    where_clauses: List[str] = []
    params: List[Any] = []

    if not filters:
        return where_clauses, params

    for item in filters:
        field = str(item.get("field") or "").strip().lower()
        operator = str(item.get("operator") or "eq").strip().lower()
        value = item.get("value")

        if field not in CONTACT_SEARCH_FIELDS:
            continue

        columns = CONTACT_SEARCH_FIELDS[field]

        if not columns:
            continue

        # Name searches first_name, last_name, and full name
        if field == "name":
            if operator == "like":
                where_clauses.append(
                    """
                    (
                        cc.first_name LIKE %s
                        OR cc.last_name LIKE %s
                        OR CONCAT(COALESCE(cc.first_name, ''), ' ', COALESCE(cc.last_name, '')) LIKE %s
                    )
                    """
                )
                params.extend([f"%{value}%", f"%{value}%", f"%{value}%"])

            elif operator == "eq":
                where_clauses.append(
                    """
                    CONCAT(COALESCE(cc.first_name, ''), ' ', COALESCE(cc.last_name, '')) = %s
                    """
                )
                params.append(value)

            continue

        column = columns[0]

        if operator == "eq":
            where_clauses.append(f"{column} = %s")
            params.append(value)

        elif operator == "neq":
            where_clauses.append(f"{column} <> %s")
            params.append(value)

        elif operator == "like":
            column_conditions = []

            for col in columns:
                column_conditions.append(f"{col} LIKE %s")
                params.append(f"%{value}%")

            where_clauses.append("(" + " OR ".join(column_conditions) + ")")

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


def make_placeholders(values: List[Any]) -> str:
    return ",".join(["%s"] * len(values))


def to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def unique_ints(values: List[Any]) -> List[int]:
    output: List[int] = []
    seen = set()

    for value in values:
        parsed = to_int(value)

        if parsed is None or parsed <= 0 or parsed in seen:
            continue

        seen.add(parsed)
        output.append(parsed)

    return output


def fetch_contact_activity_rows(
    connection: Any,
    contact_ids: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    """Fetch contact-linked notes, attachments and activities.

    Mapping rule:
    - lk_activity_contacts.contact_role = 'contact'
    - lk_activity_contacts.contact_id = lk_central_contacts.contact_id
    - lk_activity_schedule.activity_type decides note / attachment / activity
    """
    ids = unique_ints(contact_ids)

    if not ids:
        return {}

    sql = f"""
        SELECT
            lac.contact_id,
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
            las.status,
            las.active_status
        FROM lk_activity_contacts lac
        INNER JOIN lk_activity_schedule las
            ON las.activity_id = lac.activity_id
        WHERE lac.contact_id IN ({make_placeholders(ids)})
          AND lac.contact_role = 'contact'
          AND lac.contact_id IS NOT NULL
          AND lac.contact_id > 0
          AND (las.active_status IS NULL OR las.active_status <> 'deleted')
        ORDER BY lac.contact_id ASC, las.created_date ASC, las.activity_id ASC
    """

    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, ids)
        rows = cursor.fetchall()

    for row in rows:
        contact_id = to_int(row.get("contact_id"))

        if contact_id is None:
            continue

        output.setdefault(contact_id, []).append(row)

    return output




def split_id_values(value: Any) -> List[int]:
    if value is None:
        return []

    if isinstance(value, list):
        return unique_ints(value)

    value_string = str(value or "").strip()

    if not value_string:
        return []

    try:
        import json
        parsed = json.loads(value_string)

        if isinstance(parsed, list):
            return unique_ints(parsed)
    except Exception:
        pass

    cleaned = value_string.replace(" ", "")
    return unique_ints([part for part in cleaned.split(",") if part])


def fetch_contact_deal_rows(
    connection: Any,
    contact_ids: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    """Fetch deals linked to contacts.

    Deal-contact rule:
    - lk_opportunities.lead_contact_id = contact_id
    - OR contact_id appears in lk_opportunities.contact_ids
    """
    ids = unique_ints(contact_ids)

    if not ids:
        return {}

    find_conditions = []
    find_params: List[Any] = []

    for contact_id in ids:
        find_conditions.append("FIND_IN_SET(%s, REPLACE(IFNULL(o.contact_ids, ''), ' ', '')) > 0")
        find_params.append(str(contact_id))

    sql = f"""
        SELECT
            o.opportunity_id AS deal_id,
            o.lead_contact_id,
            o.contact_ids,
            o.lead_id,
            o.opportunity_name AS deal_name,
            o.opportunity_description AS deal_description,
            o.opportunity_type AS deal_type,
            o.closingdate AS closing_date,
            o.owner,
            o.created_by,
            o.created_date,
            o.modified_by,
            o.modified_date,
            o.status,
            o.oportunity_status AS deal_status,
            o.active_status,

            lm.lead_id AS account_id,
            lm.lead_name AS account_name,
            lm.lead_type AS account_type,
            lm.city AS account_city,
            lm.state AS account_state,
            lm.country AS account_country,

            status_action.id AS deal_stage_id,
            status_action.title AS deal_stage_title,
            status_action.color AS deal_stage_color
        FROM lk_opportunities o
        LEFT JOIN lk_lead_master lm
            ON lm.lead_id = o.lead_id
        LEFT JOIN jos_setting_sales_executive_action status_action
            ON status_action.id = o.opportunity_status_id
           AND status_action.section = 'STATUS'
        WHERE (
                o.lead_contact_id IN ({make_placeholders(ids)})
                OR ({" OR ".join(find_conditions)})
              )
          AND (o.active_status IS NULL OR o.active_status <> 'deleted')
        ORDER BY o.created_date ASC, o.opportunity_id ASC
    """

    params: List[Any] = list(ids) + find_params
    output: Dict[int, List[Dict[str, Any]]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    id_set = set(ids)

    for row in rows:
        linked_contact_ids: List[int] = []

        lead_contact_id = to_int(row.get("lead_contact_id"))

        if lead_contact_id is not None and lead_contact_id in id_set:
            linked_contact_ids.append(lead_contact_id)

        for linked_id in split_id_values(row.get("contact_ids")):
            if linked_id in id_set:
                linked_contact_ids.append(linked_id)

        linked_contact_ids = unique_ints(linked_contact_ids)

        for linked_id in linked_contact_ids:
            output.setdefault(linked_id, []).append(row)

    return output


def build_deal_stage(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not row.get("deal_stage_id"):
        return None

    return {
        "id": row.get("deal_stage_id"),
        "title": row.get("deal_stage_title"),
        "color": row.get("deal_stage_color"),
    }


def build_contact_deals(
    rows: List[Dict[str, Any]],
    user_map: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    deals: List[Dict[str, Any]] = []
    seen = set()

    for row in rows:
        deal_id = to_int(row.get("deal_id"))

        if deal_id is None or deal_id in seen:
            continue

        seen.add(deal_id)

        account = None
        if row.get("account_id"):
            account = {
                "account_id": row.get("account_id"),
                "name": row.get("account_name"),
                "account_type": row.get("account_type"),
                "location": {
                    "city": row.get("account_city"),
                    "state": row.get("account_state"),
                    "country": row.get("account_country"),
                },
            }

        deals.append(
            {
                "deal_id": row.get("deal_id"),
                "deal_name": row.get("deal_name"),
                "deal_description": row.get("deal_description"),
                "deal_temparature": row.get("deal_type"),
                "account": account,
                "deal_stage": build_deal_stage(row),
                "status": row.get("status"),
                "deal_status": row.get("deal_status"),
                "closing_date": format_datetime(row.get("closing_date")),
                "owner": get_user(user_map, row.get("owner")),
                "created_by": get_user(user_map, row.get("created_by")),
                "created_date": format_datetime(row.get("created_date")),
                "modified_by": get_user(user_map, row.get("modified_by")),
                "modified_date": format_datetime(row.get("modified_date")),
                "active_status": row.get("active_status"),
            }
        )

    return deals

def collect_contact_related_user_ids(
    rows: List[Dict[str, Any]],
    assignments_map: Dict[int, List[Dict[str, Any]]],
    contact_activity_map: Dict[int, List[Dict[str, Any]]],
    contact_deal_map: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> List[Any]:
    user_ids: List[Any] = []

    for row in rows:
        user_ids.extend([
            row.get("owner"),
            row.get("created_by"),
            row.get("modified_by"),
            row.get("account_owner"),
            row.get("account_created_by"),
            row.get("account_modified_by"),
        ])

    for assignments in assignments_map.values():
        for assignment in assignments:
            user_ids.extend([
                assignment.get("user_id"),
                assignment.get("assign_by"),
                assignment.get("added_by"),
            ])

    for activities in contact_activity_map.values():
        for activity in activities:
            user_ids.extend([
                activity.get("owner"),
                activity.get("created_by"),
                activity.get("modified_by"),
            ])

    contact_deal_map = contact_deal_map or {}

    for deals in contact_deal_map.values():
        for deal in deals:
            user_ids.extend([
                deal.get("owner"),
                deal.get("created_by"),
                deal.get("modified_by"),
            ])

    return user_ids


def build_account_row_from_contact(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
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
        "owner": row.get("account_owner"),
        "owner_first_name": row.get("account_owner_first_name"),
        "owner_last_name": row.get("account_owner_last_name"),
        "owner_email": row.get("account_owner_email"),
        "created_by": row.get("account_created_by"),
        "created_by_first_name": row.get("account_created_by_first_name"),
        "created_by_last_name": row.get("account_created_by_last_name"),
        "created_by_email": row.get("account_created_by_email"),
        "created_date": row.get("account_created_date"),
        "modified_by": row.get("account_modified_by"),
        "modified_by_first_name": row.get("account_modified_by_first_name"),
        "modified_by_last_name": row.get("account_modified_by_last_name"),
        "modified_by_email": row.get("account_modified_by_email"),
        "modified_date": row.get("account_modified_date"),
    }


def normalize_contact_with_account(
    row: Dict[str, Any],
    user_map: Dict[int, Dict[str, Any]],
    assignments_map: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    contact_activity_map: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    contact_deal_map: Optional[Dict[int, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    contact = normalize_contact_row(row, user_map)

    # Replace the old plain contact notes column with the CRM activity notes array.
    contact.pop("notes", None)

    contact_id = to_int(row.get("contact_id"))
    account_id = to_int(row.get("account_id"))

    assignments_map = assignments_map or {}
    contact_activity_map = contact_activity_map or {}
    contact_deal_map = contact_deal_map or {}

    contact["contact_type"] = row.get("contact_type")
    contact["account"] = normalize_account_row(build_account_row_from_contact(row)) if account_id else None

    assignments = assignments_map.get(account_id, []) if account_id else []
    assigned = build_assigned_users(
        row={"owner": row.get("account_owner") or row.get("owner")},
        assignments=assignments,
        user_map=user_map,
    )

    contact["assigned"] = assigned

    if contact.get("account"):
        contact["account"]["assigned"] = assigned

    related = build_account_activities(
        contact_activity_map.get(contact_id, []) if contact_id else [],
        user_map,
    )

    contact["notes"] = related.get("notes", [])
    contact["attachments"] = related.get("attachments", [])
    contact["activities"] = related.get("activities", [])
    contact["deals"] = build_contact_deals(
        contact_deal_map.get(contact_id, []) if contact_id else [],
        user_map,
    )

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
    filters: Optional[List[Dict[str, Any]]] = None,
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

        params.extend(
            [
                account_search_id,
                account_search_like,
                account_search_like,
            ]
        )

    build_contact_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    dynamic_where, dynamic_params = build_contact_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

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
                    lm.owner AS account_owner,
                    lm.created_by AS account_created_by,
                    lm.modified_by AS account_modified_by,

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

        contact_ids = [
            int(row.get("contact_id"))
            for row in rows
            if row.get("contact_id") is not None
        ]

        account_ids = [
            int(row.get("account_id"))
            for row in rows
            if row.get("account_id") is not None
        ]

        assignments_map = fetch_account_assignments(connection, account_ids)
        contact_activity_map = fetch_contact_activity_rows(connection, contact_ids)
        contact_deal_map = fetch_contact_deal_rows(connection, contact_ids)

        user_map = fetch_users(
            connection,
            collect_contact_related_user_ids(
                rows=rows,
                assignments_map=assignments_map,
                contact_activity_map=contact_activity_map,
                contact_deal_map=contact_deal_map,
            ),
        )

        contacts = [
            normalize_contact_with_account(
                row=row,
                user_map=user_map,
                assignments_map=assignments_map,
                contact_activity_map=contact_activity_map,
                contact_deal_map=contact_deal_map,
            )
            for row in rows
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
    filters: Optional[List[Dict[str, Any]]] = None,
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

        params.extend(
            [
                account_search_id,
                account_search_like,
                account_search_like,
            ]
        )

    build_contact_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    dynamic_where, dynamic_params = build_contact_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

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
                    lm.owner AS account_owner,
                    lm.created_by AS account_created_by,
                    lm.modified_by AS account_modified_by,

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

        contact_ids = [contact_id]
        account_ids = [int(row.get("account_id"))] if row.get("account_id") is not None else []

        assignments_map = fetch_account_assignments(connection, account_ids)
        contact_activity_map = fetch_contact_activity_rows(connection, contact_ids)
        contact_deal_map = fetch_contact_deal_rows(connection, contact_ids)

        user_map = fetch_users(
            connection,
            collect_contact_related_user_ids(
                rows=[row],
                assignments_map=assignments_map,
                contact_activity_map=contact_activity_map,
                contact_deal_map=contact_deal_map,
            ),
        )

        contact = normalize_contact_with_account(
            row=row,
            user_map=user_map,
            assignments_map=assignments_map,
            contact_activity_map=contact_activity_map,
            contact_deal_map=contact_deal_map,
        )

        dynamic_details = fetch_contact_dynamic_details(
            client_database=client_database,
            contact_ids=contact_ids,
        )

        contact["dynamic_fields"] = dynamic_details.get(contact_id, {})

        return contact

    finally:
        if connection:
            connection.close()