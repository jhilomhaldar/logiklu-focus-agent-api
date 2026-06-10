import json
import os
import time
from typing import Optional, Tuple

from fastapi import Request, Response
from starlette.responses import Response as StarletteResponse

from app.db.master import get_master_connection

from app.config import settings


MAX_BODY_LOG_LENGTH = 10000


def get_api_environment() -> str:
    environment = str(getattr(settings, "API_ENV", "production") or "production").strip().lower()

    if environment == "sandbox":
        return "sandbox"

    return "production"


def get_log_table_name() -> str:
    environment = get_api_environment()

    if environment == "sandbox":
        return "lk_agent_api_request_logs_sandbox"

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
    start_time = time.time()
    environment = get_api_environment()

    api_key = request.headers.get("X-API-KEY", "")
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

        auth_context = getattr(request.state, "auth_context", None)

        insert_api_request_log(
            api_client_id=auth_context.get("api_client_id") if auth_context else None,
            domain_id=auth_context.get("domain_id") if auth_context else None,
            client_database=auth_context.get("client_database") if auth_context else "",
            environment=environment,
            api_key_prefix=get_api_key_prefix(api_key),
            endpoint=str(request.url.path),
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