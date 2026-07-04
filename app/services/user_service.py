from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.db.client import get_client_connection, validate_database_name


SCHEMA_VERSION = "logiklu_user.v1"


PRODUCT_LABELS = {
    "CRM": "Sales CRM",
    "LEADANALYTICS": "Lead Actuator",
}


USER_SEARCH_FIELDS = {
    "id": ["ju.global_user_id"],
    "global_user_id": ["ju.global_user_id"],
    "client_user_id": ["ju.id"],
    "parent_id": ["ju.parent_id"],
    "name": ["first_name_value", "middle_name_value", "last_name_value"],
    "first_name": ["first_name_value"],
    "middle_name": ["middle_name_value"],
    "last_name": ["last_name_value"],
    "email": ["email_value"],
    "phone": ["phone_value", "zu.phone", "zu.mobile_phone", "zu.business_phone", "ju.phone"],
    "address": ["address_value"],
    "city": ["city_value"],
    "state": ["state_value"],
    "zip": ["zip_value"],
    "zipcode": ["zip_value"],
    "country": ["country_value"],
    "user_type": ["ju.user_type"],
    "role_code": ["ju.user_type"],
    "master_role": ["ju.user_type", "rut.type_name"],
    "role_name": ["rut.type_name"],
    "status": ["ju.status"],
    "registration_date": ["zu.registration_date"],
    "last_login_date": ["zul.last_login_date"],
    "company": ["zu.company"],
    "designation": ["zu.designation", "zu.title"],
    "title": ["zu.title", "zu.designation"],
    "username": ["zu.username"],
    "product": ["product"],
    "product_code": ["product"],
    "permission_group": ["permission_group"],
    "permission_group_id": ["permission_group"],
    "permission_group_code": ["permission_group_code"],
    "permission_group_name": ["permission_group_name"],
}


NUMERIC_FIELDS = {
    "id",
    "global_user_id",
    "client_user_id",
    "parent_id",
    "permission_group",
    "permission_group_id",
}


EXACT_TEXT_FIELDS = {
    "user_type",
    "role_code",
    "master_role",
    "status",
    "product",
    "product_code",
}


DATE_FIELDS = {
    "registration_date",
    "last_login_date",
}


RESERVED_SORT_FIELDS = {
    "id": "ju.global_user_id",
    "name": "first_name_value",
    "first_name": "first_name_value",
    "last_name": "last_name_value",
    "email": "email_value",
    "role_code": "ju.user_type",
    "master_role": "rut.type_name",
    "role_name": "rut.type_name",
    "status": "ju.status",
    "registration_date": "zu.registration_date",
    "last_login_date": "zul.last_login_date",
}


def normalize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None

    value_string = str(value).strip()

    if not value_string or value_string.startswith("0000-00-00"):
        return None

    return value_string


def normalize_full_name(first_name: Any, middle_name: Any, last_name: Any) -> str:
    parts = []

    for value in [first_name, middle_name, last_name]:
        value_string = str(value or "").strip()
        if value_string:
            parts.append(value_string)

    return " ".join(parts)


def normalize_product_code(value: Any) -> Optional[str]:
    if value is None:
        return None

    value_string = str(value).strip()

    if not value_string:
        return None

    normalized = value_string.lower().replace(" ", "").replace("_", "").replace("-", "")

    if normalized in ["crm", "salescrm", "salescrmproduct"]:
        return "CRM"

    if normalized in ["leadanalytics", "leadactuator", "leadanalyticsproduct"]:
        return "LEADANALYTICS"

    return value_string.upper()


def normalize_status(value: Any) -> Optional[str]:
    value_string = str(value or "").strip().upper()

    if value_string == "ACTIVE":
        return "Active"

    if value_string == "INACTIVE":
        return "Inactive"

    if value_string == "1":
        return "Active"

    if value_string == "0":
        return "Inactive"

    return str(value or "").strip() or None


def split_values(value: Any) -> List[str]:
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


def normalize_numeric_values(values: List[str]) -> List[int]:
    numeric_values: List[int] = []

    for value in values:
        try:
            numeric_values.append(int(value))
        except Exception:
            pass

    return numeric_values


