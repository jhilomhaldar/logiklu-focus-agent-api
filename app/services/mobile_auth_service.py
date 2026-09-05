import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from app.core.mobile_auth_security import issue_mobile_user_token
from app.core.security import get_api_environment
from app.db.client import get_client_connection
from app.db.master import get_master_connection


ROOT_URL = "https://logiklu.com/"
DEFAULT_CRM_PAGE = "deals.php?action=pipeline"
DEFAULT_ANALYTICS_PAGE = "index.php"
DEFAULT_BRIDGE_URL = "https://logiklu.com/app/v1/mobile-login.php"


class MobileAuthServiceError(Exception):
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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _full_name(row: Dict[str, Any]) -> str:
    return " ".join(
        [
            value
            for value in [
                _safe_str(row.get("first_name")),
                _safe_str(row.get("last_name")),
            ]
            if value
        ]
    ).strip()


def _is_active_user_status(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "active"}


def _verify_legacy_md5_password(password: str, stored_hash: Any) -> bool:
    """
    Compatibility only.

    Existing LogiKlu users are still verified against the legacy MD5 hash
    used by the old PHP login. No new MD5 hash is written by this API.
    """
    current_hash = hashlib.md5(str(password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(current_hash.lower(), _safe_str(stored_hash).lower())


def fetch_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM zp_users
                WHERE email = %s OR username = %s
                LIMIT 1
                """,
                (username, username),
            )
            return cursor.fetchone()
    finally:
        if connection:
            connection.close()


def fetch_user_access_group(user_id: int) -> Optional[Dict[str, Any]]:
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    b.id AS access_group_id,
                    b.group_code,
                    b.group_title,
                    b.login_point
                FROM zp_access_group_user_association c
                INNER JOIN zp_access_group b
                    ON b.id = c.group_id
                WHERE c.user_id = %s
                  AND b.status = '1'
                ORDER BY b.id ASC
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone()
    finally:
        if connection:
            connection.close()


def fetch_domains_for_user(user_id: int, login_point: int) -> List[Dict[str, Any]]:
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            if login_point == 1:
                cursor.execute(
                    """
                    SELECT
                        d.account_name,
                        d.ac_id,
                        d.domain_id,
                        d.websitename,
                        d.originalwebsitename,
                        d.webkey,
                        d.databasename,
                        d.timezone
                    FROM zp_subscription_domain_info d
                    INNER JOIN zp_subscription_domain_user u
                        ON d.domain_id = u.domain_id
                    WHERE d.status = 'ACTIVE'
                      AND u.user_id = %s
                    ORDER BY d.account_name ASC, d.domain_id ASC
                    """,
                    (user_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        d.account_name,
                        d.ac_id,
                        d.domain_id,
                        d.websitename,
                        d.originalwebsitename,
                        d.webkey,
                        d.databasename,
                        d.timezone
                    FROM zp_subscription_domain_info d
                    WHERE d.status = 'ACTIVE'
                    ORDER BY d.account_name ASC, d.domain_id ASC
                    """
                )

            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()


def fetch_active_domain(domain_id: int) -> Optional[Dict[str, Any]]:
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
                    websitename,
                    originalwebsitename,
                    webkey,
                    databasename,
                    timezone
                FROM zp_subscription_domain_info
                WHERE domain_id = %s
                  AND status = 'ACTIVE'
                LIMIT 1
                """,
                (domain_id,),
            )
            return cursor.fetchone()
    finally:
        if connection:
            connection.close()


def user_has_domain_assignment(user_id: int, domain_id: int) -> bool:
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT domain_id
                FROM zp_subscription_domain_user
                WHERE user_id = %s
                  AND domain_id = %s
                LIMIT 1
                """,
                (user_id, domain_id),
            )
            return cursor.fetchone() is not None
    finally:
        if connection:
            connection.close()


def fetch_permission_group(client_database: str, user_id: int) -> Dict[str, Any]:
    connection = None
    permission_group: Dict[str, Any] = {}

    try:
        connection = get_client_connection(client_database)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT product, permission_group
                FROM lk_user_permission_group
                WHERE user_id = %s
                """,
                (user_id,),
            )
            rows = cursor.fetchall() or []

        for row in rows:
            product = _safe_str(row.get("product"))
            if product:
                permission_group[product] = row.get("permission_group")

        return permission_group
    finally:
        if connection:
            connection.close()


def fetch_landing_page_definition(
    client_database: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    client_connection = None
    master_connection = None

    try:
        client_connection = get_client_connection(client_database)
        with client_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT landing_page
                FROM jos_users
                WHERE global_user_id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            user_row = cursor.fetchone()

        landing_page_id = _safe_int((user_row or {}).get("landing_page"), 0)
        if landing_page_id <= 0:
            return None

        master_connection = get_master_connection()
        with master_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, product, page
                FROM logiklu_landingpages
                WHERE id = %s
                LIMIT 1
                """,
                (landing_page_id,),
            )
            return cursor.fetchone()
    finally:
        if client_connection:
            client_connection.close()
        if master_connection:
            master_connection.close()


