from typing import Any, Dict, Optional

from app.db.client import get_client_connection
from app.db.master import get_master_connection


ROOT_URL = "https://logiklu.com/"


class DeviceProfileServiceError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        http_status: int = 400,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.data = data


USER_TYPE_DISPLAY = {
    "clientsuperadmin": "Client Super Admin",
    "clientadmin": "Client Admin",
    "dataadmin": "Client Data Admin",
    "supervisor": "Manager",
    "clientuser": "Sales Person",
    "leadresearcher": "Lead Researcher",
    "marketingprof": "Marketing Professional",
    "execmanagement": "Executive Management",
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _full_name(user: Dict[str, Any]) -> str:
    values = [
        _safe_str(user.get("first_name")),
        _safe_str(user.get("middle_name")),
        _safe_str(user.get("last_name")),
    ]
    return " ".join(value for value in values if value).strip()


def _avatar_url(profile_image: Any) -> str:
    profile_image = _safe_str(profile_image)

    if profile_image:
        return ROOT_URL + "upload/avatar/" + profile_image.lstrip("/")

    return ROOT_URL + "images/gravatar.jpg"


def _landing_page_url(product: Any, page: Any) -> str:
    product = _safe_str(product).upper()
    page = _safe_str(page)

    if not page:
        return ""

    if page.startswith("https://") or page.startswith("http://"):
        return page

    if page.startswith("ROOTPATH/"):
        page = page[len("ROOTPATH/"):]

    if product == "LEADANALYTICS":
        return ROOT_URL + "analytic/v.2/" + page.lstrip("/")

    return ROOT_URL + "app/v1/" + page.lstrip("/")


def _fetch_master_user(user_id: int) -> Dict[str, Any]:
    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    first_name,
                    middle_name,
                    last_name,
                    profile_image,
                    email,
                    phone_country_code,
                    phone,
                    company,
                    designation,
                    status
                FROM zp_users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            user = cursor.fetchone()

        if not user:
            raise DeviceProfileServiceError(
                "User does not exist",
                "DEVICE_PROFILE_USER_NOT_FOUND",
                404,
            )

        if _safe_int(user.get("status")) != 1:
            raise DeviceProfileServiceError(
                "This user is not active",
                "DEVICE_PROFILE_USER_INACTIVE",
                403,
            )

        return user

    finally:
        if connection:
            connection.close()


def _fetch_account(
    domain_id: int,
    account_id: int,
) -> Dict[str, Any]:
    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    account_name,
                    ac_id,
                    domain_id,
                    databasename,
                    websitename,
                    originalwebsitename,
                    timezone
                FROM zp_subscription_domain_info
                WHERE domain_id = %s
                  AND ac_id = %s
                  AND status = 'ACTIVE'
                LIMIT 1
                """,
                (
                    domain_id,
                    account_id,
                ),
            )
            account = cursor.fetchone()

        if not account:
            raise DeviceProfileServiceError(
                "Selected account does not exist or is inactive",
                "DEVICE_PROFILE_ACCOUNT_NOT_FOUND",
                404,
                {
                    "domain_id": domain_id,
                    "account_id": account_id,
                },
            )

        return account

    finally:
        if connection:
            connection.close()


def _fetch_client_user(
    client_database: str,
    user_id: int,
) -> Dict[str, Any]:
    """
    jos_users is authoritative for the selected account's role/user_type and
    selected landing_page ID.
    """
    connection = None

    try:
        connection = get_client_connection(client_database)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    global_user_id,
                    user_type,
                    landing_page,
                    status,
                    active_status
                FROM jos_users
                WHERE global_user_id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            client_user = cursor.fetchone()

        if not client_user:
            raise DeviceProfileServiceError(
                "You do not have access to the selected account",
                "DEVICE_PROFILE_ACCOUNT_FORBIDDEN",
                403,
            )

        status = _safe_str(
            client_user.get("status")
        ).upper()

        # Some legacy web profile/avatar update paths can leave jos_users.status
        # as an empty string. Do not treat a blank legacy value as INACTIVE.
        # Reject only an explicit INACTIVE state.
        if status == "INACTIVE":
            raise DeviceProfileServiceError(
                "Your user is inactive for the selected account",
                "DEVICE_PROFILE_ACCOUNT_USER_INACTIVE",
                403,
            )

        active_status = _safe_str(
            client_user.get("active_status")
        ).upper()

        # active_status controls archive state. Reject only explicit ARCHIVED.
        if active_status == "ARCHIVED":
            raise DeviceProfileServiceError(
                "Your user is archived for the selected account",
                "DEVICE_PROFILE_ACCOUNT_USER_ARCHIVED",
                403,
            )

        return client_user

    finally:
        if connection:
            connection.close()



PRODUCT_LABELS = {
    "CRM": "CRM",
    "LEADANALYTICS": "Lead Actuator",
}


def _fetch_assigned_products(
    client_database: str,
    user_id: int,
) -> list[Dict[str, Any]]:
    """
    Return every LogiKlu product assigned to this user for the selected
    client account, together with that product's own role.

    Sources:
    - Selected client DB.lk_user_permission_group
        user_id
        product
        permission_group
    - Master DB.logiklu_user_types
        id = permission_group
        type_code
        type_name
    """
    client_connection = None
    master_connection = None

    try:
        # Step 1: read the user's product assignments from the selected
        # client database.
        client_connection = get_client_connection(
            client_database
        )

        with client_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    product,
                    permission_group
                FROM lk_user_permission_group
                WHERE user_id = %s
                ORDER BY
                    CASE product
                        WHEN 'CRM' THEN 1
                        WHEN 'LEADANALYTICS' THEN 2
                        ELSE 99
                    END,
                    product
                """,
                (user_id,),
            )
            assignment_rows = cursor.fetchall() or []

        if not assignment_rows:
            return []

        role_ids = sorted(
            {
                _safe_int(
                    row.get("permission_group")
                )
                for row in assignment_rows
                if _safe_int(
                    row.get("permission_group")
                ) > 0
            }
        )

        role_map: Dict[int, Dict[str, str]] = {}

        # Step 2: resolve permission_group IDs from the MASTER database.
        if role_ids:
            placeholders = ",".join(
                ["%s"] * len(role_ids)
            )

            master_connection = get_master_connection()

            with master_connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        type_code,
                        type_name
                    FROM logiklu_user_types
                    WHERE id IN ({placeholders})
                      AND is_active = 1
                    """,
                    tuple(role_ids),
                )
                role_rows = cursor.fetchall() or []

            for row in role_rows:
                role_id = _safe_int(
                    row.get("id")
                )

                role_map[role_id] = {
                    "code": _safe_str(
                        row.get("type_code")
                    ),
                    "name": _safe_str(
                        row.get("type_name")
                    ),
                }

        products = []

        for row in assignment_rows:
            product_code = _safe_str(
                row.get("product")
            ).upper()

            role_id = _safe_int(
                row.get("permission_group")
            )

            role = role_map.get(
                role_id,
                {
                    "code": "",
                    "name": "",
                },
            )

            products.append(
                {
                    "code": product_code,
                    "label": PRODUCT_LABELS.get(
                        product_code,
                        product_code,
                    ),
                    "role": {
                        "id": (
                            role_id
                            if role_id > 0
                            else None
                        ),
                        "code": role["code"],
                        "name": role["name"],
                    },
                }
            )

        return products

    finally:
        if client_connection:
            client_connection.close()

        if master_connection:
            master_connection.close()

def _fetch_landing_page(
    landing_page_id: int,
) -> Dict[str, Any]:
    if landing_page_id <= 0:
        return {
            "id": None,
            "product": "",
            "name": "",
            "page": "",
            "url": "",
        }

    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    product,
                    name,
                    page,
                    status
                FROM logiklu_landingpages
                WHERE id = %s
                  AND status = 'active'
                LIMIT 1
                """,
                (landing_page_id,),
            )
            landing_page = cursor.fetchone()

        if not landing_page:
            return {
                "id": landing_page_id,
                "product": "",
                "name": "",
                "page": "",
                "url": "",
            }

        return {
            "id": _safe_int(landing_page.get("id")),
            "product": _safe_str(landing_page.get("product")),
            "name": _safe_str(landing_page.get("name")),
            "page": _safe_str(landing_page.get("page")),
            "url": _landing_page_url(
                product=landing_page.get("product"),
                page=landing_page.get("page"),
            ),
        }

    finally:
        if connection:
            connection.close()