def add_in_condition(
    column: str,
    values: List[Any],
    where_clauses: List[str],
    params: List[Any],
) -> None:
    if not values:
        return

    placeholders = ",".join(["%s"] * len(values))
    where_clauses.append("%s IN (%s)" % (column, placeholders))
    params.extend(values)


def add_like_condition(
    columns: List[str],
    value: Any,
    where_clauses: List[str],
    params: List[Any],
) -> None:
    search_value = "%" + str(value).strip() + "%"

    if not columns:
        return

    if len(columns) == 1:
        where_clauses.append("%s LIKE %%s" % columns[0])
        params.append(search_value)
        return

    parts = []
    for column in columns:
        parts.append("%s LIKE %%s" % column)
        params.append(search_value)

    where_clauses.append("(" + " OR ".join(parts) + ")")


def add_product_filter(
    field: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
    master_database: str,
    operator: str = "eq",
) -> None:
    values = split_values(value)

    if not values:
        return

    clean_field = str(field or "").strip().lower()

    if clean_field in ["product", "product_code"]:
        product_values = []
        for item in values:
            product_code = normalize_product_code(item)
            if product_code:
                product_values.append(product_code)

        if not product_values:
            return

        placeholders = ",".join(["%s"] * len(product_values))
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_user_permission_group upg_filter
                WHERE (upg_filter.user_id = ju.global_user_id OR upg_filter.user_id = ju.id)
                  AND upg_filter.product IN (%s)
            )
            """ % placeholders
        )
        params.extend(product_values)
        return

    if clean_field in ["permission_group", "permission_group_id"]:
        numeric_values = normalize_numeric_values(values)

        if not numeric_values:
            return

        placeholders = ",".join(["%s"] * len(numeric_values))
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_user_permission_group upg_filter
                WHERE (upg_filter.user_id = ju.global_user_id OR upg_filter.user_id = ju.id)
                  AND upg_filter.permission_group IN (%s)
            )
            """ % placeholders
        )
        params.extend(numeric_values)
        return

    search_value = "%" + str(value).strip() + "%"

    if clean_field == "permission_group_code":
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_user_permission_group upg_filter
                LEFT JOIN `%s`.logiklu_user_types pgt_filter
                    ON pgt_filter.id = upg_filter.permission_group
                WHERE (upg_filter.user_id = ju.global_user_id OR upg_filter.user_id = ju.id)
                  AND pgt_filter.type_code LIKE %%s
            )
            """ % master_database
        )
        params.append(search_value)
        return

    if clean_field == "permission_group_name":
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM lk_user_permission_group upg_filter
                LEFT JOIN `%s`.logiklu_user_types pgt_filter
                    ON pgt_filter.id = upg_filter.permission_group
                WHERE (upg_filter.user_id = ju.global_user_id OR upg_filter.user_id = ju.id)
                  AND pgt_filter.type_name LIKE %%s
            )
            """ % master_database
        )
        params.append(search_value)