def _resolve_page_url(page: str, product: str) -> str:
    page = _safe_str(page)
    product = _safe_str(product).upper()

    if product == "LEADANALYTICS":
        default_relative = DEFAULT_ANALYTICS_PAGE
        prefix = ROOT_URL + "analytic/v.2/"
    else:
        default_relative = DEFAULT_CRM_PAGE
        prefix = ROOT_URL + "app/v1/"

    if not page:
        return prefix + default_relative

    if page.startswith("https://") or page.startswith("http://"):
        return page

    if page.startswith("ROOTPATH/"):
        page = page[len("ROOTPATH/"):]

    return prefix + page.lstrip("/")


def determine_landing_page(
    client_database: str,
    user_id: int,
    permission_group: Dict[str, Any],
    login_point: int,
) -> str:
    if login_point in (2, 3):
        return _resolve_page_url(DEFAULT_CRM_PAGE, "CRM")

    has_crm = "CRM" in permission_group
    has_analytics = "LEADANALYTICS" in permission_group

    landing_definition = fetch_landing_page_definition(
        client_database=client_database,
        user_id=user_id,
    )

    if has_crm and not has_analytics:
        page = (landing_definition or {}).get("page") or DEFAULT_CRM_PAGE
        return _resolve_page_url(page, "CRM")

    if has_analytics and not has_crm:
        page = (landing_definition or {}).get("page") or DEFAULT_ANALYTICS_PAGE
        return _resolve_page_url(page, "LEADANALYTICS")

    if has_crm and has_analytics:
        product = _safe_str((landing_definition or {}).get("product")).upper()
        if product not in {"CRM", "LEADANALYTICS"}:
            product = "CRM"

        if product == "LEADANALYTICS":
            page = (landing_definition or {}).get("page") or DEFAULT_ANALYTICS_PAGE
        else:
            page = (landing_definition or {}).get("page") or DEFAULT_CRM_PAGE

        return _resolve_page_url(page, product)

    return _resolve_page_url(DEFAULT_CRM_PAGE, "CRM")


def fetch_all_access(user_id: int) -> List[Dict[str, Any]]:
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.access_type_code,
                    b.app_code
                FROM zp_access_type a
                INNER JOIN zp_applications b
                    ON a.application_id = b.id
                INNER JOIN zp_access_group_type_association d
                    ON a.id = d.type_id
                INNER JOIN zp_access_group c
                    ON c.id = d.group_id
                INNER JOIN zp_access_group_user_association e
                    ON c.id = e.group_id
                WHERE e.user_id = %s
                ORDER BY b.app_code, a.access_type_code
                """,
                (user_id,),
            )
            rows = cursor.fetchall() or []

        grouped: Dict[str, List[str]] = {}
        order: List[str] = []

        for row in rows:
            app_code = _safe_str(row.get("app_code"))
            access_code = _safe_str(row.get("access_type_code")).upper()

            if not app_code:
                continue

            if app_code not in grouped:
                grouped[app_code] = ["SUBMITFORM"]
                order.append(app_code)

            if access_code and access_code not in grouped[app_code]:
                grouped[app_code].append(access_code)

        return [{"apps": app, "task": grouped[app]} for app in order]
    finally:
        if connection:
            connection.close()


def record_login(user_id: int, client_ip: str) -> None:
    connection = None

    try:
        connection = get_master_connection()
        login_session = (
            f"mobile-{int(datetime.utcnow().timestamp())}-"
            f"{secrets.token_hex(12)}"
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO zp_user_login
                    (user_id, login_session, login_time, ip)
                VALUES
                    (%s, %s, %s, %s)
                """,
                (user_id, login_session, datetime.utcnow(), client_ip),
            )
        connection.commit()
    except Exception:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
    finally:
        if connection:
            connection.close()


