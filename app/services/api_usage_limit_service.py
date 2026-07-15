from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from fastapi import HTTPException, Request, status

from app.core.response import error_response
from app.db.master import get_master_connection


ENVIRONMENT_LIMIT_TABLE = "lk_api_usage_environment_limit_settings"
COUNTER_TABLE = "lk_api_usage_counters"
CLIENT_TABLE = "lk_agent_api_clients"

LIMITED_ENVIRONMENTS = ("sandbox", "staging", "production")
UNLIMITED_ENVIRONMENTS = ("development", "dev", "local")


class ApiUsageLimitError(Exception):
    pass


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _limit_value(value: Any) -> Optional[int]:
    """
    Convert a configured limit into an integer.

    NULL / empty means unlimited. BIGINT columns cannot store the text
    'infinity', but this also treats common infinity text as unlimited in case
    a future VARCHAR config is used.
    """
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("", "null", "none", "unlimited", "infinite", "infinity", "inf", "-1"):
            return None
        try:
            return int(float(text))
        except Exception:
            return None

    try:
        limit = int(value)
    except Exception:
        return None

    if limit < 0:
        return None

    return limit


def _get_timezone(timezone_name: Optional[str]):
    tz_name = _safe_str(timezone_name) or "UTC"

    if ZoneInfo:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass

    return timezone.utc


def _now_for_client(timezone_name: Optional[str]) -> datetime:
    return datetime.now(_get_timezone(timezone_name))


def _period_key(period_type: str, timezone_name: Optional[str]) -> str:
    now = _now_for_client(timezone_name)

    if period_type == "daily":
        return now.strftime("%Y-%m-%d")

    if period_type == "monthly":
        return now.strftime("%Y-%m")

    return "ALL"


def _reset_at(period_type: str, timezone_name: Optional[str]) -> Optional[str]:
    now = _now_for_client(timezone_name)

    if period_type == "daily":
        reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return reset.isoformat()

    if period_type == "monthly":
        if now.month == 12:
            reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return reset.isoformat()

    return None


def _cursor(connection):
    try:
        return connection.cursor(dictionary=True)
    except TypeError:
        try:
            import pymysql  # type: ignore
            return connection.cursor(pymysql.cursors.DictCursor)
        except Exception:
            return connection.cursor()


def _fetch_one(cursor, sql: str, params=()) -> Optional[Dict[str, Any]]:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return row if row else None


def _raise_limit_error(
    environment: str,
    period_type: str,
    limit: int,
    used: int,
    timezone_name: Optional[str],
) -> None:
    limit_label = {
        "daily": "Daily",
        "monthly": "Monthly",
        "total": "Total",
    }.get(period_type, "API")

    error_code = {
        "daily": "API_DAILY_USAGE_LIMIT_EXCEEDED",
        "monthly": "API_MONTHLY_USAGE_LIMIT_EXCEEDED",
        "total": "API_TOTAL_USAGE_LIMIT_EXCEEDED",
    }.get(period_type, "API_USAGE_LIMIT_EXCEEDED")

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=error_response(
            message=f"{limit_label} API usage limit exceeded for {environment} environment",
            error_code=error_code,
            data={
                "environment": environment,
                "limit_type": period_type,
                "limit": limit,
                "used": used,
                "reset_at": _reset_at(period_type, timezone_name),
            },
        ),
    )


def _fetch_environment_limits(cursor, environment: str) -> Dict[str, Optional[int]]:
    row = _fetch_one(
        cursor,
        f"""
        SELECT
            daily_success_limit,
            total_success_limit
        FROM `{ENVIRONMENT_LIMIT_TABLE}`
        WHERE environment = %s
          AND active_status = 'active'
        LIMIT 1
        """,
        (environment,),
    ) or {}

    return {
        "daily": _limit_value(row.get("daily_success_limit")),
        "total": _limit_value(row.get("total_success_limit")),
    }