def build_user_search_condition(
    search: Optional[str],
    search_by: Optional[str],
    where_clauses: List[str],
    params: List[Any],
    master_database: str,
) -> None:
    if not search:
        return

    search_value = str(search).strip()

    if not search_value:
        return

    search_by_value = str(search_by or "").strip().lower()

    if search_by_value in ["product", "product_code", "permission_group", "permission_group_id", "permission_group_code", "permission_group_name"]:
        add_product_filter(search_by_value, search_value, where_clauses, params, master_database)
        return

    if search_by_value:
        if search_by_value not in USER_SEARCH_FIELDS:
            return

        if search_by_value in NUMERIC_FIELDS:
            numeric_values = normalize_numeric_values([search_value])
            if numeric_values:
                where_clauses.append("%s = %%s" % USER_SEARCH_FIELDS[search_by_value][0])
                params.append(numeric_values[0])
            return

        if search_by_value in EXACT_TEXT_FIELDS:
            columns = USER_SEARCH_FIELDS[search_by_value]
            if len(columns) > 1:
                add_like_condition(columns, search_value, where_clauses, params)
            else:
                where_clauses.append("%s = %%s" % columns[0])
                params.append(search_value)
            return

        add_like_condition(USER_SEARCH_FIELDS[search_by_value], search_value, where_clauses, params)
        return

    like_value = "%" + search_value + "%"

    where_clauses.append(
        """
        (
            first_name_value LIKE %s
            OR middle_name_value LIKE %s
            OR last_name_value LIKE %s
            OR CONCAT(COALESCE(first_name_value, ''), ' ', COALESCE(middle_name_value, ''), ' ', COALESCE(last_name_value, '')) LIKE %s
            OR CONCAT(COALESCE(first_name_value, ''), ' ', COALESCE(last_name_value, '')) LIKE %s
            OR email_value LIKE %s
            OR phone_value LIKE %s
            OR city_value LIKE %s
            OR state_value LIKE %s
            OR country_value LIKE %s
            OR ju.user_type LIKE %s
            OR rut.type_name LIKE %s
            OR zu.username LIKE %s
            OR zu.company LIKE %s
            OR zu.designation LIKE %s
            OR EXISTS (
                SELECT 1
                FROM lk_user_permission_group upg_search
                LEFT JOIN `%s`.logiklu_user_types pgt_search
                    ON pgt_search.id = upg_search.permission_group
                WHERE (upg_search.user_id = ju.global_user_id OR upg_search.user_id = ju.id)
                  AND (
                        upg_search.product LIKE %%s
                        OR pgt_search.type_code LIKE %%s
                        OR pgt_search.type_name LIKE %%s
                  )
            )
        )
        """ % master_database
    )
    params.extend([like_value] * 18)


def apply_single_filter(
    field: str,
    operator: str,
    value: Any,
    where_clauses: List[str],
    params: List[Any],
    master_database: str,
) -> None:
    clean_field = str(field or "").strip().lower()
    clean_operator = str(operator or "like").strip().lower()

    if clean_field not in USER_SEARCH_FIELDS:
        return

    if clean_field in ["product", "product_code", "permission_group", "permission_group_id", "permission_group_code", "permission_group_name"]:
        add_product_filter(clean_field, value, where_clauses, params, master_database, operator=clean_operator)
        return

    columns = USER_SEARCH_FIELDS[clean_field]
    column = columns[0]

    values = split_values(value)

    if clean_field in NUMERIC_FIELDS:
        numeric_values = normalize_numeric_values(values)

        if not numeric_values:
            return

        if clean_operator in ["in", "eq"] and len(numeric_values) > 1:
            add_in_condition(column, numeric_values, where_clauses, params)
            return

        if clean_operator in ["neq", "ne"]:
            where_clauses.append("%s <> %%s" % column)
            params.append(numeric_values[0])
            return

        where_clauses.append("%s = %%s" % column)
        params.append(numeric_values[0])
        return

    if clean_field in DATE_FIELDS:
        if clean_operator in ["from", "gte", ">="]:
            where_clauses.append("%s >= %%s" % column)
            params.append(str(value).strip())
            return

        if clean_operator in ["to", "lte", "<="]:
            where_clauses.append("%s <= %%s" % column)
            params.append(str(value).strip())
            return

        if clean_operator == "between" and isinstance(value, list) and len(value) >= 2:
            where_clauses.append("%s BETWEEN %%s AND %%s" % column)
            params.append(str(value[0]).strip())
            params.append(str(value[1]).strip())
            return

    if clean_operator in ["eq", "equals"] or clean_field in EXACT_TEXT_FIELDS:
        if len(values) > 1:
            add_in_condition(column, values, where_clauses, params)
            return

        if len(columns) > 1 and clean_field == "master_role":
            add_like_condition(columns, value, where_clauses, params)
            return

        where_clauses.append("%s = %%s" % column)
        params.append(str(value).strip())
        return

    if clean_operator in ["in"]:
        add_in_condition(column, values, where_clauses, params)
        return

    if clean_operator in ["neq", "ne"]:
        where_clauses.append("%s <> %%s" % column)
        params.append(str(value).strip())
        return

    add_like_condition(columns, value, where_clauses, params)


