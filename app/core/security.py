import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Optional

from fastapi import Request, HTTPException, status

from app.config import settings
from app.db.master import get_master_connection
from app.core.response import error_response


AUTH_TIMESTAMP_TOLERANCE_SECONDS = 300


def get_api_environment() -> str:
    api_env = str(getattr(settings, "API_ENV", "production") or "production").strip().lower()

    if api_env in ["local", "development", "dev"]:
        return "local"

    if api_env == "sandbox":
        return "sandbox"

    if api_env == "staging":
        return "staging"

    return "production"


def get_setting_value(name: str, default_value: str = "") -> str:
    env_value = os.getenv(name)

    if env_value is not None and str(env_value).strip() != "":
        return str(env_value).strip()

    value = getattr(settings, name, default_value)

    if value is None:
        return default_value

    return str(value).strip()


def raise_auth_error(http_status: int, message: str, error_code: str, data=None):
    raise HTTPException(
        status_code=http_status,
        detail=error_response(
            message=message,
            error_code=error_code,
            data=data,
        ),
    )


def get_jwt_secret_key() -> str:
    secret_key = get_setting_value("JWT_SECRET_KEY", "")

    if not secret_key:
        raise_auth_error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="JWT secret key is not configured",
            error_code="AUTH_JWT_SECRET_MISSING",
        )

    return secret_key


def get_jwt_algorithm() -> str:
    algorithm = get_setting_value("JWT_ALGORITHM", "HS256")

    if algorithm != "HS256":
        raise_auth_error(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unsupported JWT algorithm",
            error_code="AUTH_JWT_ALGORITHM_UNSUPPORTED",
            data={
                "algorithm": algorithm,
            },
        )

    return algorithm


def get_jwt_access_token_expire_seconds() -> int:
    value = get_setting_value("JWT_ACCESS_TOKEN_EXPIRE_SECONDS", "900")

    try:
        seconds = int(value)
    except Exception:
        seconds = 900

    if seconds <= 0:
        seconds = 900

    return seconds


def get_jwt_issuer() -> str:
    return get_setting_value("JWT_ISSUER", "logiklu-focus-api")


def get_jwt_audiences() -> list:
    audience_value = get_setting_value("JWT_AUDIENCE", "cognitive-ai")

    audiences = [
        item.strip()
        for item in audience_value.split(",")
        if item.strip()
    ]

    if not audiences:
        audiences = ["cognitive-ai"]

    return audiences


def get_primary_jwt_audience() -> str:
    return get_jwt_audiences()[0]


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_jwt_token(payload: dict) -> str:
    get_jwt_algorithm()

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }

    header_encoded = base64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )

    payload_encoded = base64url_encode(
        json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    )

    signing_input = f"{header_encoded}.{payload_encoded}"

    signature = hmac.new(
        get_jwt_secret_key().encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    signature_encoded = base64url_encode(signature)

    return f"{signing_input}.{signature_encoded}"


def decode_and_verify_jwt_token(token: str) -> dict:
    try:
        parts = token.split(".")

        if len(parts) != 3:
            raise ValueError("JWT must contain 3 parts")

        header_encoded, payload_encoded, signature_encoded = parts
        signing_input = f"{header_encoded}.{payload_encoded}"

        expected_signature = hmac.new(
            get_jwt_secret_key().encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        actual_signature = base64url_decode(signature_encoded)

        if not hmac.compare_digest(expected_signature, actual_signature):
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid bearer token signature",
                error_code="AUTH_JWT_SIGNATURE_INVALID",
            )

        header = json.loads(base64url_decode(header_encoded).decode("utf-8"))
        payload = json.loads(base64url_decode(payload_encoded).decode("utf-8"))

        if header.get("alg") != "HS256":
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid bearer token algorithm",
                error_code="AUTH_JWT_ALGORITHM_INVALID",
            )

        current_ts = int(time.time())

        if int(payload.get("exp") or 0) < current_ts:
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Bearer token has expired",
                error_code="AUTH_JWT_EXPIRED",
            )

        if payload.get("iss") != get_jwt_issuer():
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid bearer token issuer",
                error_code="AUTH_JWT_ISSUER_INVALID",
            )

        token_audience = payload.get("aud")
        allowed_audiences = get_jwt_audiences()

        if isinstance(token_audience, list):
            audience_valid = any(aud in allowed_audiences for aud in token_audience)
        else:
            audience_valid = token_audience in allowed_audiences

        if not audience_valid:
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid bearer token audience",
                error_code="AUTH_JWT_AUDIENCE_INVALID",
                data={
                    "token_audience": token_audience,
                    "allowed_audiences": allowed_audiences,
                },
            )

        if payload.get("token_type") != "access":
            raise_auth_error(
                http_status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid bearer token type",
                error_code="AUTH_JWT_TOKEN_TYPE_INVALID",
            )

        return payload

    except HTTPException:
        raise

    except Exception:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid bearer token",
            error_code="AUTH_JWT_INVALID",
        )


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