def _fetch_production_limits(cursor, auth_context: Dict[str, Any], api_client: Optional[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    if api_client is not None:
        return {
            "monthly": _limit_value(api_client.get("production_monthly_success_limit")),
            "total": _limit_value(api_client.get("production_total_success_limit")),
        }

    api_client_id = _safe_int(auth_context.get("api_client_id"))
    oauth_client_id = _safe_str(auth_context.get("oauth_client_id"))

    where_sql = ""
    params: List[Any] = []

    if api_client_id > 0:
        where_sql = "api_client_id = %s"
        params.append(api_client_id)
    elif oauth_client_id:
        where_sql = "oauth_client_id = %s"
        params.append(oauth_client_id)
    else:
        return {"monthly": None, "total": None}

    row = _fetch_one(
        cursor,
        f"""
        SELECT
            production_monthly_success_limit,
            production_total_success_limit
        FROM `{CLIENT_TABLE}`
        WHERE {where_sql}
          AND status = 'ACTIVE'
        LIMIT 1
        """,
        tuple(params),
    ) or {}

    return {
        "monthly": _limit_value(row.get("production_monthly_success_limit")),
        "total": _limit_value(row.get("production_total_success_limit")),
    }


def _build_limit_checks(
    cursor,
    environment: str,
    auth_context: Dict[str, Any],
    api_client: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    timezone_name = auth_context.get("timezone") or (api_client or {}).get("timezone") or "UTC"

    checks: List[Dict[str, Any]] = []

    if environment in ("sandbox", "staging"):
        limits = _fetch_environment_limits(cursor, environment)
        for period_type in ("daily", "total"):
            limit = limits.get(period_type)
            if limit is not None:
                checks.append({
                    "period_type": period_type,
                    "period_key": _period_key(period_type, timezone_name),
                    "limit": limit,
                    "timezone": timezone_name,
                })
        return checks

    if environment == "production":
        limits = _fetch_production_limits(cursor, auth_context, api_client)
        for period_type in ("monthly", "total"):
            limit = limits.get(period_type)
            if limit is not None:
                checks.append({
                    "period_type": period_type,
                    "period_key": _period_key(period_type, timezone_name),
                    "limit": limit,
                    "timezone": timezone_name,
                })
        return checks

    return checks


def _ensure_counter_row(
    cursor,
    environment: str,
    oauth_client_id: str,
    api_client_id: int,
    client_database: str,
    period_type: str,
    period_key: str,
) -> None:
    cursor.execute(
        f"""
        INSERT IGNORE INTO `{COUNTER_TABLE}`
        (
            environment,
            oauth_client_id,
            api_client_id,
            client_database,
            period_type,
            period_key,
            success_count,
            inflight_count,
            created_date,
            modified_date
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, 0, 0, NOW(), NOW())
        """,
        (
            environment,
            oauth_client_id,
            api_client_id if api_client_id > 0 else None,
            client_database,
            period_type,
            period_key,
        ),
    )


def check_and_reserve_api_usage(
    request: Request,
    auth_context: Dict[str, Any],
    api_client: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Check API usage limit and reserve one in-flight request.

    Successful call counting is finalized later by request_logger after the
    endpoint response is known. Development/local is intentionally unlimited.
    """
    environment = _safe_str(auth_context.get("api_environment") or (api_client or {}).get("api_environment")).lower()

    if environment in UNLIMITED_ENVIRONMENTS:
        request.state.api_usage_reservation = None
        return

    if environment not in LIMITED_ENVIRONMENTS:
        request.state.api_usage_reservation = None
        return

    oauth_client_id = _safe_str(auth_context.get("oauth_client_id") or (api_client or {}).get("oauth_client_id"))
    api_client_id = _safe_int(auth_context.get("api_client_id") or (api_client or {}).get("api_client_id"))
    client_database = _safe_str(auth_context.get("client_database") or (api_client or {}).get("databasename"))

    if not oauth_client_id:
        request.state.api_usage_reservation = None
        return

    connection = None
    cursor = None

    try:
        connection = get_master_connection()
        cursor = _cursor(connection)

        checks = _build_limit_checks(
            cursor=cursor,
            environment=environment,
            auth_context=auth_context,
            api_client=api_client,
        )

        if not checks:
            request.state.api_usage_reservation = None
            return

        reserved: List[Dict[str, Any]] = []

        for check in checks:
            period_type = check["period_type"]
            period_key = check["period_key"]
            limit = _safe_int(check["limit"])

            _ensure_counter_row(
                cursor=cursor,
                environment=environment,
                oauth_client_id=oauth_client_id,
                api_client_id=api_client_id,
                client_database=client_database,
                period_type=period_type,
                period_key=period_key,
            )

            row = _fetch_one(
                cursor,
                f"""
                SELECT
                    counter_id,
                    success_count,
                    inflight_count
                FROM `{COUNTER_TABLE}`
                WHERE environment = %s
                  AND oauth_client_id = %s
                  AND period_type = %s
                  AND period_key = %s
                LIMIT 1
                FOR UPDATE
                """,
                (environment, oauth_client_id, period_type, period_key),
            ) or {}

            success_count = _safe_int(row.get("success_count"))
            inflight_count = _safe_int(row.get("inflight_count"))
            used = success_count + inflight_count

            if used >= limit:
                try:
                    connection.rollback()
                except Exception:
                    pass
                _raise_limit_error(
                    environment=environment,
                    period_type=period_type,
                    limit=limit,
                    used=used,
                    timezone_name=check.get("timezone"),
                )

            reserved.append({
                "counter_id": row.get("counter_id"),
                "environment": environment,
                "oauth_client_id": oauth_client_id,
                "period_type": period_type,
                "period_key": period_key,
            })

        for item in reserved:
            cursor.execute(
                f"""
                UPDATE `{COUNTER_TABLE}`
                SET inflight_count = inflight_count + 1,
                    modified_date = NOW()
                WHERE counter_id = %s
                """,
                (item.get("counter_id"),),
            )

        connection.commit()

        request.state.api_usage_reservation = {
            "environment": environment,
            "oauth_client_id": oauth_client_id,
            "counters": reserved,
        }

    except HTTPException:
        raise

    except Exception as exc:
        try:
            if connection:
                connection.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                message="Failed to check API usage limit",
                error_code="API_USAGE_LIMIT_CHECK_FAILED",
                data={"error": str(exc)},
            ),
        )

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if connection:
                connection.close()
        except Exception:
            pass


def finalize_api_usage_reservation(request: Request, success: bool) -> None:
    reservation = getattr(request.state, "api_usage_reservation", None)

    if not reservation:
        return

    counters = reservation.get("counters") or []

    if not counters:
        return

    connection = None
    cursor = None

    try:
        connection = get_master_connection()
        cursor = _cursor(connection)

        success_increment = 1 if success else 0

        for item in counters:
            counter_id = item.get("counter_id")

            if not counter_id:
                continue

            cursor.execute(
                f"""
                UPDATE `{COUNTER_TABLE}`
                SET success_count = success_count + %s,
                    inflight_count = CASE
                        WHEN inflight_count > 0 THEN inflight_count - 1
                        ELSE 0
                    END,
                    modified_date = NOW()
                WHERE counter_id = %s
                """,
                (success_increment, counter_id),
            )

        connection.commit()
        request.state.api_usage_reservation = None

    except Exception:
        try:
            if connection:
                connection.rollback()
        except Exception:
            pass
        # Finalization failure must not break the API response.
        pass

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if connection:
                connection.close()
        except Exception:
            pass