def build_filter_conditions(
    filters: Optional[List[Dict[str, Any]]],
    where_clauses: List[str],
    params: List[Any],
    master_database: str,
) -> None:
    if not filters:
        return

    for item in filters:
        if not isinstance(item, dict):
            continue

        field = item.get("field")
        operator = item.get("operator", "like")
        value = item.get("value")

        apply_single_filter(field, operator, value, where_clauses, params, master_database)


def build_user_where_sql(
    master_database: str,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    include_archived: bool = False,
) -> Tuple[str, List[Any]]:
    where_clauses = ["1=1"]
    params: List[Any] = []

    if not include_archived:
        where_clauses.append("COALESCE(ju.active_status, 'ACTIVE') <> 'ARCHIVED'")

    build_user_search_condition(search, search_by, where_clauses, params, master_database)
    build_filter_conditions(filters, where_clauses, params, master_database)

    return " AND ".join(where_clauses), params


def get_order_by(sort_by: Optional[str], sort_order: Optional[str]) -> str:
    sort_by_value = str(sort_by or "").strip().lower()
    sort_order_value = str(sort_order or "asc").strip().lower()

    if sort_order_value not in ["asc", "desc"]:
        sort_order_value = "asc"

    if sort_by_value not in RESERVED_SORT_FIELDS:
        return "first_name_value ASC, last_name_value ASC, ju.global_user_id ASC, ju.id ASC"

    column = RESERVED_SORT_FIELDS[sort_by_value]

    return "%s %s, ju.global_user_id ASC, ju.id ASC" % (column, sort_order_value.upper())


def normalize_user_row(row: Dict[str, Any]) -> Dict[str, Any]:
    first_name = row.get("first_name")
    middle_name = row.get("middle_name")
    last_name = row.get("last_name")

    full_name = normalize_full_name(first_name, middle_name, last_name)

    return {
        "id": row.get("id"),
        "parent_id": row.get("parent_id"),
        "master_role": {
            "name": row.get("master_role_name"),
            "code": row.get("master_role_code"),
        },
        "name": full_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "email": row.get("email"),
        "phone": row.get("phone"),
        "address": {
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "zip": row.get("zip"),
            "country": row.get("country"),
        },
        "status": normalize_status(row.get("status")),
        "registration_date": normalize_datetime(row.get("registration_date")),
        "last_login_date": normalize_datetime(row.get("last_login_date")),
        "product_permissions": [],
        "_client_user_id": row.get("client_user_id"),
    }


def normalize_permission_row(row: Dict[str, Any]) -> Dict[str, Any]:
    product_code = row.get("product")
    product_code_string = str(product_code or "").upper()

    return {
        "product": {           
            "name": PRODUCT_LABELS.get(product_code_string, product_code),
            "permission_group": {
                "id": row.get("permission_group"),
                "role_code": row.get("permission_group_code"),
                "role_name": row.get("permission_group_name"),
            },
        }
    }


