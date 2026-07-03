from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection, validate_database_name
from app.services.contact_service import (
    CONTACT_SEARCH_FIELDS,
    fetch_contact_dynamic_details,
    normalize_contact_with_account,
)


TEXT_COLLATION = "utf8mb4_unicode_ci"
SCHEMA_VERSION = "logiklu_focus_contact.v1"


FOCUS_CONTACT_SEARCH_FIELDS = dict(CONTACT_SEARCH_FIELDS)
FOCUS_CONTACT_SEARCH_FIELDS.update(
    {
        "contact_id": ["cc.contact_id"],
        "account_id": ["cc.lead_id"],
        "lead_id": ["cc.lead_id"],
        "company_id": ["cc.company_id"],
        "company_name": ["lm.lead_name"],
        "account_name": ["lm.lead_name"],
        "company": ["lm.lead_name"],
        "website": ["lm.website"],
        "account_website": ["lm.website"],
        "company_website": ["lm.website"],
        "industry": ["lm.industry"],
        "account_city": ["lm.city"],
        "account_state": ["lm.state"],
        "account_country": ["lm.country"],
        "primary_phone": ["cc.primary_phone"],
        "whatsappno": ["cc.whatsappno"],
        "linkedin": ["cc.linkedin"],
        "facebook": ["cc.facebook"],
        "instagram": ["cc.instagram"],
        "skype": ["cc.skype"],
        "created_date": ["cc.created_date"],
        "modified_date": ["cc.modified_date"],
        "is_important": ["cc.is_important"],
        "status": ["cc.status"],
        "active_status": ["cc.active_status"],
    }
)


NUMERIC_FOCUS_CONTACT_FIELDS = {
    "contact_id",
    "account_id",
    "lead_id",
    "company_id",
    "owner",
    "created_by",
    "modified_by",
}


EXACT_FOCUS_CONTACT_FIELDS = {
    "contact_type",
    "source",
    "country",
    "state",
    "city",
    "owner",
    "created_by",
    "modified_by",
    "is_important",
    "status",
    "active_status",
}


def sql_collated_text(expression: str) -> str:
    return f"CONVERT({expression} USING utf8mb4) COLLATE {TEXT_COLLATION}"


def sql_collated_equal(left_expression: str, right_expression: str) -> str:
    return f"{sql_collated_text(left_expression)} = {sql_collated_text(right_expression)}"


def sql_collated_lower_trim_equal(left_expression: str, right_expression: str) -> str:
    return (
        f"LOWER(TRIM({sql_collated_text(left_expression)})) "
        f"= LOWER(TRIM({sql_collated_text(right_expression)}))"
    )


def format_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def parse_bool_value(value: Any) -> Optional[bool]:
    if value is None:
        return None

    value_string = str(value).strip().lower()

    if not value_string:
        return None

    if value_string in ["1", "true", "yes", "y"]:
        return True

    if value_string in ["0", "false", "no", "n"]:
        return False

    return None


def normalize_interaction_type(value: Any) -> Optional[str]:
    if value is None:
        return None

    value_string = str(value).strip().lower().replace("-", "_").replace(" ", "_")

    if not value_string:
        return None

    if value_string in ["leadform", "lead_form"]:
        return "lead_form_submission"

    if value_string in ["innerform", "inner_form"]:
        return "inner_form_submission"

    if value_string in ["link_click", "email_click"]:
        return "email_link_click"

    if value_string in [
        "lead_form_submission",
        "inner_form_submission",
        "email_link_click",
    ]:
        return value_string

    return None



