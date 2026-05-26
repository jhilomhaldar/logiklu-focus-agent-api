import json
import time
from typing import Optional

from fastapi import Request, Response

from app.db.master import get_master_connection


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


def insert_api_request_log(
    api_client_id: Optional[int],
    domain_id: Optional[int],
    client_database: str,
    api_key_prefix: str,
    endpoint: str,
    request_method: str,
    ip_address: str,
    user_agent: str,
    request_params: str,
    http_status_code: int,
    response_status: str,
    error_code: str,
    error_message: str,
    execution_time_ms: int,
) -> None:
    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            sql = """
                INSERT INTO lk_agent_api_request_logs
                (
                    api_client_id,
                    domain_id,
                    client_database,
                    api_key_prefix,
                    endpoint,
                    request_method,
                    ip_address,
                    user_agent,
                    request_params,
                    http_status_code,
                    response_status,
                    error_code,
                    error_message,
                    execution_time_ms,
                    created_at
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """

            cursor.execute(
                sql,
                (
                    api_client_id,
                    domain_id,
                    client_database,
                    api_key_prefix,
                    endpoint,
                    request_method,
                    ip_address,
                    user_agent,
                    request_params,
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

    response: Response = await call_next(request)

    execution_time_ms = int((time.time() - start_time) * 1000)

    auth_context = getattr(request.state, "auth_context", None)
    api_key = request.headers.get("X-API-KEY", "")

    response_status = "success" if response.status_code < 400 else "error"

    insert_api_request_log(
        api_client_id=auth_context.get("api_client_id") if auth_context else None,
        domain_id=auth_context.get("domain_id") if auth_context else None,
        client_database=auth_context.get("client_database") if auth_context else "",
        api_key_prefix=get_api_key_prefix(api_key),
        endpoint=str(request.url.path),
        request_method=request.method,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        request_params=safe_request_params(request),
        http_status_code=response.status_code,
        response_status=response_status,
        error_code="",
        error_message="",
        execution_time_ms=execution_time_ms,
    )

    return response