def attach_product_permissions(
    connection: Any,
    users: List[Dict[str, Any]],
    master_database: str,
) -> None:
    if not users:
        return

    lookup_ids: List[int] = []
    lookup_to_global_id: Dict[int, int] = {}

    for user in users:
        global_id = user.get("id")
        client_user_id = user.get("_client_user_id")

        if global_id is not None:
            try:
                global_id_int = int(global_id)
                lookup_ids.append(global_id_int)
                lookup_to_global_id[global_id_int] = global_id_int
            except Exception:
                pass

        if client_user_id is not None and global_id is not None:
            try:
                client_user_id_int = int(client_user_id)
                lookup_ids.append(client_user_id_int)
                lookup_to_global_id[client_user_id_int] = int(global_id)
            except Exception:
                pass

    lookup_ids = sorted(list(set(lookup_ids)))

    if not lookup_ids:
        return

    placeholders = ",".join(["%s"] * len(lookup_ids))

    sql = """
        SELECT
            upg.user_id,
            upg.product,
            upg.permission_group,
            pgt.type_code AS permission_group_code,
            pgt.type_name AS permission_group_name
        FROM lk_user_permission_group upg
        LEFT JOIN `%s`.logiklu_user_types pgt
            ON pgt.id = upg.permission_group
        WHERE upg.user_id IN (%s)
        ORDER BY
            upg.user_id ASC,
            FIELD(upg.product, 'CRM', 'LEADANALYTICS') ASC,
            upg.product ASC,
            upg.permission_group ASC
    """ % (master_database, placeholders)

    permissions_by_user: Dict[int, List[Dict[str, Any]]] = {}
    seen: Dict[int, Dict[str, bool]] = {}

    with connection.cursor() as cursor:
        cursor.execute(sql, tuple(lookup_ids))
        rows = cursor.fetchall()

    for row in rows:
        lookup_user_id = row.get("user_id")

        if lookup_user_id is None:
            continue

        try:
            global_id = lookup_to_global_id.get(int(lookup_user_id))
        except Exception:
            global_id = None

        if global_id is None:
            continue

        if global_id not in permissions_by_user:
            permissions_by_user[global_id] = []
            seen[global_id] = {}

        dedupe_key = "%s|%s" % (row.get("product"), row.get("permission_group"))
        if seen[global_id].get(dedupe_key):
            continue

        seen[global_id][dedupe_key] = True
        permissions_by_user[global_id].append(normalize_permission_row(row))

    for user in users:
        global_id = user.get("id")
        try:
            global_id_int = int(global_id)
        except Exception:
            global_id_int = None

        user["product_permissions"] = permissions_by_user.get(global_id_int, [])
        user.pop("_client_user_id", None)


def get_user_select_sql(master_database: str) -> str:
    return """
        SELECT
            ju.id AS client_user_id,
            ju.global_user_id AS id,
            ju.parent_id,
            ju.user_type AS master_role_code,
            rut.type_name AS master_role_name,

            COALESCE(NULLIF(zu.first_name, ''), ju.first_name) AS first_name,
            COALESCE(NULLIF(zu.middle_name, ''), ju.middle_name) AS middle_name,
            COALESCE(NULLIF(zu.last_name, ''), ju.last_name) AS last_name,
            COALESCE(NULLIF(zu.email, ''), ju.email) AS email,
            COALESCE(NULLIF(zu.mobile_phone, ''), NULLIF(zu.phone, ''), NULLIF(zu.business_phone, ''), ju.phone) AS phone,
            COALESCE(NULLIF(zu.address, ''), ju.address) AS address,
            COALESCE(NULLIF(zu.city, ''), ju.city) AS city,
            COALESCE(NULLIF(zu.state, ''), ju.state) AS state,
            COALESCE(NULLIF(zu.zip, ''), ju.zip) AS zip,
            COALESCE(NULLIF(zu.country, ''), ju.country) AS country,

            COALESCE(NULLIF(zu.first_name, ''), ju.first_name) AS first_name_value,
            COALESCE(NULLIF(zu.middle_name, ''), ju.middle_name) AS middle_name_value,
            COALESCE(NULLIF(zu.last_name, ''), ju.last_name) AS last_name_value,
            COALESCE(NULLIF(zu.email, ''), ju.email) AS email_value,
            COALESCE(NULLIF(zu.mobile_phone, ''), NULLIF(zu.phone, ''), NULLIF(zu.business_phone, ''), ju.phone) AS phone_value,
            COALESCE(NULLIF(zu.address, ''), ju.address) AS address_value,
            COALESCE(NULLIF(zu.city, ''), ju.city) AS city_value,
            COALESCE(NULLIF(zu.state, ''), ju.state) AS state_value,
            COALESCE(NULLIF(zu.zip, ''), ju.zip) AS zip_value,
            COALESCE(NULLIF(zu.country, ''), ju.country) AS country_value,

            ju.status,
            zu.registration_date,
            zul.last_login_date
        FROM jos_users ju
        LEFT JOIN `%s`.zp_users zu
            ON zu.id = ju.global_user_id
        LEFT JOIN `%s`.logiklu_user_types rut
            ON CONVERT(ju.user_type USING utf8mb4) COLLATE utf8mb4_general_ci = rut.type_code COLLATE utf8mb4_general_ci
        LEFT JOIN (
            SELECT
                user_id,
                MAX(login_time) AS last_login_date
            FROM `%s`.zp_user_login
            GROUP BY user_id
        ) zul
            ON zul.user_id = ju.global_user_id
    """ % (master_database, master_database, master_database)