def _build_public_user(user: Dict[str, Any], group: Dict[str, Any]) -> Dict[str, Any]:
    profile_image = _safe_str(user.get("profile_image"))
    avatar_url = (
        ROOT_URL + "upload/avatar/" + profile_image
        if profile_image
        else ROOT_URL + "images/gravatar.jpg"
    )

    login_point = _safe_int(group.get("login_point"), 0)

    return {
        "id": _safe_int(user.get("id")),
        "name": _full_name(user),
        "first_name": _safe_str(user.get("first_name")),
        "last_name": _safe_str(user.get("last_name")),
        "username": _safe_str(user.get("email") or user.get("username")),
        "email": _safe_str(user.get("email")),
        "company": _safe_str(user.get("company")),
        "title": _safe_str(user.get("title")),
        "avatar_url": avatar_url,
        "user_role": "member" if login_point == 1 else "admin",
        "group": {
            "id": _safe_int(group.get("access_group_id")),
            "code": _safe_str(group.get("group_code")),
            "title": _safe_str(group.get("group_title")),
            "login_point": login_point,
        },
    }


def authenticate_mobile_login(
    username: str,
    password: str,
    current_timezone: str,
    client_ip: str,
) -> Dict[str, Any]:
    username = _safe_str(username)
    password = str(password or "")
    current_timezone = _safe_str(current_timezone) or "UTC"

    if not username or not password:
        raise MobileAuthServiceError(
            "Username / email and password are required",
            "MOBILE_AUTH_CREDENTIALS_REQUIRED",
            422,
        )

    user = fetch_user_by_username(username)

    if not user:
        raise MobileAuthServiceError(
            "Invalid username or password",
            "MOBILE_AUTH_INVALID_CREDENTIALS",
            401,
        )

    if not _is_active_user_status(user.get("status")):
        raise MobileAuthServiceError(
            "This user is not active. Please contact administrator",
            "MOBILE_AUTH_USER_INACTIVE",
            403,
        )

    if not _verify_legacy_md5_password(password, user.get("password")):
        raise MobileAuthServiceError(
            "Invalid username or password",
            "MOBILE_AUTH_INVALID_CREDENTIALS",
            401,
        )

    user_id = _safe_int(user.get("id"))
    group = fetch_user_access_group(user_id)

    if not group:
        raise MobileAuthServiceError(
            "No active access group is assigned to this user",
            "MOBILE_AUTH_ACCESS_GROUP_MISSING",
            403,
        )

    login_point = _safe_int(group.get("login_point"))
    raw_domains = fetch_domains_for_user(user_id, login_point)

    domains: List[Dict[str, Any]] = []
    landing_page_map: Dict[str, str] = {}

    for domain in raw_domains:
        client_database = _safe_str(domain.get("databasename"))
        domain_id = _safe_int(domain.get("domain_id"))

        if not client_database or domain_id <= 0:
            continue

        permission_group = fetch_permission_group(client_database, user_id)
        landing_page = determine_landing_page(
            client_database,
            user_id,
            permission_group,
            login_point,
        )

        landing_page_map[str(domain_id)] = landing_page
        webkey = _safe_str(domain.get("webkey"))

        domains.append(
            {
                "domain_id": domain_id,
                "account_id": _safe_int(domain.get("ac_id")),
                "account_name": _safe_str(domain.get("account_name")),
                "website": _safe_str(domain.get("websitename")),
                "original_website": _safe_str(domain.get("originalwebsitename")),
                "webkey": webkey,
                "logo_url": (
                    ROOT_URL + "subscriber/" + webkey + "/logo/logo.png"
                    if webkey else None
                ),
                "timezone": _safe_str(domain.get("timezone")),
                "permission_group": permission_group,
                "landing_page": landing_page,
            }
        )

    token = issue_mobile_user_token(
        user_id=user_id,
        group_code=_safe_str(group.get("group_code")),
        login_point=login_point,
    )

    record_login(user_id, client_ip)

    return {
        **token,
        "user": _build_public_user(user, group),
        "assigned_domain": len(domains),
        "assigned_domains": domains,
        "landing_pages": landing_page_map,
        "landing_page": domains[0]["landing_page"] if domains else None,
        "current_timezone": current_timezone,
    }


def fetch_user_and_group_by_id(user_id: int) -> Dict[str, Any]:
    user = None
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM zp_users WHERE id = %s LIMIT 1", (user_id,))
            user = cursor.fetchone()
    finally:
        if connection:
            connection.close()

    if not user:
        raise MobileAuthServiceError(
            "User no longer exists",
            "MOBILE_AUTH_USER_NOT_FOUND",
            401,
        )

    if not _is_active_user_status(user.get("status")):
        raise MobileAuthServiceError(
            "This user is not active. Please contact administrator",
            "MOBILE_AUTH_USER_INACTIVE",
            403,
        )

    group = fetch_user_access_group(user_id)
    if not group:
        raise MobileAuthServiceError(
            "No active access group is assigned to this user",
            "MOBILE_AUTH_ACCESS_GROUP_MISSING",
            403,
        )

    return {"user": user, "group": group}