def safe_json_decode(value, default=None):
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


def normalize_permissions(permissions_value):
    return safe_json_decode(permissions_value, {})


def extract_scope_from_permissions(permissions_value) -> str:
    permissions = normalize_permissions(permissions_value)
    scopes = set()

    if isinstance(permissions, dict):
        for key in ["scope", "scopes", "permissions"]:
            value = permissions.get(key)

            if isinstance(value, list):
                for item in value:
                    if item:
                        scopes.add(str(item).strip())

            elif isinstance(value, str):
                for item in value.replace(",", " ").split():
                    if item:
                        scopes.add(item.strip())

    elif isinstance(permissions, list):
        for item in permissions:
            if item:
                scopes.add(str(item).strip())

    if not scopes:
        scopes.add("focus:account-intelligence:read")
        scopes.add("focus:company-intelligence:read")
        scopes.add("focus:contacts:read")

    return " ".join(sorted(scopes))


def get_api_client_select_sql(where_condition: str) -> str:
    return f"""
        SELECT
            ac.api_client_id,
            ac.domain_id,
            ac.api_client_name,
            ac.oauth_client_id,

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
        WHERE {where_condition}
        LIMIT 1
    """


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
    elif api_environment == "staging":
        # Staging currently uses the production API-key columns for legacy X-API-KEY
        # compatibility because the master table does not yet have staging_api_key
        # columns. OAuth/JWT tokens are still environment-specific through API_ENV,
        # JWT_ISSUER, JWT_AUDIENCE and JWT_SECRET_KEY.
        key_condition = """
            (
                ac.production_api_key = %s
                OR ac.production_api_key_hash = %s
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
            sql = get_api_client_select_sql(key_condition)
            cursor.execute(sql, (api_key, api_key_hash))
            return cursor.fetchone()

    finally:
        if connection:
            connection.close()


def fetch_api_client_by_oauth_client_id(client_id: str) -> Optional[dict]:
    connection = None

    if not client_id:
        return None

    client_id = str(client_id).strip()

    if not client_id:
        return None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            sql = get_api_client_select_sql("ac.oauth_client_id = %s")
            cursor.execute(sql, (client_id,))
            return cursor.fetchone()

    finally:
        if connection:
            connection.close()


def validate_api_client_record(api_client: dict):
    if not api_client:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid API client",
            error_code="AUTH_INVALID_API_CLIENT",
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


def build_auth_context_from_api_client(api_client: dict, api_environment: str, auth_type: str) -> dict:
    return {
        "authenticated": True,
        "auth_type": auth_type,
        "api_environment": api_environment,
        "api_client_id": api_client.get("api_client_id"),
        "oauth_client_id": api_client.get("oauth_client_id"),
        "domain_id": api_client.get("domain_id"),
        "api_client_name": api_client.get("api_client_name"),
        "account_name": api_client.get("account_name"),
        "websitename": api_client.get("websitename"),
        "originalwebsitename": api_client.get("originalwebsitename"),
        "client_database": api_client.get("databasename"),
        "webkey": api_client.get("webkey"),
        "timezone": api_client.get("timezone"),
        "domain_type": api_client.get("domain_type"),
        "permissions": normalize_permissions(api_client.get("permissions")),
        "scope": extract_scope_from_permissions(api_client.get("permissions")),
        "rate_limit_per_minute": api_client.get("rate_limit_per_minute"),
    }


def build_auth_context_from_jwt_payload(payload: dict) -> dict:
    return {
        "authenticated": True,
        "auth_type": "jwt_bearer",
        "api_environment": payload.get("api_environment"),
        "api_client_id": payload.get("api_client_id"),
        "oauth_client_id": payload.get("oauth_client_id"),
        "domain_id": payload.get("domain_id"),
        "api_client_name": payload.get("api_client_name"),
        "account_name": payload.get("account_name"),
        "websitename": payload.get("websitename"),
        "originalwebsitename": payload.get("originalwebsitename"),
        "client_database": payload.get("client_database"),
        "webkey": payload.get("webkey"),
        "timezone": payload.get("timezone"),
        "domain_type": payload.get("domain_type"),
        "permissions": payload.get("permissions") or {},
        "scope": payload.get("scope") or "",
        "rate_limit_per_minute": payload.get("rate_limit_per_minute"),
    }


def issue_client_credentials_token(
    client_id: str,
    client_secret: str,
    grant_type: str,
    request: Request,
) -> dict:
    if grant_type != "client_credentials":
        raise_auth_error(
            http_status=status.HTTP_400_BAD_REQUEST,
            message="Unsupported grant type",
            error_code="OAUTH_UNSUPPORTED_GRANT_TYPE",
            data={
                "grant_type": grant_type,
            },
        )

    api_environment = get_api_environment()

    api_client = fetch_api_client_by_oauth_client_id(client_id)

    if not api_client:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid client credentials",
            error_code="OAUTH_INVALID_CLIENT",
        )

    validate_api_client_record(api_client)

    if not api_client.get("oauth_client_id"):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="OAuth client id is not configured",
            error_code="OAUTH_CLIENT_ID_MISSING",
        )

    stored_secret = str(api_client.get("api_secret") or "")

    if not stored_secret or not hmac.compare_digest(stored_secret, str(client_secret or "")):
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid client credentials",
            error_code="OAUTH_INVALID_CLIENT_SECRET",
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

    now_ts = int(time.time())
    expires_in = get_jwt_access_token_expire_seconds()
    scope = extract_scope_from_permissions(api_client.get("permissions"))

    payload = {
        "iss": get_jwt_issuer(),
        "aud": get_primary_jwt_audience(),
        "sub": str(api_client.get("oauth_client_id")),
        "jti": str(uuid.uuid4()),
        "token_type": "access",

        "iat": now_ts,
        "exp": now_ts + expires_in,

        "api_environment": api_environment,
        "api_client_id": api_client.get("api_client_id"),
        "oauth_client_id": api_client.get("oauth_client_id"),
        "domain_id": api_client.get("domain_id"),
        "api_client_name": api_client.get("api_client_name"),

        "account_name": api_client.get("account_name"),
        "websitename": api_client.get("websitename"),
        "originalwebsitename": api_client.get("originalwebsitename"),
        "client_database": api_client.get("databasename"),
        "webkey": api_client.get("webkey"),
        "timezone": api_client.get("timezone"),
        "domain_type": api_client.get("domain_type"),

        "permissions": normalize_permissions(api_client.get("permissions")),
        "scope": scope,
        "rate_limit_per_minute": api_client.get("rate_limit_per_minute"),
        "allowed_ips": api_client.get("allowed_ips"),
    }

    access_token = create_jwt_token(payload)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": scope,
    }


async def authenticate_bearer_request(request: Request, token: str) -> dict:
    api_environment = get_api_environment()

    payload = decode_and_verify_jwt_token(token)

    token_environment = str(payload.get("api_environment") or "").lower()

    if token_environment != api_environment:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Bearer token environment does not match current API environment",
            error_code="AUTH_JWT_ENVIRONMENT_MISMATCH",
            data={
                "token_environment": token_environment,
                "api_environment": api_environment,
            },
        )

    if not payload.get("client_database"):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="Client database is missing in bearer token",
            error_code="AUTH_JWT_CLIENT_DATABASE_MISSING",
        )

    if not payload.get("oauth_client_id"):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="OAuth client id is missing in bearer token",
            error_code="AUTH_JWT_OAUTH_CLIENT_ID_MISSING",
        )

    client_ip = get_client_ip(request)

    if not is_ip_allowed(client_ip, payload.get("allowed_ips")):
        raise_auth_error(
            http_status=status.HTTP_403_FORBIDDEN,
            message="IP address is not allowed",
            error_code="AUTH_IP_NOT_ALLOWED",
            data={
                "ip_address": client_ip,
            },
        )

    auth_context = build_auth_context_from_jwt_payload(payload)

    request.state.auth_context = auth_context

    return auth_context


async def authenticate_api_key_request(request: Request) -> dict:
    api_environment = get_api_environment()

    api_key = get_header_value(request, "X-API-KEY")
    timestamp_value = get_header_value(request, "X-TIMESTAMP")
    signature = get_header_value(request, "X-SIGNATURE")

    if not api_key:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Missing API key or bearer token",
            error_code="AUTH_CREDENTIALS_MISSING",
        )

    api_client = fetch_api_client(
        api_key=api_key,
        api_environment=api_environment,
    )

    if not api_client:
        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid API key",
            error_code="AUTH_INVALID_API_KEY",
            data={
                "environment": api_environment,
            },
        )

    validate_api_client_record(api_client)

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

    auth_context = build_auth_context_from_api_client(
        api_client=api_client,
        api_environment=api_environment,
        auth_type="api_key",
    )

    request.state.auth_context = auth_context

    return auth_context


async def authenticate_request(request: Request) -> dict:
    api_environment = get_api_environment()

    if not settings.API_AUTH_ENABLED:
        auth_context = {
            "authenticated": True,
            "auth_type": "auth_disabled",
            "api_environment": api_environment,
            "api_client_id": 0,
            "oauth_client_id": "",
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
            "scope": "",
            "rate_limit_per_minute": 0,
        }

        request.state.auth_context = auth_context

        return auth_context

    authorization = get_header_value(request, "Authorization")

    if authorization:
        parts = authorization.split(" ", 1)

        if len(parts) == 2 and parts[0].lower() == "bearer":
            return await authenticate_bearer_request(
                request=request,
                token=parts[1].strip(),
            )

        raise_auth_error(
            http_status=status.HTTP_401_UNAUTHORIZED,
            message="Invalid Authorization header. Expected Bearer token.",
            error_code="AUTHORIZATION_HEADER_INVALID",
        )

    return await authenticate_api_key_request(request)