def get_device_profile(
    user_id: int,
    domain_id: int,
    account_id: int,
) -> Dict[str, Any]:
    """
    Return the logged-in user's fresh profile for one selected account.

    Field sources:
    - Master zp_users:
        name, avatar, email, phone code, phone, company, designation
    - Selected client DB jos_users:
        user_type, landing_page
    - Selected client DB lk_user_permission_group:
        all assigned LogiKlu products and each product's permission_group ID
    - Master DB logiklu_user_types:
        resolves permission_group IDs to role code/name
    - Master logiklu_landingpages:
        landing page display name/product/page/url
    """
    user_id = _safe_int(user_id)
    domain_id = _safe_int(domain_id)
    account_id = _safe_int(account_id)

    if user_id <= 0:
        raise DeviceProfileServiceError(
            "Authenticated user is invalid",
            "DEVICE_PROFILE_AUTH_USER_INVALID",
            401,
        )

    if domain_id <= 0 or account_id <= 0:
        raise DeviceProfileServiceError(
            "domain_id and account_id are required",
            "DEVICE_PROFILE_ACCOUNT_REQUIRED",
            422,
        )

    user = _fetch_master_user(user_id)

    account = _fetch_account(
        domain_id=domain_id,
        account_id=account_id,
    )

    client_database = _safe_str(account.get("databasename"))

    if not client_database:
        raise DeviceProfileServiceError(
            "Selected account database is not configured",
            "DEVICE_PROFILE_DATABASE_MISSING",
            500,
        )

    client_user = _fetch_client_user(
        client_database=client_database,
        user_id=user_id,
    )

    products = _fetch_assigned_products(
        client_database=client_database,
        user_id=user_id,
    )

    user_type = _safe_str(
        client_user.get("user_type")
    ).lower()

    landing_page = _fetch_landing_page(
        landing_page_id=_safe_int(
            client_user.get("landing_page")
        ),
    )

    return {
        "user_id": user_id,
        "domain_id": domain_id,
        "account_id": account_id,
        "account_name": _safe_str(account.get("account_name")),
        "account_role": {
            "code": user_type,
            "name": USER_TYPE_DISPLAY.get(
                user_type,
                user_type.replace("_", " ").title()
                if user_type
                else "",
            ),
        },
        "products": products,
        "avatar_url": _avatar_url(
            user.get("profile_image")
        ),
        "name": _full_name(user),
        "email": _safe_str(user.get("email")),
        "phone_code": _safe_str(
            user.get("phone_country_code")
        ),
        "phone": _safe_str(user.get("phone")),
        "company": _safe_str(user.get("company")),
        "designation": _safe_str(
            user.get("designation")
        ),
        "landing_page": {
            "id": landing_page["id"],
            "name": landing_page["name"],
            "url": landing_page["url"],
        },
    }
