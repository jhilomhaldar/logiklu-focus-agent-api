import hashlib
import hmac
import time
from typing import Optional

from fastapi import Request, HTTPException, status

from app.config import settings
from app.db.master import get_master_connection
from app.core.response import error_response


AUTH_TIMESTAMP_TOLERANCE_SECONDS = 300


def get_api_environment() -> str:
    api_env = str(getattr(settings, "API_ENV", "production") or "production").strip().lower()

    if api_env == "sandbox":
        return "sandbox"

    return "production"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_header_value(request: Request, name: str) -> str:
    value = request.headers.get(name)
    return value.strip() if value else ""


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return ""


def is_ip_allowed(client_ip: str, allowed_ips: Optional[str]) -> bool:
    if not allowed_ips:
        return True

    allowed_list = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]

    if not allowed_list:
        return True

    return client_ip in allowed_list


def validate_timestamp(timestamp_value: str) -> bool:
    try:
        request_ts = int(timestamp_value)
    except ValueError:
        return False

    current_ts = int(time.time())

    return abs(current_ts - request_ts) <= AUTH_TIMESTAMP_TOLERANCE_SECONDS


def build_signature_payload(
    timestamp: str,
    api_key: str,
    request_body: str = ""
) -> str:
    return f"{timestamp}.{api_key}.{request_body}"


def generate_signature(api_secret: str, payload: str) -> str:
    return hmac.new(
        api_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def raise_auth_error(http_status: int, message: str, error_code: str, data=None):
    raise HTTPException(
        status_code=http_status,
        detail=error_response(
            message=message,
            error_code=error_code,
            data=data,
        ),
    )


def fetch_api_client(api_key: str, api_environment: str) -> Optional[dict]:
    connection = None
    api_key_hash = hash_api_key(api_key)

    if api_environment == "sandbox":
        key_condition = """
            (
                ac.sandbox_api_key = %s
                OR ac.sandbox_api_key_hash = %s
            )
        """
    else:
        key_condition = """
            (
                ac.production_api_key = %s
                OR ac.production_api_key_hash = %s
            )
        """

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            sql = f"""
                SELECT
                    ac.api_client_id,
                    ac.domain_id,
                    ac.api_client_name,

                    ac.api_key,
                    ac.sandbox_api_key,
                    ac.sandbox_api_key_hash,
                    ac.production_api_key,
                    ac.production_api_key_hash,

                    ac.api_secret,
                    ac.allowed_ips,
                    ac.allowed_origins,
                    ac.permissions,
                    ac.status AS api_status,
                    ac.rate_limit_per_minute,

                    d.account_name,
                    d.websitename,
                    d.originalwebsitename,
                    d.databasename,
                    d.webkey,
                    d.subscription_product,
                    d.status AS subscription_status,
                    d.active_status,
                    d.domain_type,
                    d.timezone
                FROM lk_agent_api_clients ac
                INNER JOIN zp_subscription_domain_info d
                    ON d.domain_id = ac.domain_id
                WHERE {key_condition}
                LIMIT 1
            """

            cursor.execute(sql, (api_key, api_key_hash))

            return cursor.fetchone()

    finally:
        if connection:
            connection.close()


async def authenticate_request(request: Request) -> dict:
    api_environment = get_api_environment()

    if not settings.API_AUTH_ENABLED:
        auth_context = {
            "authenticated": True,
            "api_environment": api_environment,
            "api_client_id": 0,
            "domain_id": 0,
            "api_client_name": "auth_disabled",
            "account_name": "",
            "websitename": "",
            "originalwebsitename": "",
            "client_database": "",
            "webkey": "",
            "timezone": "UTC",
            "domain_type": "",
            "permissions": {},
            "rate_limit_per_minute": 0,
        }

        request.state.auth_context = auth_context

        return auth_context

    api_key = get_header_value(request, "X-API-KEY")
    timestamp_value = get_header_value(request, "X-TIMESTAMP")
    signature = get_header_value(request, "X-SIGNATURE")

    if not api_key:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Missing API key",
            error_code="AUTH_API_KEY_MISSING",
        )

    api_client = fetch_api_client(
        api_key=api_key,
        api_environment=api_environment,
    )

    if not api_client:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message=f"Invalid API key",
            error_code="AUTH_INVALID_API_KEY",
            data={
                "environment": api_environment,
            },
        )

    if api_client.get("api_status") != "ACTIVE":
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="API client is not active",
            error_code="AUTH_API_CLIENT_INACTIVE",
        )

    if api_client.get("subscription_status") != "ACTIVE":
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="Client subscription is not active",
            error_code="AUTH_SUBSCRIPTION_INACTIVE",
        )

    if api_client.get("active_status") != "ACTIVE":
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="Client account is not active",
            error_code="AUTH_CLIENT_ACCOUNT_INACTIVE",
        )

    if not api_client.get("databasename"):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="Client database is not configured",
            error_code="AUTH_CLIENT_DATABASE_MISSING",
        )

    client_ip = get_client_ip(request)

    if not is_ip_allowed(client_ip, api_client.get("allowed_ips")):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="IP address is not allowed",
            error_code="AUTH_IP_NOT_ALLOWED",
            data={
                "ip_address": client_ip,
            },
        )

    if settings.API_SIGNATURE_REQUIRED:
        if not timestamp_value or not signature:
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Missing signature headers",
                error_code="AUTH_SIGNATURE_HEADERS_MISSING",
            )

        if not validate_timestamp(timestamp_value):
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid or expired timestamp",
                error_code="AUTH_TIMESTAMP_INVALID",
            )

        body_bytes = await request.body()
        request_body = body_bytes.decode("utf-8") if body_bytes else ""

        payload = build_signature_payload(
            timestamp=timestamp_value,
            api_key=api_key,
            request_body=request_body,
        )

        expected_signature = generate_signature(
            api_client["api_secret"],
            payload
        )

        if not hmac.compare_digest(expected_signature, signature):
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid request signature",
                error_code="AUTH_SIGNATURE_INVALID",
            )

    auth_context = {
        "authenticated": True,
        "api_environment": api_environment,
        "api_client_id": api_client.get("api_client_id"),
        "domain_id": api_client.get("domain_id"),
        "api_client_name": api_client.get("api_client_name"),
        "account_name": api_client.get("account_name"),
        "websitename": api_client.get("websitename"),
        "originalwebsitename": api_client.get("originalwebsitename"),
        "client_database": api_client.get("databasename"),
        "webkey": api_client.get("webkey"),
        "timezone": api_client.get("timezone"),
        "domain_type": api_client.get("domain_type"),
        "permissions": api_client.get("permissions"),
        "rate_limit_per_minute": api_client.get("rate_limit_per_minute"),
    }

    request.state.auth_context = auth_context

    return auth_context