def fetch_users(
    client_database: str,
    search: Optional[str] = None,
    search_by: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    filters: Optional[List[Dict[str, Any]]] = None,
    include_archived: bool = False,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
) -> Dict[str, Any]:
    connection = None
    client_database_name = validate_database_name(client_database)
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    page_value = max(int(page or 1), 1)
    per_page_value = min(max(int(per_page or 10), 1), 100)
    offset = (page_value - 1) * per_page_value

    where_sql, params = build_user_where_sql(
        master_database=master_database,
        search=search,
        search_by=search_by,
        filters=filters,
        include_archived=include_archived,
    )

    order_by_sql = get_order_by(sort_by, sort_order)

    try:
        connection = get_client_connection(client_database_name)

        with connection.cursor() as cursor:
            count_sql = """
                SELECT COUNT(DISTINCT ju.id) AS total_records
                FROM jos_users ju
                LEFT JOIN `%s`.zp_users zu
                    ON zu.id = ju.global_user_id
                LEFT JOIN `%s`.logiklu_user_types rut
                    ON CONVERT(ju.user_type USING utf8mb4) COLLATE utf8mb4_general_ci = rut.type_code COLLATE utf8mb4_general_ci
                LEFT JOIN (
                    SELECT
                        user_id,
                        MAX(login_time) AS last_login_date
                    FROM `%s`.zp_user_login
                    GROUP BY user_id
                ) zul
                    ON zul.user_id = ju.global_user_id
                WHERE %s
            """ % (master_database, master_database, master_database, where_sql)

            cursor.execute(count_sql, tuple(params))
            count_row = cursor.fetchone()
            total_records = int(count_row.get("total_records", 0)) if count_row else 0

            list_sql = """
                %s
                WHERE %s
                ORDER BY %s
                LIMIT %%s OFFSET %%s
            """ % (get_user_select_sql(master_database), where_sql, order_by_sql)

            cursor.execute(list_sql, tuple(params + [per_page_value, offset]))
            rows = cursor.fetchall()

        users = [normalize_user_row(row) for row in rows]
        attach_product_permissions(connection, users, master_database)

        total_pages = 0
        if total_records > 0:
            total_pages = int((total_records + per_page_value - 1) / per_page_value)

        return {
            "items": users,
            "total_records": total_records,
            "page": page_value,
            "per_page": per_page_value,
            "offset": offset,
            "total_pages": total_pages,
            "has_next": page_value < total_pages,
            "has_previous": page_value > 1,
        }

    finally:
        if connection:
            connection.close()


def fetch_user_by_id(
    client_database: str,
    user_id: int,
    include_archived: bool = False,
) -> Optional[Dict[str, Any]]:
    connection = None
    client_database_name = validate_database_name(client_database)
    master_database = validate_database_name(settings.MASTER_DB_NAME)

    where_clauses = ["ju.global_user_id = %s"]
    params: List[Any] = [user_id]

    if not include_archived:
        where_clauses.append("COALESCE(ju.active_status, 'ACTIVE') <> 'ARCHIVED'")

    where_sql = " AND ".join(where_clauses)

    try:
        connection = get_client_connection(client_database_name)

        with connection.cursor() as cursor:
            sql = """
                %s
                WHERE %s
                LIMIT 1
            """ % (get_user_select_sql(master_database), where_sql)

            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        if not row:
            return None

        users = [normalize_user_row(row)]
        attach_product_permissions(connection, users, master_database)

        return users[0]

    finally:
        if connection:
            connection.close()
