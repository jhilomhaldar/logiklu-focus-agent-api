import hashlib
import json
import hmac
from typing import Any, Dict, Optional

from app.db.client import get_client_connection
from app.db.master import get_master_connection


ROOT_URL = "https://logiklu.com/"


class UserProfileServiceError(Exception):
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
            raise UserProfileServiceError(
                "User does not exist",
                "DEVICE_PROFILE_USER_NOT_FOUND",
                404,
            )

        if _safe_int(user.get("status")) != 1:
            raise UserProfileServiceError(
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
            raise UserProfileServiceError(
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
            raise UserProfileServiceError(
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
            raise UserProfileServiceError(
                "Your user is inactive for the selected account",
                "DEVICE_PROFILE_ACCOUNT_USER_INACTIVE",
                403,
            )

        active_status = _safe_str(
            client_user.get("active_status")
        ).upper()

        # active_status controls archive state. Reject only explicit ARCHIVED.
        if active_status == "ARCHIVED":
            raise UserProfileServiceError(
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


def get_user_profile(
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
        raise UserProfileServiceError(
            "Authenticated user is invalid",
            "DEVICE_PROFILE_AUTH_USER_INVALID",
            401,
        )

    if domain_id <= 0 or account_id <= 0:
        raise UserProfileServiceError(
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
        raise UserProfileServiceError(
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


def change_user_password(
    user_id: int,
    old_password: str,
    new_password: str,
    confirm_password: str,
) -> Dict[str, Any]:
    """
    Change the password for the currently logged-in LogiKlu user.

    Master DB only:
    - Verify old_password against zp_users.password (MD5).
    - Reject new_password if it is the current password.
    - Reject new_password if it matches any of the last 3 previous passwords
      stored in zp_users.password_history JSON.
    - Store the current password hash at the front of password_history.
    - Keep only the latest 3 previous password hashes.
    - Store new password directly in zp_users.password2.
    - Store MD5(new_password) in zp_users.password.

    password_history format:
        [
            "most_recent_previous_md5",
            "second_previous_md5",
            "third_previous_md5"
        ]

    The caller's user_id must come from the authenticated active session.
    """
    user_id = _safe_int(user_id)
    old_password = str(old_password or "")
    new_password = str(new_password or "")
    confirm_password = str(confirm_password or "")

    if user_id <= 0:
        raise UserProfileServiceError(
            "Authenticated user is invalid",
            "USER_PASSWORD_AUTH_USER_INVALID",
            401,
        )

    if not old_password:
        raise UserProfileServiceError(
            "Old password is required",
            "USER_PASSWORD_OLD_REQUIRED",
            422,
        )

    if not new_password:
        raise UserProfileServiceError(
            "New password is required",
            "USER_PASSWORD_NEW_REQUIRED",
            422,
        )

    if not confirm_password:
        raise UserProfileServiceError(
            "Confirm password is required",
            "USER_PASSWORD_CONFIRM_REQUIRED",
            422,
        )

    if not hmac.compare_digest(
        new_password,
        confirm_password,
    ):
        raise UserProfileServiceError(
            "New password and confirm password do not match",
            "USER_PASSWORD_CONFIRM_MISMATCH",
            422,
        )

    connection = None

    try:
        connection = get_master_connection()
        connection.begin()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    password,
                    password2,
                    password_history,
                    status
                FROM zp_users
                WHERE id = %s
                LIMIT 1
                FOR UPDATE
                """,
                (user_id,),
            )
            user = cursor.fetchone()

            if not user:
                raise UserProfileServiceError(
                    "User does not exist",
                    "USER_PASSWORD_USER_NOT_FOUND",
                    404,
                )

            if _safe_int(user.get("status")) != 1:
                raise UserProfileServiceError(
                    "This user is not active",
                    "USER_PASSWORD_USER_INACTIVE",
                    403,
                )

            stored_password = _safe_str(
                user.get("password")
            )

            current_password_md5 = (
                stored_password
                .split(":", 1)[0]
                .strip()
                .lower()
            )

            old_password_md5 = hashlib.md5(
                old_password.encode("utf-8")
            ).hexdigest().lower()

            # Step 1: old password must match the current password.
            if not hmac.compare_digest(
                old_password_md5,
                current_password_md5,
            ):
                raise UserProfileServiceError(
                    "Old password does not match",
                    "USER_PASSWORD_OLD_INVALID",
                    400,
                )

            new_password_md5 = hashlib.md5(
                new_password.encode("utf-8")
            ).hexdigest().lower()

            # Step 2: new password cannot be the current password.
            if hmac.compare_digest(
                new_password_md5,
                current_password_md5,
            ):
                raise UserProfileServiceError(
                    "New password cannot be the same as your current password",
                    "USER_PASSWORD_SAME_AS_CURRENT",
                    400,
                )

            # Step 3: read the last-3 previous password hashes from JSON.
            raw_history = user.get("password_history")
            password_history = []

            if raw_history:
                try:
                    if isinstance(raw_history, (list, tuple)):
                        parsed_history = list(raw_history)
                    else:
                        parsed_history = json.loads(
                            str(raw_history)
                        )

                    if isinstance(parsed_history, list):
                        for item in parsed_history:
                            history_hash = _safe_str(item).lower()

                            if history_hash:
                                password_history.append(
                                    history_hash
                                )
                except Exception:
                    # Invalid legacy/bad JSON should not expose data or break
                    # password changes. Treat it as no usable history.
                    password_history = []

            # Only the last 3 values are relevant even if older data contains more.
            password_history = password_history[:3]

            # Step 4: new password cannot match any of the last 3 previous hashes.
            for history_hash in password_history:
                if hmac.compare_digest(
                    new_password_md5,
                    history_hash,
                ):
                    raise UserProfileServiceError(
                        "You cannot reuse any of your last 3 passwords",
                        "USER_PASSWORD_RECENTLY_USED",
                        400,
                    )

            # Step 5: move the current password into history, newest first.
            new_history = []

            if current_password_md5:
                new_history.append(
                    current_password_md5
                )

            for history_hash in password_history:
                if (
                    history_hash
                    and history_hash not in new_history
                ):
                    new_history.append(
                        history_hash
                    )

            # Keep only the latest 3 PREVIOUS passwords.
            new_history = new_history[:3]

            # Step 6: update zp_users in one statement.
            cursor.execute(
                """
                UPDATE zp_users
                SET
                    password = %s,
                    password2 = %s,
                    password_history = %s
                WHERE id = %s
                LIMIT 1
                """,
                (
                    new_password_md5,
                    new_password,
                    json.dumps(new_history),
                    user_id,
                ),
            )

        connection.commit()

        return {
            "authentication_status": "authenticated",
            "password_changed": True,
            "password_history_rule": 3,
            "session_valid": True,
            "reauthentication_required": False,
        }

    except UserProfileServiceError:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise

    except Exception as exc:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass

        raise UserProfileServiceError(
            "Unable to change password",
            "USER_PASSWORD_CHANGE_FAILED",
            500,
            {
                "error": str(exc),
            },
        ) from exc

    finally:
        if connection:
            connection.close()