def _get_handoff_ttl_seconds() -> int:
    try:
        value = int(os.getenv("MOBILE_WEB_HANDOFF_EXPIRE_SECONDS", "3600"))
    except Exception:
        value = 3600

    if value < 15:
        value = 15
    if value > 3600:
        value = 3600

    return value


def _get_bridge_url() -> str:
    return _safe_str(os.getenv("MOBILE_WEB_BRIDGE_URL")) or DEFAULT_BRIDGE_URL


def _hash_handoff_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_php_session_payload(
    user: Dict[str, Any],
    group: Dict[str, Any],
    domain: Dict[str, Any],
    permission_group: Dict[str, Any],
    landing_page: str,
    current_timezone: str,
    check_os: str,
    check_version: str,
) -> Dict[str, Any]:
    user_id = _safe_int(user.get("id"))
    login_point = _safe_int(group.get("login_point"))
    access_group_id = _safe_int(group.get("access_group_id"))

    payload = {
        "name": _full_name(user),
        "username": _safe_str(user.get("email") or user.get("username")),
        "userid": user_id,
        "useremail": _safe_str(user.get("email")),
        "usertype": _safe_str(group.get("group_code")),
        "title": _safe_str(user.get("title")),
        "company": _safe_str(user.get("company")),
        "lk_main_user_type": _safe_str(group.get("group_code")),
        "lk_app_user_timezone": current_timezone,
        "permissiongroup": permission_group,
        "domain_id": _safe_int(domain.get("domain_id")),
        "ac_id": _safe_int(domain.get("ac_id")),
        "domain_checked": 1,
        "landing_page": landing_page,
        "check_os": check_os,
        "check_version": check_version,
        "login_point": login_point,
        "access_group_id": access_group_id,
        "domain_count": 1,
    }

    if login_point in (1, 3):
        payload["frontAccessGroupID"] = access_group_id

    if login_point in (2, 3):
        payload.update(
            {
                "backAccessGroupID": access_group_id,
                "loggedAdmin": "loggedAdmin",
                "session_userid": user_id,
                "adminid": user_id,
                "admin_name": _safe_str(user.get("first_name")),
                "f_name": _safe_str(user.get("first_name")),
                "l_name": _safe_str(user.get("last_name")),
                "ademail": _safe_str(user.get("ademail")),
                "serveraddress": _safe_str(user.get("serverip")),
                "userip": _safe_str(user.get("userip")),
                "lastlogintime": _safe_str(user.get("last_login_time")),
                "ADMINTYPE": _safe_str(group.get("group_code")),
                "ACCESS_ARRAY": fetch_all_access(user_id),
                "logged": "logged",
                "email": _safe_str(user.get("email")),
                "cpath": "..",
                "website": _safe_str(user.get("website")),
                "isadmin": 1,
            }
        )

    # Unlike the legacy PHP code, the password/hash is not placed in session.
    return payload