def split_csv_values(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    value_string = str(value).strip()

    if not value_string:
        return []

    return [item.strip() for item in value_string.split(",") if item.strip()]


def normalize_numeric_values(values: List[Any]) -> List[int]:
    numeric_values: List[int] = []

    for value in values:
        try:
            numeric_values.append(int(value))
        except Exception:
            pass

    return numeric_values


def build_focus_contact_in_condition(
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


def build_focus_contact_search_condition(
    search: Optional[str],
    search_by: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not search:
        return

    search_by_value = str(search_by or "").strip().lower()
    search_text = str(search).strip()

    if not search_text:
        return

    search_value = f"%{search_text}%"

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
                OR cc.linkedin LIKE %s
                OR cc.facebook LIKE %s
                OR cc.instagram LIKE %s
                OR cc.skype LIKE %s
                OR cc.address LIKE %s
                OR cc.city LIKE %s
                OR cc.state LIKE %s
                OR cc.country LIKE %s
                OR cc.zipcode LIKE %s
                OR cc.department LIKE %s
                OR cc.designation LIKE %s
                OR cc.contact_type LIKE %s
                OR cc.source LIKE %s
                OR lm.lead_name LIKE %s
                OR lm.website LIKE %s
                OR lm.industry LIKE %s
                OR lm.city LIKE %s
                OR lm.state LIKE %s
                OR lm.country LIKE %s
            )
            """
        )

        params.extend([search_value] * 27)
        return

    if search_by_value not in FOCUS_CONTACT_SEARCH_FIELDS:
        return

    values = split_csv_values(search_text)

    if not values:
        return

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

    column = FOCUS_CONTACT_SEARCH_FIELDS[search_by_value][0]

    if search_by_value in NUMERIC_FOCUS_CONTACT_FIELDS:
        numeric_values = normalize_numeric_values(values)
        build_focus_contact_in_condition(column, numeric_values, where_clauses, params)
        return

    if search_by_value in EXACT_FOCUS_CONTACT_FIELDS and len(values) > 1:
        build_focus_contact_in_condition(column, values, where_clauses, params)
        return

    column_conditions: List[str] = []

    for column in FOCUS_CONTACT_SEARCH_FIELDS[search_by_value]:
        column_conditions.append(f"{column} LIKE %s")
        params.append(f"%{values[0]}%")

    where_clauses.append("(" + " OR ".join(column_conditions) + ")")


def build_focus_contact_dynamic_filters(
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

        if field not in FOCUS_CONTACT_SEARCH_FIELDS:
            continue

        columns = FOCUS_CONTACT_SEARCH_FIELDS[field]

        if not columns:
            continue

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

        elif operator == "between" and isinstance(value, list) and len(value) >= 2:
            where_clauses.append(f"{column} BETWEEN %s AND %s")
            params.extend([value[0], value[1]])

    return where_clauses, params


def split_interaction_types(value: Any) -> List[str]:
    normalized_types: List[str] = []

    for item in split_csv_values(value):
        normalized_type = normalize_interaction_type(item)

        if normalized_type and normalized_type not in normalized_types:
            normalized_types.append(normalized_type)

    return normalized_types


def get_lead_form_exists_sql(date_condition: str = "") -> str:
    return f"""
        EXISTS (
            SELECT 1
            FROM lk_leadform_form_submission lfs_exists
            WHERE (
                    (
                        lfs_exists.contact_id IS NOT NULL
                        AND lfs_exists.contact_id <> 0
                        AND lfs_exists.contact_id = cc.contact_id
                    )
                    OR (
                        lfs_exists.email IS NOT NULL
                        AND lfs_exists.email <> ''
                        AND cc.email IS NOT NULL
                        AND cc.email <> ''
                        AND {sql_collated_lower_trim_equal("lfs_exists.email", "cc.email")}
                    )
                )
                {date_condition}
        )
    """


def get_inner_form_exists_sql(date_condition: str = "") -> str:
    return f"""
        EXISTS (
            SELECT 1
            FROM jos_form_track jft_exists
            INNER JOIN jos_form_track_setting jfts_exists
                ON jfts_exists.page_id = jft_exists.page_id
               AND jfts_exists.form_id = jft_exists.form_id
               AND jfts_exists.leadfieldemail IS NOT NULL
               AND jfts_exists.leadfieldemail <> ''
               AND {sql_collated_equal("jfts_exists.leadfieldemail", "jft_exists.field_name")}
            WHERE cc.email IS NOT NULL
              AND cc.email <> ''
              AND jft_exists.field_val IS NOT NULL
              AND jft_exists.field_val <> ''
              AND {sql_collated_lower_trim_equal("jft_exists.field_val", "cc.email")}
              {date_condition}
        )
    """


def get_email_link_exists_sql(date_condition: str = "") -> str:
    return f"""
        EXISTS (
            SELECT 1
            FROM lk_link_visits lv_exists
            WHERE lv_exists.contact_id IS NOT NULL
              AND lv_exists.contact_id <> 0
              AND lv_exists.contact_id = cc.contact_id
              {date_condition}
        )
    """


def add_focus_contact_base_condition(where_clauses: List[str]) -> None:
    where_clauses.append(
        f"""
        (
            {get_lead_form_exists_sql()}
            OR {get_inner_form_exists_sql()}
            OR {get_email_link_exists_sql()}
        )
        """
    )


def get_interaction_exists_sql(interaction_type: str) -> Optional[str]:
    normalized_type = normalize_interaction_type(interaction_type)

    if normalized_type == "lead_form_submission":
        return get_lead_form_exists_sql()

    if normalized_type == "inner_form_submission":
        return get_inner_form_exists_sql()

    if normalized_type == "email_link_click":
        return get_email_link_exists_sql()

    return None


def add_interaction_type_condition(
    interaction_type: Optional[str],
    where_clauses: List[str],
) -> None:
    normalized_types = split_interaction_types(interaction_type)

    if not normalized_types:
        return

    exists_parts: List[str] = []

    for normalized_type in normalized_types:
        exists_sql = get_interaction_exists_sql(normalized_type)

        if exists_sql:
            exists_parts.append(exists_sql)

    if not exists_parts:
        return

    where_clauses.append("(" + " OR ".join(exists_parts) + ")")


def add_required_interactions_condition(
    required_interactions: Optional[str],
    where_clauses: List[str],
) -> None:
    normalized_types = split_interaction_types(required_interactions)

    for normalized_type in normalized_types:
        exists_sql = get_interaction_exists_sql(normalized_type)

        if exists_sql:
            where_clauses.append(exists_sql)


def add_excluded_interactions_condition(
    excluded_interactions: Optional[str],
    where_clauses: List[str],
) -> None:
    normalized_types = split_interaction_types(excluded_interactions)

    for normalized_type in normalized_types:
        exists_sql = get_interaction_exists_sql(normalized_type)

        if exists_sql:
            where_clauses.append(f"NOT ({exists_sql})")

def add_has_interaction_condition(
    value: Optional[str],
    exists_sql: str,
    where_clauses: List[str],
) -> None:
    parsed_value = parse_bool_value(value)

    if parsed_value is None:
        return

    if parsed_value:
        where_clauses.append(exists_sql)
        return

    where_clauses.append(f"NOT ({exists_sql})")


def add_last_interaction_from_condition(
    last_interaction_from: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not last_interaction_from:
        return

    where_clauses.append(
        f"""
        (
            {get_lead_form_exists_sql("AND lfs_exists.track_date_time >= %s")}
            OR {get_inner_form_exists_sql("AND jft_exists.track_date_time >= %s")}
            OR {get_email_link_exists_sql("AND lv_exists.track_date_time >= %s")}
        )
        """
    )

    params.extend([last_interaction_from, last_interaction_from, last_interaction_from])


def add_last_interaction_to_condition(
    last_interaction_to: Optional[str],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not last_interaction_to:
        return

    where_clauses.append(
        f"""
        (
            {get_lead_form_exists_sql("AND lfs_exists.track_date_time <= %s")}
            OR {get_inner_form_exists_sql("AND jft_exists.track_date_time <= %s")}
            OR {get_email_link_exists_sql("AND lv_exists.track_date_time <= %s")}
        )
        """
    )

    params.extend([last_interaction_to, last_interaction_to, last_interaction_to])


def build_focus_contact_where_clause(
    account_id: Optional[int] = None,
    account_search: Optional[str] = None,
    associated_accounts_only: bool = False,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    interaction_type: Optional[str] = None,
    has_lead_form_submission: Optional[str] = None,
    has_inner_form_submission: Optional[str] = None,
    has_email_link_click: Optional[str] = None,
    required_interactions: Optional[str] = None,
    excluded_interactions: Optional[str] = None,
    last_interaction_from: Optional[str] = None,
    last_interaction_to: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    where_clauses: List[str] = [
        "cc.active_status = 'active'"
    ]

    params: List[Any] = []

    add_focus_contact_base_condition(where_clauses)

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

    build_focus_contact_search_condition(
        search=search,
        search_by=search_by,
        where_clauses=where_clauses,
        params=params,
    )

    dynamic_where, dynamic_params = build_focus_contact_dynamic_filters(filters)
    where_clauses.extend(dynamic_where)
    params.extend(dynamic_params)

    add_interaction_type_condition(
        interaction_type=interaction_type,
        where_clauses=where_clauses,
    )

    add_required_interactions_condition(
        required_interactions=required_interactions,
        where_clauses=where_clauses,
    )

    add_excluded_interactions_condition(
        excluded_interactions=excluded_interactions,
        where_clauses=where_clauses,
    )

    add_has_interaction_condition(
        value=has_lead_form_submission,
        exists_sql=get_lead_form_exists_sql(),
        where_clauses=where_clauses,
    )

    add_has_interaction_condition(
        value=has_inner_form_submission,
        exists_sql=get_inner_form_exists_sql(),
        where_clauses=where_clauses,
    )

    add_has_interaction_condition(
        value=has_email_link_click,
        exists_sql=get_email_link_exists_sql(),
        where_clauses=where_clauses,
    )

    add_last_interaction_from_condition(
        last_interaction_from=last_interaction_from,
        where_clauses=where_clauses,
        params=params,
    )

    add_last_interaction_to_condition(
        last_interaction_to=last_interaction_to,
        where_clauses=where_clauses,
        params=params,
    )

    return " AND ".join(where_clauses), params


def get_focus_contact_select_fields(master_database: str) -> str:
    return f"""
        SELECT
            cc.contact_id,
            cc.lead_id,
            cc.contact_type,
            cc.first_name,
            cc.last_name,
            cc.email,
            cc.primary_phone,
            cc.whatsappno,
            cc.linkedin,
            cc.facebook,
            cc.instagram,
            cc.skype,
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
            account_modified_user.email AS account_modified_by_email,

            (
                SELECT COUNT(*)
                FROM lk_leadform_form_submission lfs_count
                WHERE (
                        (
                            lfs_count.contact_id IS NOT NULL
                            AND lfs_count.contact_id <> 0
                            AND lfs_count.contact_id = cc.contact_id
                        )
                        OR (
                            lfs_count.email IS NOT NULL
                            AND lfs_count.email <> ''
                            AND cc.email IS NOT NULL
                            AND cc.email <> ''
                            AND {sql_collated_lower_trim_equal("lfs_count.email", "cc.email")}
                        )
                    )
            ) AS lead_form_submission_count,

            (
                SELECT COUNT(DISTINCT COALESCE(NULLIF(jft_count.form_track_id, 0), NULLIF(jft_count.support_id, 0), jft_count.id))
                FROM jos_form_track jft_count
                INNER JOIN jos_form_track_setting jfts_count
                    ON jfts_count.page_id = jft_count.page_id
                   AND jfts_count.form_id = jft_count.form_id
                   AND jfts_count.leadfieldemail IS NOT NULL
                   AND jfts_count.leadfieldemail <> ''
                   AND {sql_collated_equal("jfts_count.leadfieldemail", "jft_count.field_name")}
                WHERE cc.email IS NOT NULL
                  AND cc.email <> ''
                  AND jft_count.field_val IS NOT NULL
                  AND jft_count.field_val <> ''
                  AND {sql_collated_lower_trim_equal("jft_count.field_val", "cc.email")}
            ) AS inner_form_submission_count,

            (
                SELECT COUNT(*)
                FROM lk_link_visits lv_count
                WHERE lv_count.contact_id IS NOT NULL
                  AND lv_count.contact_id <> 0
                  AND lv_count.contact_id = cc.contact_id
            ) AS email_link_click_count,

            (
                SELECT MIN(lfs_min.track_date_time)
                FROM lk_leadform_form_submission lfs_min
                WHERE (
                        (
                            lfs_min.contact_id IS NOT NULL
                            AND lfs_min.contact_id <> 0
                            AND lfs_min.contact_id = cc.contact_id
                        )
                        OR (
                            lfs_min.email IS NOT NULL
                            AND lfs_min.email <> ''
                            AND cc.email IS NOT NULL
                            AND cc.email <> ''
                            AND {sql_collated_lower_trim_equal("lfs_min.email", "cc.email")}
                        )
                    )
            ) AS lead_form_first_interaction_at,

            (
                SELECT MAX(lfs_max.track_date_time)
                FROM lk_leadform_form_submission lfs_max
                WHERE (
                        (
                            lfs_max.contact_id IS NOT NULL
                            AND lfs_max.contact_id <> 0
                            AND lfs_max.contact_id = cc.contact_id
                        )
                        OR (
                            lfs_max.email IS NOT NULL
                            AND lfs_max.email <> ''
                            AND cc.email IS NOT NULL
                            AND cc.email <> ''
                            AND {sql_collated_lower_trim_equal("lfs_max.email", "cc.email")}
                        )
                    )
            ) AS lead_form_last_interaction_at,

            (
                SELECT MIN(jft_min.track_date_time)
                FROM jos_form_track jft_min
                INNER JOIN jos_form_track_setting jfts_min
                    ON jfts_min.page_id = jft_min.page_id
                   AND jfts_min.form_id = jft_min.form_id
                   AND jfts_min.leadfieldemail IS NOT NULL
                   AND jfts_min.leadfieldemail <> ''
                   AND {sql_collated_equal("jfts_min.leadfieldemail", "jft_min.field_name")}
                WHERE cc.email IS NOT NULL
                  AND cc.email <> ''
                  AND jft_min.field_val IS NOT NULL
                  AND jft_min.field_val <> ''
                  AND {sql_collated_lower_trim_equal("jft_min.field_val", "cc.email")}
            ) AS inner_form_first_interaction_at,

            (
                SELECT MAX(jft_max.track_date_time)
                FROM jos_form_track jft_max
                INNER JOIN jos_form_track_setting jfts_max
                    ON jfts_max.page_id = jft_max.page_id
                   AND jfts_max.form_id = jft_max.form_id
                   AND jfts_max.leadfieldemail IS NOT NULL
                   AND jfts_max.leadfieldemail <> ''
                   AND {sql_collated_equal("jfts_max.leadfieldemail", "jft_max.field_name")}
                WHERE cc.email IS NOT NULL
                  AND cc.email <> ''
                  AND jft_max.field_val IS NOT NULL
                  AND jft_max.field_val <> ''
                  AND {sql_collated_lower_trim_equal("jft_max.field_val", "cc.email")}
            ) AS inner_form_last_interaction_at,

            (
                SELECT MIN(lv_min.track_date_time)
                FROM lk_link_visits lv_min
                WHERE lv_min.contact_id IS NOT NULL
                  AND lv_min.contact_id <> 0
                  AND lv_min.contact_id = cc.contact_id
            ) AS email_link_first_interaction_at,

            (
                SELECT MAX(lv_max.track_date_time)
                FROM lk_link_visits lv_max
                WHERE lv_max.contact_id IS NOT NULL
                  AND lv_max.contact_id <> 0
                  AND lv_max.contact_id = cc.contact_id
            ) AS email_link_last_interaction_at

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
    """


def get_datetime_candidates(row: Dict[str, Any], keys: List[str]) -> List[datetime]:
    candidates: List[datetime] = []

    for key in keys:
        value = row.get(key)

        if not value:
            continue

        if isinstance(value, datetime):
            candidates.append(value)
            continue

        try:
            candidates.append(datetime.fromisoformat(str(value).replace("T", " ")))
        except Exception:
            pass

    return candidates


def build_focus_interaction_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    lead_form_count = int(row.get("lead_form_submission_count") or 0)
    inner_form_count = int(row.get("inner_form_submission_count") or 0)
    email_link_count = int(row.get("email_link_click_count") or 0)

    interaction_types: List[str] = []

    if lead_form_count > 0:
        interaction_types.append("lead_form_submission")

    if inner_form_count > 0:
        interaction_types.append("inner_form_submission")

    if email_link_count > 0:
        interaction_types.append("email_link_click")

    first_candidates = get_datetime_candidates(
        row,
        [
            "lead_form_first_interaction_at",
            "inner_form_first_interaction_at",
            "email_link_first_interaction_at",
        ],
    )

    last_candidates = get_datetime_candidates(
        row,
        [
            "lead_form_last_interaction_at",
            "inner_form_last_interaction_at",
            "email_link_last_interaction_at",
        ],
    )

    first_interaction_at = min(first_candidates) if first_candidates else None
    last_interaction_at = max(last_candidates) if last_candidates else None

    return {
        "has_focus_interaction": (lead_form_count + inner_form_count + email_link_count) > 0,
        "interaction_types": interaction_types,
        "lead_form_submission_count": lead_form_count,
        "inner_form_submission_count": inner_form_count,
        "email_link_click_count": email_link_count,
        "total_focus_interactions": lead_form_count + inner_form_count + email_link_count,
        "first_interaction_at": format_datetime(first_interaction_at),
        "last_interaction_at": format_datetime(last_interaction_at),
    }


def normalize_focus_contact_row(row: Dict[str, Any]) -> Dict[str, Any]:
    contact = normalize_contact_with_account(row)
    contact["schema_version"] = SCHEMA_VERSION
    contact["focus_interaction_summary"] = build_focus_interaction_summary(row)
    return contact


def fetch_focus_contacts(
    client_database: str,
    page: int = 1,
    per_page: int = 10,
    account_id: Optional[int] = None,
    account_search: Optional[str] = None,
    associated_accounts_only: bool = False,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    interaction_type: Optional[str] = None,
    has_lead_form_submission: Optional[str] = None,
    has_inner_form_submission: Optional[str] = None,
    has_email_link_click: Optional[str] = None,
    required_interactions: Optional[str] = None,
    excluded_interactions: Optional[str] = None,
    last_interaction_from: Optional[str] = None,
    last_interaction_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    page = max(1, int(page))
    per_page = max(10, min(int(per_page), 100))
    offset = (page - 1) * per_page

    where_sql, params = build_focus_contact_where_clause(
        account_id=account_id,
        account_search=account_search,
        associated_accounts_only=associated_accounts_only,
        search=search,
        search_by=search_by,
        filters=filters,
        interaction_type=interaction_type,
        has_lead_form_submission=has_lead_form_submission,
        has_inner_form_submission=has_inner_form_submission,
        has_email_link_click=has_email_link_click,
        required_interactions=required_interactions,
        excluded_interactions=excluded_interactions,
        last_interaction_from=last_interaction_from,
        last_interaction_to=last_interaction_to,
    )

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                {get_focus_contact_select_fields(master_database)}

                WHERE {where_sql}

                ORDER BY
                    email_link_last_interaction_at DESC,
                    lead_form_last_interaction_at DESC,
                    inner_form_last_interaction_at DESC,
                    cc.modified_date DESC,
                    cc.created_date DESC

                LIMIT %s OFFSET %s
            """

            query_params = params + [per_page, offset]
            cursor.execute(sql, tuple(query_params))
            rows = cursor.fetchall()

        contacts = [normalize_focus_contact_row(row) for row in rows]

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


def count_focus_contacts(
    client_database: str,
    account_id: Optional[int] = None,
    account_search: Optional[str] = None,
    associated_accounts_only: bool = False,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    interaction_type: Optional[str] = None,
    has_lead_form_submission: Optional[str] = None,
    has_inner_form_submission: Optional[str] = None,
    has_email_link_click: Optional[str] = None,
    required_interactions: Optional[str] = None,
    excluded_interactions: Optional[str] = None,
    last_interaction_from: Optional[str] = None,
    last_interaction_to: Optional[str] = None,
) -> int:
    connection = None

    where_sql, params = build_focus_contact_where_clause(
        account_id=account_id,
        account_search=account_search,
        associated_accounts_only=associated_accounts_only,
        search=search,
        search_by=search_by,
        filters=filters,
        interaction_type=interaction_type,
        has_lead_form_submission=has_lead_form_submission,
        has_inner_form_submission=has_inner_form_submission,
        has_email_link_click=has_email_link_click,
        required_interactions=required_interactions,
        excluded_interactions=excluded_interactions,
        last_interaction_from=last_interaction_from,
        last_interaction_to=last_interaction_to,
    )

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


def fetch_focus_contact_by_id(
    client_database: str,
    contact_id: int,
) -> Optional[Dict[str, Any]]:
    connection = None
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    where_clauses = [
        "cc.contact_id = %s",
        "cc.active_status = 'active'",
    ]

    params: List[Any] = [contact_id]

    add_focus_contact_base_condition(where_clauses)

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            sql = f"""
                {get_focus_contact_select_fields(master_database)}

                WHERE {where_sql}

                LIMIT 1
            """

            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        if not row:
            return None

        contact = normalize_focus_contact_row(row)

        dynamic_details = fetch_contact_dynamic_details(
            client_database=client_database,
            contact_ids=[contact_id],
        )

        contact["dynamic_fields"] = dynamic_details.get(contact_id, {})

        return contact

    finally:
        if connection:
            connection.close()
