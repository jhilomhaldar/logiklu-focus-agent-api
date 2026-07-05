from __future__ import annotations

import base64
import calendar
import hashlib
import hmac
import json
import time
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import os

from app.db.client import get_client_connection

MASTER_DB_NAME = os.getenv("MASTER_DB_NAME", "logiklu0_leadactuator")



def _table_name(table_name: str) -> str:
    """Force usage-login master tables to be read from logiklu0_leadactuator."""
    db_name = (MASTER_DB_NAME or "logiklu0_leadactuator").replace("`", "")
    safe_table = str(table_name or "").replace("`", "")
    return f"`{db_name}`.`{safe_table}`"

ENVIRONMENTS = {
    "sandbox": {
        "label": "Sandbox API",
        "url": "https://sandboxapi.logiklu.com",
        "status": "SANDBOX API",
        "table": "lk_agent_api_request_logs_sandbox",
    },
    "staging": {
        "label": "Staging API",
        "url": "https://stagingapi.logiklu.com",
        "status": "STAGING",
        "table": "lk_agent_api_request_logs_staging",
    },
    "production": {
        "label": "Live API",
        "url": "https://api.logiklu.com",
        "status": "LIVE API",
        "table": "lk_agent_api_request_logs",
    },
}

PUBLIC_REPORT_PATH_PREFIXES = (
    "/client/apiusage",
    "/instructions",
    "/masterinstruction",
    "/masterinstructions",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)


class ApiUsageError(Exception):
    pass


USAGE_SESSION_TTL_SECONDS = int(os.getenv("USAGE_SESSION_TTL_SECONDS", "28800"))