def create_web_session_handoff(
    user_id: int,
    token_login_point: int,
    domain_id: int,
    account_id: Optional[int],
    current_timezone: str,
    check_os: str,
    check_version: str,
    client_ip: str,
) -> Dict[str, Any]:
    identity = fetch_user_and_group_by_id(user_id)
    user = identity["user"]
    group = identity["group"]
    login_point = _safe_int(group.get("login_point"))

    if token_login_point and login_point != _safe_int(token_login_point):
        raise MobileAuthServiceError(
            "User access level has changed. Please sign in again",
            "MOBILE_AUTH_ACCESS_CHANGED",
            401,
        )

    domain = fetch_active_domain(domain_id)
    if not domain:
        raise MobileAuthServiceError(
            "Selected domain was not found or is inactive",
            "MOBILE_AUTH_DOMAIN_NOT_FOUND",
            404,
        )

    if login_point == 1 and not user_has_domain_assignment(user_id, domain_id):
        raise MobileAuthServiceError(
            "You do not have access to the selected domain",
            "MOBILE_AUTH_DOMAIN_FORBIDDEN",
            403,
        )

    if account_id is not None and _safe_int(domain.get("ac_id")) != _safe_int(account_id):
        raise MobileAuthServiceError(
            "Selected account does not match the selected domain",
            "MOBILE_AUTH_ACCOUNT_DOMAIN_MISMATCH",
            422,
        )

    client_database = _safe_str(domain.get("databasename"))
    if not client_database:
        raise MobileAuthServiceError(
            "Selected domain does not have a client database",
            "MOBILE_AUTH_CLIENT_DATABASE_MISSING",
            500,
        )

    permission_group = fetch_permission_group(client_database, user_id)
    landing_page = determine_landing_page(
        client_database,
        user_id,
        permission_group,
        login_point,
    )

    current_timezone = (
        _safe_str(current_timezone)
        or _safe_str(domain.get("timezone"))
        or "UTC"
    )

    session_payload = _build_php_session_payload(
        user=user,
        group=group,
        domain=domain,
        permission_group=permission_group,
        landing_page=landing_page,
        current_timezone=current_timezone,
        check_os=_safe_str(check_os),
        check_version=_safe_str(check_version),
    )

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_handoff_token(raw_token)
    ttl_seconds = _get_handoff_ttl_seconds()
    now = datetime.utcnow()
    expires = now + timedelta(seconds=ttl_seconds)
    api_environment = get_api_environment()

    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO logiklu_mobile_web_handoff
                (
                    token_hash,
                    api_environment,
                    user_id,
                    domain_id,
                    ac_id,
                    timezone,
                    session_payload_json,
                    request_ip,
                    created_date,
                    expires_date,
                    used_date
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                """,
                (
                    token_hash,
                    api_environment,
                    user_id,
                    _safe_int(domain.get("domain_id")),
                    _safe_int(domain.get("ac_id")),
                    current_timezone,
                    json.dumps(session_payload, separators=(",", ":"), default=str),
                    client_ip,
                    now,
                    expires,
                ),
            )
        connection.commit()
    except Exception as exc:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        raise MobileAuthServiceError(
            "Unable to create web session handoff",
            "MOBILE_WEB_SESSION_CREATE_FAILED",
            500,
            {"error": str(exc)},
        )
    finally:
        if connection:
            connection.close()

    query = urlencode({"token": raw_token, "env": api_environment})

    return {
        "handoff_token": raw_token,
        "expires_in": ttl_seconds,
        "redirect_url": _get_bridge_url() + "?" + query,
        "landing_page": landing_page,
        "domain_id": _safe_int(domain.get("domain_id")),
        "account_id": _safe_int(domain.get("ac_id")),
    }


def consume_web_session_handoff(token: str) -> Dict[str, Any]:
    token = _safe_str(token)

    if not token:
        raise MobileAuthServiceError(
            "Web session token is required",
            "MOBILE_WEB_SESSION_TOKEN_REQUIRED",
            422,
        )

    token_hash = _hash_handoff_token(token)
    api_environment = get_api_environment()
    now = datetime.utcnow()
    connection = None

    try:
        connection = get_master_connection()
        connection.begin()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM logiklu_mobile_web_handoff
                WHERE token_hash = %s
                  AND api_environment = %s
                LIMIT 1
                FOR UPDATE
                """,
                (token_hash, api_environment),
            )
            row = cursor.fetchone()

            if not row:
                raise MobileAuthServiceError(
                    "Invalid web session token",
                    "MOBILE_WEB_SESSION_TOKEN_INVALID",
                    401,
                )

            if row.get("used_date") is not None:
                raise MobileAuthServiceError(
                    "Web session token has already been used",
                    "MOBILE_WEB_SESSION_TOKEN_USED",
                    401,
                )

            expires_date = row.get("expires_date")
            if not expires_date or expires_date < now:
                raise MobileAuthServiceError(
                    "Web session token has expired",
                    "MOBILE_WEB_SESSION_TOKEN_EXPIRED",
                    401,
                )

            cursor.execute(
                """
                UPDATE logiklu_mobile_web_handoff
                SET used_date = %s
                WHERE handoff_id = %s
                  AND used_date IS NULL
                """,
                (now, row.get("handoff_id")),
            )

            if cursor.rowcount != 1:
                raise MobileAuthServiceError(
                    "Web session token could not be consumed",
                    "MOBILE_WEB_SESSION_TOKEN_CONFLICT",
                    409,
                )

        connection.commit()

        try:
            session_payload = json.loads(row.get("session_payload_json") or "{}")
        except Exception:
            session_payload = {}

        if not isinstance(session_payload, dict) or not session_payload:
            raise MobileAuthServiceError(
                "Web session data is invalid",
                "MOBILE_WEB_SESSION_DATA_INVALID",
                500,
            )

        return {"session": session_payload}

    except MobileAuthServiceError:
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
        raise MobileAuthServiceError(
            "Unable to consume web session token",
            "MOBILE_WEB_SESSION_CONSUME_FAILED",
            500,
            {"error": str(exc)},
        )
    finally:
        if connection:
            connection.close()
