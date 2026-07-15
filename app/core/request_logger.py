import json
import os
import time
from typing import Optional, Tuple

from fastapi import Request, Response
from starlette.responses import Response as StarletteResponse

from app.db.master import get_master_connection

from app.config import settings
from app.core.security import decode_and_verify_jwt_token, build_auth_context_from_jwt_payload
from app.services.api_usage_limit_service import finalize_api_usage_reservation


MAX_BODY_LOG_LENGTH = 10000


NO_API_LOG_PATH_PREFIXES = (
    "/client/apiusage",
    "/instructions",
    "/masterinstruction",
    "/masterinstructions",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/static",
)


def should_skip_api_log_path(path: str) -> bool:
    path = str(path or "")

    for prefix in NO_API_LOG_PATH_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


def get_bearer_token_from_request(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")

    if not authorization:
        return ""

    parts = authorization.split(" ", 1)

    if len(parts) != 2:
        return ""

    if parts[0].strip().lower() != "bearer":
        return ""

    return parts[1].strip()


def get_jwt_api_key_prefix(auth_context: dict) -> str:
    oauth_client_id = str(auth_context.get("oauth_client_id") or "").strip()

    if oauth_client_id:
        return ("jwt:" + oauth_client_id)[:30]

    api_client_id = auth_context.get("api_client_id")

    if api_client_id:
        return ("jwt_client:" + str(api_client_id))[:30]

    return "jwt_bearer"


def resolve_bearer_auth_context_for_logging(request: Request) -> Optional[dict]:
    """
    Resolve the client context directly from a Bearer JWT before route handling.

    This is required for invalid-route calls such as /rolesa. Those calls never
    reach endpoint-level dependencies, so request.state.auth_context would remain
    empty unless the logger resolves the token itself.
    """

    token = get_bearer_token_from_request(request)

    if not token:
        return None

    try:
        payload = decode_and_verify_jwt_token(token)
        auth_context = build_auth_context_from_jwt_payload(payload)

        if not auth_context.get("api_client_id") or not auth_context.get("domain_id"):
            return None

        request.state.auth_context = auth_context

        return auth_context

    except Exception:
        # Invalid/expired/malformed Bearer tokens are not authenticated API calls.
        # Do not log them in client usage reports.
        return None


def get_api_environment() -> str:
    """
    Resolve the current API environment for request logging.

    Supported environments:
    - development / dev / local
    - sandbox
    - staging
    - production / prod / live

    Unknown values fall back to production so table selection always remains safe.
    """

    environment = str(
        getattr(settings, "API_ENV", "production") or "production"
    ).strip().lower()

    if environment in ["development", "dev", "local"]:
        return "development"

    if environment in ["production", "prod", "live"]:
        return "production"

    if environment == "sandbox":
        return "sandbox"

    if environment == "staging":
        return "staging"

    return "production"


def get_log_table_name() -> str:
    """
    Return a fixed whitelist table name for the current environment.
    Do not build this from user input.
    """

    environment = get_api_environment()

    if environment == "development":
        return "lk_agent_api_request_logs_development"

    if environment == "sandbox":
        return "lk_agent_api_request_logs_sandbox"

    if environment == "staging":
        return "lk_agent_api_request_logs_staging"

    return "lk_agent_api_request_logs"


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return ""


def get_api_key_prefix(api_key: str) -> str:
    if not api_key:
        return ""

    return api_key[:18]


def safe_request_params(request: Request) -> str:
    try:
        params = dict(request.query_params)
        return json.dumps(params, default=str)
    except Exception:
        return ""


def safe_decode_body(body_bytes: bytes) -> str:
    if not body_bytes:
        return ""

    try:
        body_text = body_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""

    if len(body_text) > MAX_BODY_LOG_LENGTH:
        return body_text[:MAX_BODY_LOG_LENGTH] + "...[TRUNCATED]"

    return body_text


def should_log_request_body(request: Request) -> bool:
    return request.method.upper() in ["POST", "PUT", "PATCH", "DELETE"]


async def set_body_for_downstream(request: Request, body: bytes) -> None:
    async def receive():
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    request._receive = receive


def extract_error_from_response_body(response_body: bytes) -> Tuple[str, str]:
    if not response_body:
        return "", ""

    try:
        parsed = json.loads(response_body.decode("utf-8", errors="replace"))

        if isinstance(parsed, dict):
            detail = parsed.get("detail")

            if isinstance(detail, dict):
                return (
                    str(detail.get("error_code") or ""),
                    str(detail.get("message") or detail.get("detail") or ""),
                )

            return (
                str(parsed.get("error_code") or ""),
                str(parsed.get("message") or parsed.get("detail") or ""),
            )

    except Exception:
        pass

    return "", ""


async def rebuild_response(response: Response) -> Tuple[Response, bytes]:
    response_body = b""

    async for chunk in response.body_iterator:
        response_body += chunk

    rebuilt_response = StarletteResponse(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )

    return rebuilt_response, response_body


def insert_api_request_log(
    api_client_id: Optional[int],
    domain_id: Optional[int],
    client_database: str,
    environment: str,
    api_key_prefix: str,
    endpoint: str,
    request_method: str,
    ip_address: str,
    user_agent: str,
    request_params: str,
    request_body: str,
    http_status_code: int,
    response_status: str,
    error_code: str,
    error_message: str,
    execution_time_ms: int,
) -> None:
    connection = None
    table_name = get_log_table_name()

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            sql = f"""
                INSERT INTO `{table_name}`
                (
                    api_client_id,
                    domain_id,
                    client_database,
                    environment,
                    api_key_prefix,
                    endpoint,
                    request_method,
                    ip_address,
                    user_agent,
                    request_params,
                    request_body,
                    http_status_code,
                    response_status,
                    error_code,
                    error_message,
                    execution_time_ms,
                    created_at
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """

            cursor.execute(
                sql,
                (
                    api_client_id,
                    domain_id,
                    client_database,
                    environment,
                    api_key_prefix,
                    endpoint,
                    request_method,
                    ip_address,
                    user_agent,
                    request_params,
                    request_body,
                    http_status_code,
                    response_status,
                    error_code,
                    error_message,
                    execution_time_ms,
                ),
            )

    except Exception:
        # Logging must never break the API response.
        pass

    finally:
        if connection:
            connection.close()


async def api_request_logger_middleware(request: Request, call_next):
    path = str(request.url.path)

    if should_skip_api_log_path(path):
        return await call_next(request)

    # Bearer requests can be resolved before route handling, which allows even
    # invalid-route authenticated calls to be logged. X-API-KEY requests are
    # resolved later inside endpoint dependencies, so we do not skip early when
    # this is empty.
    auth_context = resolve_bearer_auth_context_for_logging(request)

    start_time = time.time()
    environment = get_api_environment()

    request_body = ""
    body_bytes = b""

    if should_log_request_body(request):
        try:
            body_bytes = await request.body()
            request_body = safe_decode_body(body_bytes)
            await set_body_for_downstream(request, body_bytes)
        except Exception:
            request_body = ""

    response_status_code = 500
    response_status = "error"
    error_code = ""
    error_message = ""
    response = None

    try:
        response = await call_next(request)
        response_status_code = response.status_code
        response_status = "success" if response.status_code < 400 else "error"

        rebuilt_response, response_body = await rebuild_response(response)

        if response.status_code >= 400:
            error_code, error_message = extract_error_from_response_body(response_body)

        response = rebuilt_response

    except Exception as exc:
        response_status_code = 500
        response_status = "error"
        error_code = "UNHANDLED_EXCEPTION"
        error_message = str(exc)
        raise

    finally:
        execution_time_ms = int((time.time() - start_time) * 1000)

        auth_context = getattr(request.state, "auth_context", None) or auth_context

        # Only 2xx responses consume successful usage quota.
        finalize_api_usage_reservation(
            request=request,
            success=(200 <= int(response_status_code or 0) <= 299),
        )

        # Usage logs are only for secured authenticated API calls. Public pages,
        # OAuth token calls, browser pages, and unauthenticated hits are not
        # inserted into lk_agent_api_request_logs*.
        if auth_context and auth_context.get("api_client_id") and auth_context.get("domain_id"):
            insert_api_request_log(
                api_client_id=auth_context.get("api_client_id"),
                domain_id=auth_context.get("domain_id"),
                client_database=auth_context.get("client_database") or "",
                environment=environment,
                api_key_prefix=get_jwt_api_key_prefix(auth_context or {}),
                endpoint=path,
                request_method=request.method,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                request_params=safe_request_params(request),
                request_body=request_body,
                http_status_code=response_status_code,
                response_status=response_status,
                error_code=error_code,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
            )

    return response