def _usage_session_secret() -> str:
    return (
        os.getenv("USAGE_SESSION_SECRET")
        or os.getenv("JWT_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or "logiklu-apiusage-session-secret-change-me"
    )


def get_usage_session_cookie_name(oauth_client_id: str) -> str:
    digest = hashlib.sha256(str(oauth_client_id or "").encode("utf-8")).hexdigest()[:16]
    return "lk_apiusage_session_" + digest


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _sign_usage_payload(payload_encoded: str) -> str:
    return hmac.new(
        _usage_session_secret().encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_usage_session_token(oauth_client_id: str, domain_id: Any, user: Dict[str, Any]) -> str:
    now_ts = int(time.time())
    payload = {
        "oauth_client_id": str(oauth_client_id or ""),
        "domain_id": _safe_int(domain_id),
        "user_id": _safe_int(user.get("id")),
        "email": str(user.get("email") or ""),
        "username": str(user.get("username") or ""),
        "name": " ".join([
            str(user.get("first_name") or "").strip(),
            str(user.get("last_name") or "").strip(),
        ]).strip(),
        "iat": now_ts,
        "exp": now_ts + max(USAGE_SESSION_TTL_SECONDS, 300),
        "token_type": "apiusage_session",
    }
    payload_encoded = _b64_encode(json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"))
    signature = _sign_usage_payload(payload_encoded)
    return payload_encoded + "." + signature


def _decode_usage_session_token(token: str) -> Optional[Dict[str, Any]]:
    token = str(token or "").strip()
    if not token or "." not in token:
        return None

    try:
        payload_encoded, signature = token.rsplit(".", 1)
        expected = _sign_usage_payload(payload_encoded)
        if not hmac.compare_digest(expected, signature):
            return None
        payload = json.loads(_b64_decode(payload_encoded).decode("utf-8"))
        if payload.get("token_type") != "apiusage_session":
            return None
        if _safe_int(payload.get("exp")) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def _verify_user_domain_access(cursor, domain_id: Any, user_id: Any) -> bool:
    table = _table_name("zp_subscription_domain_user")
    row = _fetch_one(cursor, f"""
        SELECT id
        FROM {table}
        WHERE domain_id = %s
          AND user_id = %s
          AND status = 'ACTIVE'
          AND is_admin IN ('ADMINISTRATOR', 'MODERATOR')
        LIMIT 1
    """, (_safe_int(domain_id), _safe_int(user_id)))
    return bool(row)

def get_usage_report_client(oauth_client_id: str) -> Optional[Dict[str, Any]]:
    conn = None
    cursor = None
    try:
        conn = _get_conn()
        cursor = _cursor(conn)
        return _resolve_client(cursor, oauth_client_id)
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def authenticate_usage_report_user(oauth_client_id: str, login_id: str, password: str) -> Dict[str, Any]:
    login_id = str(login_id or "").strip()
    password = str(password or "")

    if not login_id or not password:
        return {
            "valid": False,
            "message": "Please enter your email/username and password.",
        }

    conn = None
    cursor = None
    try:
        conn = _get_conn()
        cursor = _cursor(conn)
        client = _resolve_client(cursor, oauth_client_id)
        if not client:
            return {
                "valid": False,
                "message": "Invalid or inactive client access key.",
            }

        user_table = _table_name("zp_users")
        user = _fetch_one(cursor, f"""
            SELECT
                id,
                first_name,
                last_name,
                email,
                username,
                status
            FROM {user_table}
            WHERE status = 1
              AND (
                    LOWER(TRIM(COALESCE(email, ''))) = LOWER(TRIM(%s))
                 OR LOWER(TRIM(COALESCE(username, ''))) = LOWER(TRIM(%s))
              )
              AND password = MD5(%s)
            LIMIT 1
        """, (login_id, login_id, password))

        if not user:
            return {
                "valid": False,
                "message": "Invalid email/username or password.",
            }

        if not _verify_user_domain_access(cursor, client.get("domain_id"), user.get("id")):
            return {
                "valid": False,
                "message": "You do not have permission to view this API usage report.",
            }

        return {
            "valid": True,
            "client": client,
            "user": user,
            "token": create_usage_session_token(oauth_client_id, client.get("domain_id"), user),
        }

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def verify_usage_report_session(oauth_client_id: str, token: str) -> Dict[str, Any]:
    payload = _decode_usage_session_token(token)
    if not payload:
        return {"valid": False, "message": "Login required."}

    if str(payload.get("oauth_client_id") or "") != str(oauth_client_id or ""):
        return {"valid": False, "message": "Login required."}

    conn = None
    cursor = None
    try:
        conn = _get_conn()
        cursor = _cursor(conn)
        client = _resolve_client(cursor, oauth_client_id)
        if not client:
            return {"valid": False, "message": "Invalid or inactive client access key."}

        if _safe_int(client.get("domain_id")) != _safe_int(payload.get("domain_id")):
            return {"valid": False, "message": "Login required."}

        if not _verify_user_domain_access(cursor, client.get("domain_id"), payload.get("user_id")):
            return {"valid": False, "message": "You do not have permission to view this API usage report."}

        return {"valid": True, "client": client, "user": payload}

    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def _get_conn():
    return get_client_connection(MASTER_DB_NAME)


def _cursor(conn):
    try:
        return conn.cursor(dictionary=True)
    except TypeError:
        # Fallback for PyMySQL based connections.
        try:
            import pymysql  # type: ignore

            return conn.cursor(pymysql.cursors.DictCursor)
        except Exception:
            return conn.cursor()


def _fetch_one(cursor, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return row if row else None


def _fetch_all(cursor, sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return list(rows or [])


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _fmt_num(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return "0"


def _fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def _fmt_ms(value: Any) -> str:
    try:
        return f"{int(round(float(value)))}ms"
    except Exception:
        return "0ms"


def _mask_key(key: Optional[str]) -> str:
    key = key or ""
    if len(key) <= 10:
        return key
    return key[:10] + "xxxx" + key[-4:]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


DEFAULT_TIMEZONE = "Asia/Calcutta"
DEFAULT_TIMEZONE_OFFSET_MINUTES = 330


def _safe_timezone_name(timezone_name: Optional[str]) -> str:
    tz = (timezone_name or "").strip()
    return tz or DEFAULT_TIMEZONE


def _safe_timezone_offset(value: Optional[int]) -> int:
    try:
        offset = int(value) if value is not None else DEFAULT_TIMEZONE_OFFSET_MINUTES
    except Exception:
        offset = DEFAULT_TIMEZONE_OFFSET_MINUTES
    if offset < -840 or offset > 840:
        return DEFAULT_TIMEZONE_OFFSET_MINUTES
    return offset


def _local_now(tz_offset_minutes: int) -> datetime:
    return datetime.utcnow() + timedelta(minutes=tz_offset_minutes)


def _local_to_utc(local_dt: datetime, tz_offset_minutes: int) -> datetime:
    return local_dt - timedelta(minutes=tz_offset_minutes)


def _utc_to_local(utc_dt: datetime, tz_offset_minutes: int) -> datetime:
    return utc_dt + timedelta(minutes=tz_offset_minutes)


def _local_created_expr(tz_offset_minutes: int) -> str:
    # Offset is already validated by _safe_timezone_offset, so this is safe in SQL.
    offset = _safe_timezone_offset(tz_offset_minutes)
    return f"DATE_ADD(created_at, INTERVAL {offset} MINUTE)"


def _range_dates(range_key: str, date_from: Optional[str], date_to: Optional[str], tz_offset_minutes: int = DEFAULT_TIMEZONE_OFFSET_MINUTES) -> Tuple[datetime, datetime]:
    today = _local_now(tz_offset_minutes).date()
    start_date = _parse_date(date_from)
    end_date = _parse_date(date_to)

    if start_date:
        start = datetime.combine(start_date, datetime.min.time())
        if end_date:
            end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        else:
            end = datetime.combine(today + timedelta(days=1), datetime.min.time())
        return _local_to_utc(start, tz_offset_minutes), _local_to_utc(end, tz_offset_minutes)

    if range_key == "last_7_days":
        start = datetime.combine(today - timedelta(days=6), datetime.min.time())
    elif range_key == "this_month":
        start = datetime.combine(today.replace(day=1), datetime.min.time())
    else:
        start = datetime.combine(today - timedelta(days=29), datetime.min.time())

    end = datetime.combine(today + timedelta(days=1), datetime.min.time())
    return _local_to_utc(start, tz_offset_minutes), _local_to_utc(end, tz_offset_minutes)


def _month_range(tz_offset_minutes: int = DEFAULT_TIMEZONE_OFFSET_MINUTES, ref: Optional[date] = None) -> Tuple[datetime, datetime]:
    ref = ref or _local_now(tz_offset_minutes).date()
    start = datetime.combine(ref.replace(day=1), datetime.min.time())
    last_day = calendar.monthrange(ref.year, ref.month)[1]
    end = datetime.combine(ref.replace(day=last_day) + timedelta(days=1), datetime.min.time())
    return _local_to_utc(start, tz_offset_minutes), _local_to_utc(end, tz_offset_minutes)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _normalize_weekly_range(value: Optional[str]) -> str:
    value = str(value or "this_week").strip().lower()
    if value in ["last_week", "last_4_weeks"]:
        return value
    return "this_week"


def _weekly_range_label(weekly_range: str) -> str:
    weekly_range = _normalize_weekly_range(weekly_range)
    if weekly_range == "last_week":
        return "Last Week"
    if weekly_range == "last_4_weeks":
        return "Last 4 Weeks"
    return "This Week"


def _weekly_selected_bounds(weekly_range: str, tz_offset_minutes: int) -> Tuple[date, date]:
    today = _local_now(tz_offset_minutes).date()
    this_start = _week_start(today)
    weekly_range = _normalize_weekly_range(weekly_range)

    if weekly_range == "last_week":
        start = this_start - timedelta(days=7)
        end = this_start
    elif weekly_range == "last_4_weeks":
        start = this_start - timedelta(days=21)
        end = this_start + timedelta(days=7)
    else:
        start = this_start
        end = this_start + timedelta(days=7)

    return start, end


def _weekly_compare_bounds(weekly_range: str, tz_offset_minutes: int) -> Tuple[date, date, date, date]:
    weekly_range = _normalize_weekly_range(weekly_range)
    selected_start, selected_end = _weekly_selected_bounds(weekly_range, tz_offset_minutes)

    if weekly_range == "last_4_weeks":
        # Keep the daily comparison graph readable by comparing the current week with the previous week.
        today = _local_now(tz_offset_minutes).date()
        selected_start = _week_start(today)
        selected_end = selected_start + timedelta(days=7)

    previous_start = selected_start - timedelta(days=7)
    previous_end = selected_start
    return selected_start, selected_end, previous_start, previous_end


def _previous_month(d: date, months_back: int) -> date:
    month = d.month - months_back
    year = d.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _determine_selected_environment(requested_env: Optional[str]) -> str:
    # The browser report is opened by oauth_client_id, not by environment API key.
    # Any environment can be viewed from any deployment/domain, so the selected
    # tab is controlled only by the optional query parameter.
    if requested_env in ENVIRONMENTS:
        return requested_env
    return "sandbox"


def _resolve_client(cursor, oauth_client_id: str) -> Optional[Dict[str, Any]]:
    table = _table_name("lk_agent_api_clients")
    sql = f"""
        SELECT
            api_client_id,
            domain_id,
            api_client_name,
            oauth_client_id,
            api_key,
            sandbox_api_key,
            staging_api_key,
            production_api_key,
            monthly_quota,
            rate_limit,
            rate_limit_per_minute,
            status
        FROM {table}
        WHERE status = 'ACTIVE'
          AND oauth_client_id = %s
        LIMIT 1
    """
    return _fetch_one(cursor, sql, (oauth_client_id,))

def _base_where(client: Dict[str, Any], start_dt: datetime, end_dt: datetime) -> Tuple[str, Tuple[Any, ...]]:
    where_parts = [
        "api_client_id = %s",
        "domain_id = %s",
        "created_at >= %s",
        "created_at < %s",
    ]
    params: List[Any] = [
        client.get("api_client_id"),
        client.get("domain_id"),
        start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        end_dt.strftime("%Y-%m-%d %H:%M:%S"),
    ]

    # Public visual/documentation pages are intentionally excluded from usage analytics.
    # Usage report should count only secured authenticated API calls.
    for prefix in PUBLIC_REPORT_PATH_PREFIXES:
        where_parts.append("COALESCE(endpoint, '') NOT LIKE %s")
        params.append(prefix + "%")

    return " AND ".join(where_parts), tuple(params)


def _summary(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT
            COUNT(*) AS total_calls,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code BETWEEN 400 AND 499 THEN 1 ELSE 0 END) AS errors_4xx,
            SUM(CASE WHEN http_status_code >= 500 THEN 1 ELSE 0 END) AS errors_5xx,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
    """
    row = _fetch_one(cursor, sql, params) or {}
    total = _safe_int(row.get("total_calls"))
    success = _safe_int(row.get("success_calls"))
    e4 = _safe_int(row.get("errors_4xx"))
    e5 = _safe_int(row.get("errors_5xx"))
    error_calls = e4 + e5
    success_rate = (success / total * 100.0) if total else 0.0
    error_rate = (error_calls / total * 100.0) if total else 0.0
    return {
        "total": total,
        "success": success,
        "errors_4xx": e4,
        "errors_5xx": e5,
        "error_calls": error_calls,
        "success_rate": success_rate,
        "error_rate": error_rate,
        "avg_response_ms": _safe_float(row.get("avg_response_ms")),
    }


def _current_minute_count(cursor, table: str, client: Dict[str, Any]) -> int:
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(minutes=1)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"SELECT COUNT(*) AS total FROM `{table}` WHERE {where_sql}", params) or {}
    return _safe_int(row.get("total"))


def _last_success_text(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> str:
    sql = f"""
        SELECT created_at
        FROM `{table}`
        WHERE api_client_id = %s
          AND domain_id = %s
          AND http_status_code BETWEEN 200 AND 299
        ORDER BY created_at DESC
        LIMIT 1
    """
    row = _fetch_one(cursor, sql, (client.get("api_client_id"), client.get("domain_id"))) or {}
    dt = row.get("created_at")
    if not dt:
        return "No successful call"
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(dt)
    diff = datetime.utcnow() - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds} sec ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} hr ago"
    return f"{seconds // 86400} days ago"


def _p50_latency(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime) -> int:
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT execution_time_ms
        FROM `{table}`
        WHERE {where_sql}
          AND execution_time_ms IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1000
    """
    rows = _fetch_all(cursor, sql, params)
    values = sorted([_safe_int(r.get("execution_time_ms")) for r in rows if r.get("execution_time_ms") is not None])
    if not values:
        return 0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return int(round((values[mid - 1] + values[mid]) / 2.0))


def _top_error(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime) -> Tuple[str, str]:
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT
            http_status_code,
            COALESCE(NULLIF(error_code, ''), NULLIF(response_status, ''), 'UNKNOWN') AS error_text,
            COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
          AND http_status_code >= 400
        GROUP BY http_status_code, error_text
        ORDER BY total DESC, http_status_code ASC
        LIMIT 1
    """
    row = _fetch_one(cursor, sql, params) or {}
    if not row:
        return "-", "NO_ERROR"
    return str(row.get("http_status_code") or "-"), str(row.get("error_text") or "UNKNOWN")


def _top_endpoints(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime, total_calls: int) -> List[List[str]]:
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT
            COALESCE(request_method, 'GET') AS request_method,
            SUBSTRING_INDEX(COALESCE(endpoint, '/'), '?', 1) AS endpoint,
            COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY request_method, SUBSTRING_INDEX(COALESCE(endpoint, '/'), '?', 1)
        ORDER BY total DESC, endpoint ASC
    """
    rows = _fetch_all(cursor, sql, params)
    output: List[List[str]] = []
    for row in rows:
        count = _safe_int(row.get("total"))
        pct = (count / total_calls * 100.0) if total_calls else 0.0
        method = str(row.get("request_method") or "GET").upper()
        endpoint = str(row.get("endpoint") or "/")
        output.append([f"{method} {endpoint}", "API endpoint", _fmt_num(count), _fmt_pct(pct) + " of calls"])
    return output


def _endpoint_options(endpoint_rows: List[List[str]]) -> List[str]:
    values: List[str] = []
    seen = set()
    for row in endpoint_rows:
        label = row[0] if row else ""
        parts = label.split(" ", 1)
        path = parts[1] if len(parts) == 2 else label
        if path and path not in seen:
            seen.add(path)
            values.append(path)
    return values


def _format_call_row(row: Dict[str, Any], tz_offset_minutes: int) -> List[str]:
    dt = row.get("created_at")
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = None
    if isinstance(dt, datetime):
        dt_label = _utc_to_local(dt, tz_offset_minutes).strftime("%d %b %Y, %H:%M:%S")
    else:
        dt_label = str(row.get("created_at") or "")
    return [
        dt_label,
        "req_" + str(row.get("log_id") or ""),
        str(row.get("request_method") or "GET").upper(),
        str(row.get("endpoint") or "/"),
        str(row.get("http_status_code") or "-"),
        _fmt_ms(row.get("execution_time_ms")),
        str(row.get("ip_address") or "-"),
        str(row.get("api_key_prefix") or "-"),
        str(row.get("error_code") or "-"),
    ]


def _error_buckets(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime, tz_offset_minutes: int) -> List[Dict[str, Any]]:
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT
            http_status_code,
            COALESCE(NULLIF(error_code, ''), NULLIF(response_status, ''), 'UNKNOWN') AS error_text,
            COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
          AND http_status_code >= 400
        GROUP BY http_status_code, error_text
        ORDER BY http_status_code ASC, total DESC
    """
    rows = _fetch_all(cursor, sql, params)
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        status = str(row.get("http_status_code") or "-")
        total = _safe_int(row.get("total"))
        error_text = str(row.get("error_text") or "UNKNOWN")
        if status not in grouped:
            grouped[status] = {"status": status, "count_num": 0, "top_error": error_text, "top_error_count": total}
        grouped[status]["count_num"] += total
        if total > grouped[status].get("top_error_count", 0):
            grouped[status]["top_error"] = error_text
            grouped[status]["top_error_count"] = total

    buckets: List[Dict[str, Any]] = []
    for status, bucket in sorted(grouped.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 999):
        call_sql = f"""
            SELECT
                log_id,
                created_at,
                request_method,
                endpoint,
                http_status_code,
                execution_time_ms,
                ip_address,
                api_key_prefix,
                error_code
            FROM `{table}`
            WHERE {where_sql}
              AND http_status_code = %s
            ORDER BY created_at DESC
            LIMIT 100
        """
        call_rows = _fetch_all(cursor, call_sql, params + (int(status),) if status.isdigit() else params + (status,))
        buckets.append({
            "status": status,
            "count": _fmt_num(bucket.get("count_num")),
            "count_num": bucket.get("count_num", 0),
            "top_error": bucket.get("top_error") or "UNKNOWN",
            "calls": [_format_call_row(r, tz_offset_minutes) for r in call_rows],
        })
    return buckets


def _daily_trend(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime, tz_offset_minutes: int) -> Tuple[List[int], List[int]]:
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT
            DATE({local_expr}) AS day,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS failed_calls
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY DATE({local_expr})
        ORDER BY day ASC
    """
    rows = _fetch_all(cursor, sql, params)
    by_day = {str(r.get("day")): r for r in rows}
    trend: List[int] = []
    fail: List[int] = []
    d = _utc_to_local(start_dt, tz_offset_minutes).date()
    end_local_date = _utc_to_local(end_dt, tz_offset_minutes).date()
    while d < end_local_date:
        row = by_day.get(str(d))
        trend.append(_safe_int(row.get("success_calls")) if row else 0)
        fail.append(_safe_int(row.get("failed_calls")) if row else 0)
        d += timedelta(days=1)
    if not trend:
        trend = [0]
        fail = [0]
    return trend[-30:], fail[-30:]


def _selected_daily_date(daily_date: Optional[str], tz_offset_minutes: int) -> date:
    parsed = _parse_date(daily_date)
    return parsed or _local_now(tz_offset_minutes).date()


def _day_bounds(local_day: date, tz_offset_minutes: int) -> Tuple[datetime, datetime]:
    start_dt = _local_to_utc(datetime.combine(local_day, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(local_day + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    return start_dt, end_dt


def _format_hour_12(hour: int) -> str:
    hour = int(hour) % 24
    if hour == 0:
        return "12 AM"
    if hour < 12:
        return f"{hour} AM"
    if hour == 12:
        return "12 PM"
    return f"{hour - 12} PM"


def _format_hour_range_12(hour: int) -> str:
    return f"{_format_hour_12(hour)} - {_format_hour_12((hour + 1) % 24)}"


def _daily_label(local_day: date, tz_offset_minutes: int) -> str:
    today = _local_now(tz_offset_minutes).date()
    if local_day == today:
        return "Today"
    return local_day.strftime("%d %b %Y")


def _hourly_for_date(cursor, table: str, client: Dict[str, Any], local_day: date, tz_offset_minutes: int) -> Tuple[List[int], List[int]]:
    start_dt, end_dt = _day_bounds(local_day, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT
            HOUR({local_expr}) AS hour_value,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS failed_calls
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY HOUR({local_expr})
        ORDER BY hour_value ASC
    """
    rows = _fetch_all(cursor, sql, params)
    success = [0] * 24
    fail = [0] * 24
    for row in rows:
        hour = _safe_int(row.get("hour_value"), -1)
        if 0 <= hour <= 23:
            success[hour] = _safe_int(row.get("success_calls"))
            fail[hour] = _safe_int(row.get("failed_calls"))
    return success, fail


def _day_extra_metrics(cursor, table: str, client: Dict[str, Any], local_day: date, tz_offset_minutes: int) -> Dict[str, Any]:
    start_dt, end_dt = _day_bounds(local_day, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"""
        SELECT
            SUM(CASE WHEN http_status_code = 429 OR error_code = 'RATE_LIMIT' THEN 1 ELSE 0 END) AS rate_limit_hits,
            SUM(CASE WHEN execution_time_ms > 300 THEN 1 ELSE 0 END) AS slow_calls
        FROM `{table}`
        WHERE {where_sql}
    """, params) or {}
    return {
        "rate_limit_hits": _safe_int(row.get("rate_limit_hits")),
        "slow_calls": _safe_int(row.get("slow_calls")),
    }


def _peak_hour_for_date(cursor, table: str, client: Dict[str, Any], local_day: date, tz_offset_minutes: int) -> Dict[str, Any]:
    start_dt, end_dt = _day_bounds(local_day, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    row = _fetch_one(cursor, f"""
        SELECT
            HOUR({local_expr}) AS hour_value,
            COUNT(*) AS total,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY HOUR({local_expr})
        ORDER BY total DESC
        LIMIT 1
    """, params) or {}
    if not row:
        return {"peak_time": "Not available", "peak_calls": 0, "peak_response": "0ms"}
    hour = _safe_int(row.get("hour_value"), 0)
    return {
        "peak_time": _format_hour_range_12(hour),
        "peak_calls": _safe_int(row.get("total")),
        "peak_response": _fmt_ms(row.get("avg_response_ms")),
    }


def _single_day_row(cursor, table: str, client: Dict[str, Any], quota: float, local_day: date, tz_offset_minutes: int) -> List[str]:
    start_dt, end_dt = _day_bounds(local_day, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code BETWEEN 400 AND 499 THEN 1 ELSE 0 END) AS errors_4xx,
            SUM(CASE WHEN http_status_code >= 500 THEN 1 ELSE 0 END) AS errors_5xx,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
    """, params) or {}
    total = _safe_int(row.get("total"))
    quota_used = f"{(total / quota * 100.0):.2f}%" if quota else "Not Set"
    return [
        local_day.strftime("%d %b %Y"),
        _fmt_num(total),
        _fmt_num(row.get("success_calls")),
        _fmt_num(row.get("errors_4xx")),
        _fmt_num(row.get("errors_5xx")),
        _fmt_ms(row.get("avg_response_ms")),
        quota_used,
    ]


def _hourly_today(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> List[int]:
    today = _local_now(tz_offset_minutes).date()
    start_dt = _local_to_utc(datetime.combine(today, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT HOUR({local_expr}) AS hour_value, COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY HOUR({local_expr})
        ORDER BY hour_value ASC
    """
    rows = _fetch_all(cursor, sql, params)
    data = [0] * 24
    for row in rows:
        hour = _safe_int(row.get("hour_value"), -1)
        if 0 <= hour <= 23:
            data[hour] = _safe_int(row.get("total"))
    return data


def _today_extra_metrics(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> Dict[str, Any]:
    today = _local_now(tz_offset_minutes).date()
    start_dt = _local_to_utc(datetime.combine(today, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"""
        SELECT
            SUM(CASE WHEN http_status_code = 429 OR error_code = 'RATE_LIMIT' THEN 1 ELSE 0 END) AS rate_limit_hits,
            SUM(CASE WHEN execution_time_ms > 300 THEN 1 ELSE 0 END) AS slow_calls
        FROM `{table}`
        WHERE {where_sql}
    """, params) or {}
    return {
        "rate_limit_hits": _safe_int(row.get("rate_limit_hits")),
        "slow_calls": _safe_int(row.get("slow_calls")),
    }


def _peak_hour(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> Dict[str, Any]:
    today = _local_now(tz_offset_minutes).date()
    start_dt = _local_to_utc(datetime.combine(today, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    row = _fetch_one(cursor, f"""
        SELECT
            HOUR({local_expr}) AS hour_value,
            COUNT(*) AS total,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY HOUR({local_expr})
        ORDER BY total DESC
        LIMIT 1
    """, params) or {}
    if not row:
        return {"peak_time": "Not available", "peak_calls": 0, "peak_response": "0ms"}
    hour = _safe_int(row.get("hour_value"), 0)
    return {
        "peak_time": _format_hour_range_12(hour),
        "peak_calls": _safe_int(row.get("total")),
        "peak_response": _fmt_ms(row.get("avg_response_ms")),
    }


def _daily_rows(cursor, table: str, client: Dict[str, Any], quota: float, tz_offset_minutes: int) -> List[List[str]]:
    today = _local_now(tz_offset_minutes).date()
    start_dt = _local_to_utc(datetime.combine(today - timedelta(days=6), datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT
            DATE({local_expr}) AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code BETWEEN 400 AND 499 THEN 1 ELSE 0 END) AS errors_4xx,
            SUM(CASE WHEN http_status_code >= 500 THEN 1 ELSE 0 END) AS errors_5xx,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY DATE({local_expr})
        ORDER BY day DESC
    """
    rows = _fetch_all(cursor, sql, params)
    output: List[List[str]] = []
    for row in rows:
        total = _safe_int(row.get("total"))
        quota_used = f"{(total / quota * 100.0):.2f}%" if quota else "Not Set"
        day_value = row.get("day")
        if isinstance(day_value, date):
            day_label = day_value.strftime("%d %b %Y")
        else:
            day_label = str(day_value or "")
        output.append([
            day_label,
            _fmt_num(total),
            _fmt_num(row.get("success_calls")),
            _fmt_num(row.get("errors_4xx")),
            _fmt_num(row.get("errors_5xx")),
            _fmt_ms(row.get("avg_response_ms")),
            quota_used,
        ])
    if not output:
        day_label = _local_now(tz_offset_minutes).strftime("%d %b %Y")
        output.append([day_label, "0", "0", "0", "0", "0ms", "Not Set" if not quota else "0.00%"])
    return output


def _weekly_arrays(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int, weekly_range: str = "this_week") -> Tuple[List[int], List[int]]:
    selected_start, selected_end, previous_start, previous_end = _weekly_compare_bounds(weekly_range, tz_offset_minutes)
    start_dt = _local_to_utc(datetime.combine(previous_start, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(selected_end, datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT DATE({local_expr}) AS day, COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY DATE({local_expr})
    """
    rows = _fetch_all(cursor, sql, params)
    by_day = {str(r.get("day")): _safe_int(r.get("total")) for r in rows}
    selected_week = []
    previous_week = []
    for i in range(7):
        previous_week.append(by_day.get(str(previous_start + timedelta(days=i)), 0))
        selected_week.append(by_day.get(str(selected_start + timedelta(days=i)), 0))
    return selected_week, previous_week


def _weekly_rows(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int, weekly_range: str = "this_week") -> List[List[str]]:
    weekly_range = _normalize_weekly_range(weekly_range)
    selected_start, selected_end = _weekly_selected_bounds(weekly_range, tz_offset_minutes)
    start_dt = _local_to_utc(datetime.combine(selected_start, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(selected_end, datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)

    sql = f"""
        SELECT
            YEARWEEK({local_expr}, 1) AS week_key,
            MIN(DATE({local_expr})) AS min_day,
            MAX(DATE({local_expr})) AS max_day,
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS error_calls,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY YEARWEEK({local_expr}, 1)
        ORDER BY week_key DESC
    """
    rows = _fetch_all(cursor, sql, params)

    output: List[List[str]] = []
    previous_total_for_growth = _weekly_total_for_period(cursor, table, client, selected_start - timedelta(days=7), selected_start, tz_offset_minutes)

    for row in rows:
        total = _safe_int(row.get("total"))
        success = _safe_int(row.get("success_calls"))
        success_rate = (success / total * 100.0) if total else 0.0
        growth = "0.0%"
        if previous_total_for_growth:
            diff = ((total - previous_total_for_growth) / previous_total_for_growth) * 100.0
            growth = ("+" if diff >= 0 else "") + f"{diff:.1f}%"

        min_day = row.get("min_day")
        max_day = row.get("max_day")
        if isinstance(min_day, date) and isinstance(max_day, date):
            period = f"{min_day.strftime('%d %b')} - {max_day.strftime('%d %b')}"
            week_label = f"Week {min_day.isocalendar()[1]}"
        else:
            period = "-"
            week_label = str(row.get("week_key") or _weekly_range_label(weekly_range))

        if weekly_range in ["this_week", "last_week"] and output:
            continue

        output.append([
            week_label,
            period,
            _fmt_num(total),
            _fmt_pct(success_rate),
            _fmt_num(row.get("error_calls")),
            _fmt_ms(row.get("avg_response_ms")),
            growth,
        ])

    if not output:
        label = _weekly_range_label(weekly_range)
        output.append([
            label,
            f"{selected_start.strftime('%d %b')} - {(selected_end - timedelta(days=1)).strftime('%d %b')}",
            "0",
            "0.0%",
            "0",
            "0ms",
            "0.0%",
        ])

    return output


def _weekly_total_for_period(cursor, table: str, client: Dict[str, Any], start_day: date, end_day: date, tz_offset_minutes: int) -> int:
    start_dt = _local_to_utc(datetime.combine(start_day, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(end_day, datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
    """
    row = _fetch_one(cursor, sql, params) or {}
    return _safe_int(row.get("total"))


def _weekly_summary(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int, weekly_range: str = "this_week") -> Dict[str, Any]:
    weekly_range = _normalize_weekly_range(weekly_range)
    selected_start, selected_end = _weekly_selected_bounds(weekly_range, tz_offset_minutes)
    previous_total = _weekly_total_for_period(cursor, table, client, selected_start - timedelta(days=7), selected_start, tz_offset_minutes)

    start_dt = _local_to_utc(datetime.combine(selected_start, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(selected_end, datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    sql = f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS error_calls,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
    """
    row = _fetch_one(cursor, sql, params) or {}
    total = _safe_int(row.get("total"))
    success = _safe_int(row.get("success_calls"))
    errors = _safe_int(row.get("error_calls"))
    success_rate = (success / total * 100.0) if total else 0.0
    error_rate = (errors / total * 100.0) if total else 0.0
    growth = "0.0%"
    if previous_total:
        diff = ((total - previous_total) / previous_total) * 100.0
        growth = ("+" if diff >= 0 else "") + f"{diff:.1f}%"

    return {
        "weeklyRange": weekly_range,
        "weeklyRangeLabel": _weekly_range_label(weekly_range),
        "total": _fmt_num(total),
        "avgDaily": _fmt_num(round(total / 7)),
        "successRate": _fmt_pct(success_rate),
        "errorCalls": _fmt_num(errors),
        "errorRate": _fmt_pct(error_rate),
        "avgResponse": _fmt_ms(row.get("avg_response_ms")),
        "growth": growth,
        "period": f"{selected_start.strftime('%d %b')} - {(selected_end - timedelta(days=1)).strftime('%d %b')}",
    }



def _month_options(tz_offset_minutes: int) -> List[Dict[str, str]]:
    today = _local_now(tz_offset_minutes).date()
    options: List[Dict[str, str]] = []
    for i in range(6):
        month_date = _previous_month(today, i)
        month_key = month_date.strftime("%Y-%m")
        options.append({
            "value": month_key,
            "label": month_date.strftime("%B %Y"),
        })
    return options


def _normalize_month_key(month_key: Optional[str], tz_offset_minutes: int) -> str:
    allowed = [item["value"] for item in _month_options(tz_offset_minutes)]
    value = str(month_key or "").strip()
    if value in allowed:
        return value
    return allowed[0]


def _month_label(month_key: str) -> str:
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    except Exception:
        return month_key


def _month_bounds_from_key(month_key: str, tz_offset_minutes: int) -> Tuple[datetime, datetime]:
    try:
        month_date = datetime.strptime(month_key, "%Y-%m").date()
    except Exception:
        month_date = _local_now(tz_offset_minutes).date().replace(day=1)
    start_local = datetime.combine(month_date.replace(day=1), datetime.min.time())
    last_day = calendar.monthrange(month_date.year, month_date.month)[1]
    end_local = datetime.combine(month_date.replace(day=last_day) + timedelta(days=1), datetime.min.time())
    return _local_to_utc(start_local, tz_offset_minutes), _local_to_utc(end_local, tz_offset_minutes)


def _month_summary(cursor, table: str, client: Dict[str, Any], month_key: str, quota: float, tz_offset_minutes: int) -> Dict[str, Any]:
    start_dt, end_dt = _month_bounds_from_key(month_key, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS error_calls,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
    """, params) or {}
    total = _safe_int(row.get("total"))
    success = _safe_int(row.get("success_calls"))
    errors = _safe_int(row.get("error_calls"))
    success_rate = (success / total * 100.0) if total else 0.0
    quota_used = f"{(total / quota * 100.0):.0f}%" if quota else "Not Set"
    return {
        "monthKey": month_key,
        "monthLabel": _month_label(month_key),
        "total_num": total,
        "success_num": success,
        "error_num": errors,
        "total": _fmt_num(total),
        "success": _fmt_num(success),
        "errors": _fmt_num(errors),
        "successRate": _fmt_pct(success_rate),
        "avgResponse": _fmt_ms(row.get("avg_response_ms")),
        "quotaUsage": quota_used,
    }


def _monthly_endpoint_share(cursor, table: str, client: Dict[str, Any], month_key: str, total_calls: int, tz_offset_minutes: int) -> List[List[str]]:
    start_dt, end_dt = _month_bounds_from_key(month_key, tz_offset_minutes)
    return _top_endpoints(cursor, table, client, start_dt, end_dt, total_calls)


def _monthly_calendar_days(cursor, table: str, client: Dict[str, Any], month_key: str, tz_offset_minutes: int) -> List[Dict[str, Any]]:
    start_dt, end_dt = _month_bounds_from_key(month_key, tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT
            DATE({local_expr}) AS local_day,
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS error_calls
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY DATE({local_expr})
        ORDER BY local_day ASC
    """
    rows = _fetch_all(cursor, sql, params)
    by_day = {str(row.get("local_day")): row for row in rows}

    try:
        month_date = datetime.strptime(month_key, "%Y-%m").date()
    except Exception:
        month_date = _local_now(tz_offset_minutes).date().replace(day=1)

    last_day = calendar.monthrange(month_date.year, month_date.month)[1]
    result: List[Dict[str, Any]] = []
    max_total = 0
    for day in range(1, last_day + 1):
        local_day = date(month_date.year, month_date.month, day)
        row = by_day.get(str(local_day)) or {}
        total = _safe_int(row.get("total"))
        max_total = max(max_total, total)
        result.append({
            "date": local_day.strftime("%Y-%m-%d"),
            "day": day,
            "total": total,
            "success": _safe_int(row.get("success_calls")),
            "errors": _safe_int(row.get("error_calls")),
            "calls": [],
        })

    # Attach recent calls per day. The selected month has at most 31 days, so this is acceptable for a visual report.
    calls_sql = f"""
        SELECT
            log_id,
            created_at,
            request_method,
            endpoint,
            http_status_code,
            execution_time_ms,
            ip_address,
            api_key_prefix,
            error_code,
            DATE({local_expr}) AS local_day
        FROM `{table}`
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT 500
    """
    call_rows = _fetch_all(cursor, calls_sql, params)
    day_map = {item["date"]: item for item in result}
    for row in call_rows:
        key = str(row.get("local_day") or "")
        if key in day_map and len(day_map[key]["calls"]) < 100:
            day_map[key]["calls"].append(_format_call_row(row, tz_offset_minutes))

    for item in result:
        item["intensity"] = (item["total"] / max_total) if max_total else 0
    return result


def _month_rows(cursor, table: str, client: Dict[str, Any], quota: float, tz_offset_minutes: int) -> List[List[str]]:
    rows: List[List[str]] = []
    for option in _month_options(tz_offset_minutes):
        summary = _month_summary(cursor, table, client, option["value"], quota, tz_offset_minutes)
        rows.append([
            summary["monthLabel"],
            summary["total"],
            summary["success"],
            summary["errors"],
            summary["successRate"],
            summary["avgResponse"],
            summary["quotaUsage"],
        ])
    return rows


def _month_used(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> int:
    start_dt, end_dt = _month_range(tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    row = _fetch_one(cursor, f"SELECT COUNT(*) AS total FROM `{table}` WHERE {where_sql}", params) or {}
    return _safe_int(row.get("total"))


def _projected_usage(month_used: int, tz_offset_minutes: int) -> int:
    today = _local_now(tz_offset_minutes).date()
    day = max(today.day, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return int(round((month_used / float(day)) * last_day)) if month_used else 0


def _csv_values(value: Optional[str], allowed: Optional[List[str]] = None) -> List[str]:
    if not value:
        return []

    allowed_set = set([str(v).upper() for v in allowed]) if allowed else None
    values: List[str] = []
    for item in str(value).replace("|", ",").split(","):
        item = item.strip()
        if not item:
            continue
        upper = item.upper()
        if upper in ["ALL", "ALL_METHODS", "ALL_STATUSES"]:
            return []
        if allowed_set is not None and upper not in allowed_set:
            continue
        if upper not in values:
            values.append(upper)
    return values


def _calls_range_dates(
    calls_range: Optional[str],
    calls_date_from: Optional[str],
    calls_date_to: Optional[str],
    tz_offset_minutes: int,
) -> Tuple[datetime, datetime]:
    value = str(calls_range or "last_24_hours").strip().lower()
    now_local = _local_now(tz_offset_minutes)

    if value == "custom_range":
        start_date = _parse_date(calls_date_from)
        end_date = _parse_date(calls_date_to)
        if start_date and end_date:
            start = datetime.combine(start_date, datetime.min.time())
            end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
            return _local_to_utc(start, tz_offset_minutes), _local_to_utc(end, tz_offset_minutes)

    if value == "last_7_days":
        start_local = now_local - timedelta(days=7)
    elif value == "last_15_days":
        start_local = now_local - timedelta(days=15)
    elif value == "last_30_days":
        start_local = now_local - timedelta(days=30)
    else:
        start_local = now_local - timedelta(hours=24)

    return _local_to_utc(start_local, tz_offset_minutes), _local_to_utc(now_local, tz_offset_minutes)


def _detailed_calls_where(
    client: Dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
    call_search: Optional[str] = None,
    call_methods: Optional[str] = None,
    call_statuses: Optional[str] = None,
) -> Tuple[str, Tuple[Any, ...]]:
    where_sql, base_params = _base_where(client, start_dt, end_dt)
    where_parts = [where_sql]
    params: List[Any] = list(base_params)

    methods = _csv_values(call_methods, ["GET", "POST", "PUT", "PATCH", "DELETE"])
    if methods:
        placeholders = ", ".join(["%s"] * len(methods))
        where_parts.append(f"UPPER(COALESCE(request_method, '')) IN ({placeholders})")
        params.extend(methods)

    statuses = _csv_values(call_statuses, ["2XX", "3XX", "4XX", "5XX"])
    status_parts: List[str] = []
    for status in statuses:
        if status == "2XX":
            status_parts.append("http_status_code BETWEEN 200 AND 299")
        elif status == "3XX":
            status_parts.append("http_status_code BETWEEN 300 AND 399")
        elif status == "4XX":
            status_parts.append("http_status_code BETWEEN 400 AND 499")
        elif status == "5XX":
            status_parts.append("http_status_code >= 500")
    if status_parts:
        where_parts.append("(" + " OR ".join(status_parts) + ")")

    search = str(call_search or "").strip()
    if search:
        like = "%" + search + "%"
        where_parts.append("(" + " OR ".join([
            "COALESCE(endpoint, '') LIKE %s",
            "COALESCE(ip_address, '') LIKE %s",
            "COALESCE(api_key_prefix, '') LIKE %s",
            "COALESCE(error_code, '') LIKE %s",
            "CAST(log_id AS CHAR) LIKE %s",
        ]) + ")")
        params.extend([like, like, like, like, like])

    return " AND ".join(where_parts), tuple(params)


def _detailed_calls(
    cursor,
    table: str,
    client: Dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
    page: int,
    per_page: int,
    tz_offset_minutes: int,
    call_search: Optional[str] = None,
    call_methods: Optional[str] = None,
    call_statuses: Optional[str] = None,
) -> Dict[str, Any]:
    page = max(page, 1)
    per_page = max(min(per_page, 100), 1)
    offset = (page - 1) * per_page
    where_sql, params = _detailed_calls_where(
        client=client,
        start_dt=start_dt,
        end_dt=end_dt,
        call_search=call_search,
        call_methods=call_methods,
        call_statuses=call_statuses,
    )

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM `{table}`
        WHERE {where_sql}
    """
    count_row = _fetch_one(cursor, count_sql, params) or {}
    total = _safe_int(count_row.get("total"))
    total_pages = int((total + per_page - 1) / per_page) if total else 1
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * per_page

    sql = f"""
        SELECT
            log_id,
            created_at,
            request_method,
            endpoint,
            http_status_code,
            execution_time_ms,
            ip_address,
            api_key_prefix,
            error_code
        FROM `{table}`
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT {int(per_page)} OFFSET {int(offset)}
    """
    rows = _fetch_all(cursor, sql, params)

    shown_from = offset + 1 if total and rows else 0
    shown_to = offset + len(rows) if total and rows else 0

    return {
        "rows": [_format_call_row(row, tz_offset_minutes) for row in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "from": shown_from,
            "to": shown_to,
        },
    }


def _key_count(client: Dict[str, Any]) -> int:
    return sum(1 for key in [client.get("api_key"), client.get("sandbox_api_key"), client.get("staging_api_key"), client.get("production_api_key")] if key)


def _env_api_key(client: Dict[str, Any], env: str) -> str:
    if env == "sandbox":
        return _mask_key(client.get("sandbox_api_key") or client.get("api_key"))
    if env == "staging":
        return _mask_key(client.get("staging_api_key") or client.get("api_key"))
    return _mask_key(client.get("production_api_key") or client.get("api_key"))


def _build_environment_report(cursor, client: Dict[str, Any], env: str, range_key: str, date_from: Optional[str], date_to: Optional[str], page: int, per_page: int, timezone_name: str, timezone_offset_minutes: int, daily_date: Optional[str] = None, weekly_range: Optional[str] = "this_week", monthly_month: Optional[str] = None, call_search: Optional[str] = None, call_methods: Optional[str] = None, call_statuses: Optional[str] = None, calls_range: Optional[str] = "last_24_hours", calls_date_from: Optional[str] = None, calls_date_to: Optional[str] = None) -> Dict[str, Any]:
    env_conf = ENVIRONMENTS[env]
    table = env_conf["table"]
    start_dt, end_dt = _range_dates(range_key, date_from, date_to, timezone_offset_minutes)
    summary = _summary(cursor, table, client, start_dt, end_dt)
    month_used = _month_used(cursor, table, client, timezone_offset_minutes)

    monthly_quota = _safe_float(client.get("monthly_quota"), 0.0)
    rate_limit = _safe_float(client.get("rate_limit"), 0.0)
    selected_month_key = _normalize_month_key(monthly_month, timezone_offset_minutes)
    monthly_summary = _month_summary(cursor, table, client, selected_month_key, monthly_quota, timezone_offset_minutes)
    monthly_calendar = _monthly_calendar_days(cursor, table, client, selected_month_key, timezone_offset_minutes)
    monthly_endpoint_share = _monthly_endpoint_share(cursor, table, client, selected_month_key, monthly_summary.get("total_num", 0), timezone_offset_minutes)
    projected = _projected_usage(month_used, timezone_offset_minutes)

    top_error_status, top_error_text = _top_error(cursor, table, client, start_dt, end_dt)
    selected_day = _selected_daily_date(daily_date, timezone_offset_minutes)
    daily_label = _daily_label(selected_day, timezone_offset_minutes)
    today_extra = _day_extra_metrics(cursor, table, client, selected_day, timezone_offset_minutes)
    peak = _peak_hour_for_date(cursor, table, client, selected_day, timezone_offset_minutes)
    daily_success, daily_fail = _hourly_for_date(cursor, table, client, selected_day, timezone_offset_minutes)
    trend, fail = _daily_trend(cursor, table, client, start_dt, end_dt, timezone_offset_minutes)
    weekly_range_key = _normalize_weekly_range(weekly_range)
    weekly_this, weekly_prev = _weekly_arrays(cursor, table, client, timezone_offset_minutes, weekly_range_key)
    weekly_summary = _weekly_summary(cursor, table, client, timezone_offset_minutes, weekly_range_key)
    endpoints = _top_endpoints(cursor, table, client, start_dt, end_dt, summary["total"])
    calls_start_dt, calls_end_dt = _calls_range_dates(calls_range, calls_date_from, calls_date_to, timezone_offset_minutes)
    detailed_calls = _detailed_calls(
        cursor=cursor,
        table=table,
        client=client,
        start_dt=calls_start_dt,
        end_dt=calls_end_dt,
        page=page,
        per_page=per_page,
        tz_offset_minutes=timezone_offset_minutes,
        call_search=call_search,
        call_methods=call_methods,
        call_statuses=call_statuses,
    )

    total = summary["total"]
    error_calls = summary["error_calls"]

    if monthly_quota:
        quota_pct = month_used / monthly_quota * 100.0
        if quota_pct >= 90:
            suggestion = "Quota is near limit. Prepare additional quota or reduce repeated calls."
        elif quota_pct >= 70:
            suggestion = "Show a soft warning and review repeated API calls."
        else:
            suggestion = "Usage is within the configured quota."
        projected_text = _fmt_num(projected) + " calls"
    else:
        suggestion = "Monthly quota is not configured yet. Usage is shown without limit warning."
        projected_text = "Not available"

    return {
        "label": env_conf["label"],
        "timezone": timezone_name,
        "timezoneOffsetMinutes": timezone_offset_minutes,
        "dailyDate": selected_day.strftime("%Y-%m-%d"),
        "dailyDateLabel": daily_label,
        "dailyGraphTitle": daily_label + ", Hour by Hour Graph",
        "dailyCardTitle": daily_label,
        "dailyHourLabels": [_format_hour_12(i) for i in range(24)],
        "url": env_conf["url"],
        "status": env_conf["status"],
        "apiKey": _env_api_key(client, env),
        "quota": monthly_quota,
        "used": month_used,
        "rateLimit": (str(int(rate_limit)) + "/min") if rate_limit else "Not Set",
        "currentMinute": str(_current_minute_count(cursor, table, client)),
        "totalCalls": _fmt_num(total),
        "successRate": _fmt_pct(summary["success_rate"]),
        "avgResponse": _fmt_ms(summary["avg_response_ms"]),
        "errorCalls": _fmt_num(error_calls),
        "errorRate": _fmt_pct(summary["error_rate"]) + " of total calls",
        "errors4xx": _fmt_num(summary["errors_4xx"]),
        "errors5xx": _fmt_num(summary["errors_5xx"]),
        "errorPercent": _fmt_pct(summary["error_rate"]),
        "topError": top_error_status,
        "topErrorText": top_error_text,
        "reqRate": str(_current_minute_count(cursor, table, client)) + "/min",
        "p50": _fmt_ms(_p50_latency(cursor, table, client, start_dt, end_dt)),
        "uptime": _fmt_pct(summary["success_rate"]),
        "growth": "Current selected period",
        "projected": projected_text,
        "suggestion": suggestion,
        "lastSuccess": _last_success_text(cursor, table, client, timezone_offset_minutes),
        "trend": trend,
        "fail": fail,
        "daily": daily_success,
        "dailyFail": daily_fail,
        "rateLimitHits": _fmt_num(today_extra.get("rate_limit_hits")),
        "slowCalls": _fmt_num(today_extra.get("slow_calls")),
        "peakTime": peak.get("peak_time"),
        "peakCallsValue": _fmt_num(peak.get("peak_calls")),
        "peakResponseValue": peak.get("peak_response"),
        "weeklyRange": weekly_range_key,
        "weeklyRangeLabel": weekly_summary.get("weeklyRangeLabel"),
        "weeklyGraphTitle": ("This Week vs Last Week Graph" if weekly_range_key == "this_week" else ("Last Week vs Previous Week Graph" if weekly_range_key == "last_week" else "Current Week vs Last Week Graph")),
        "weeklyCurrentLabel": ("This week" if weekly_range_key != "last_week" else "Last week"),
        "weeklyPreviousLabel": ("Last week" if weekly_range_key != "last_week" else "Previous week"),
        "weeklySummary": weekly_summary,
        "weeklyThis": weekly_this,
        "weeklyPrev": weekly_prev,
        "weeklyRows": _weekly_rows(cursor, table, client, timezone_offset_minutes, weekly_range_key),
        "endpoints": endpoints,
        "endpointOptions": _endpoint_options(endpoints),
        "errorBuckets": _error_buckets(cursor, table, client, start_dt, end_dt, timezone_offset_minutes),
        "keys": str(_key_count(client)),
        "monthly": {
            "selectedMonth": selected_month_key,
            "monthLabel": monthly_summary.get("monthLabel"),
            "monthOptions": _month_options(timezone_offset_minutes),
            "summary": monthly_summary,
            "calendar": monthly_calendar,
            "endpointShare": monthly_endpoint_share,
        },
        "monthPast": _month_rows(cursor, table, client, monthly_quota, timezone_offset_minutes),
        "dailyRows": [_single_day_row(cursor, table, client, monthly_quota, selected_day, timezone_offset_minutes)],
        "calls": detailed_calls.get("rows", []),
        "callsPagination": detailed_calls.get("pagination", {"page": page, "per_page": per_page, "total": 0, "total_pages": 1, "from": 0, "to": 0}),
        "callsFilters": {
            "search": call_search or "",
            "methods": call_methods or "all",
            "statuses": call_statuses or "all",
            "range": calls_range or "last_24_hours",
            "date_from": calls_date_from or "",
            "date_to": calls_date_to or "",
        },
    }


def build_client_apiusage_report(
    oauth_client_id: str,
    environment: Optional[str] = None,
    range_key: str = "last_30_days",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    timezone: Optional[str] = None,
    timezone_offset_minutes: Optional[int] = None,
    daily_date: Optional[str] = None,
    weekly_range: Optional[str] = "this_week",
    monthly_month: Optional[str] = None,
    call_search: Optional[str] = None,
    call_methods: Optional[str] = None,
    call_statuses: Optional[str] = None,
    calls_range: Optional[str] = "last_24_hours",
    calls_date_from: Optional[str] = None,
    calls_date_to: Optional[str] = None,
) -> Dict[str, Any]:
    conn = None
    cursor = None
    try:
        conn = _get_conn()
        cursor = _cursor(conn)
        client = _resolve_client(cursor, oauth_client_id)
        if not client:
            return {
                "valid": False,
                "message": "Invalid or inactive client access key.",
            }

        selected_env = _determine_selected_environment(environment)
        timezone_name = _safe_timezone_name(timezone)
        timezone_offset = _safe_timezone_offset(timezone_offset_minutes)
        envs = {}
        for env in ["sandbox", "staging", "production"]:
            envs[env] = _build_environment_report(
                cursor,
                client,
                env,
                range_key,
                date_from,
                date_to,
                page,
                per_page,
                timezone_name,
                timezone_offset,
                daily_date,
                weekly_range,
                monthly_month,
                call_search,
                call_methods,
                call_statuses,
                calls_range,
                calls_date_from,
                calls_date_to,
            )

        return {
            "valid": True,
            "selected_environment": selected_env,
            "timezone": timezone_name,
            "timezone_offset_minutes": timezone_offset,
            "client": {
                "api_client_id": client.get("api_client_id"),
                "domain_id": client.get("domain_id"),
                "api_client_name": client.get("api_client_name"),
            },
            "envs": envs,
        }
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
