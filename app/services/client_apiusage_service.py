from __future__ import annotations

import calendar
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import os

from app.db.client import get_client_connection

MASTER_DB_NAME = os.getenv("MASTER_DB_NAME", "logiklu0_leadactuator")

ENVIRONMENTS = {
    "sandbox": {
        "label": "Sandbox",
        "url": "https://sandboxapi.logiklu.com",
        "status": "SANDBOX LIVE",
        "table": "lk_agent_api_request_logs_sandbox",
    },
    "staging": {
        "label": "Stage / Staging",
        "url": "https://stagingapi.logiklu.com",
        "status": "STAGING TEST",
        "table": "lk_agent_api_request_logs_staging",
    },
    "production": {
        "label": "Production",
        "url": "https://api.logiklu.com",
        "status": "PRODUCTION LIVE",
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
    sql = """
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
        FROM lk_agent_api_clients
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


def _weekly_arrays(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> Tuple[List[int], List[int]]:
    today = _local_now(tz_offset_minutes).date()
    this_start = _week_start(today)
    prev_start = this_start - timedelta(days=7)
    start_dt = _local_to_utc(datetime.combine(prev_start, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(this_start + timedelta(days=7), datetime.min.time()), tz_offset_minutes)
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
    this_week = []
    prev_week = []
    for i in range(7):
        prev_week.append(by_day.get(str(prev_start + timedelta(days=i)), 0))
        this_week.append(by_day.get(str(this_start + timedelta(days=i)), 0))
    return this_week, prev_week


def _weekly_rows(cursor, table: str, client: Dict[str, Any], tz_offset_minutes: int) -> List[List[str]]:
    today = _local_now(tz_offset_minutes).date()
    this_start = _week_start(today)
    start_dt = _local_to_utc(datetime.combine(this_start - timedelta(days=14), datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(this_start + timedelta(days=7), datetime.min.time()), tz_offset_minutes)
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
        LIMIT 3
    """
    rows = _fetch_all(cursor, sql, params)
    output: List[List[str]] = []
    previous_total: Optional[int] = None
    for row in rows:
        total = _safe_int(row.get("total"))
        success = _safe_int(row.get("success_calls"))
        success_rate = (success / total * 100.0) if total else 0.0
        growth = "0.0%"
        if previous_total is not None and previous_total:
            diff = ((total - previous_total) / previous_total) * 100.0
            growth = ("+" if diff >= 0 else "") + f"{diff:.1f}%"
        min_day = row.get("min_day")
        max_day = row.get("max_day")
        if isinstance(min_day, date) and isinstance(max_day, date):
            period = f"{min_day.strftime('%d %b')} - {max_day.strftime('%d %b')}"
            week_label = f"Week {min_day.isocalendar()[1]}"
        else:
            period = "-"
            week_label = str(row.get("week_key") or "Week")
        output.append([
            week_label,
            period,
            _fmt_num(total),
            _fmt_pct(success_rate),
            _fmt_num(row.get("error_calls")),
            _fmt_ms(row.get("avg_response_ms")),
            growth,
        ])
        previous_total = total
    if not output:
        today = _local_now(tz_offset_minutes).date()
        ws = _week_start(today)
        output.append([f"Week {ws.isocalendar()[1]}", f"{ws.strftime('%d %b')} - {(ws + timedelta(days=6)).strftime('%d %b')}", "0", "0.0%", "0", "0ms", "0.0%"])
    return output


def _month_rows(cursor, table: str, client: Dict[str, Any], quota: float, tz_offset_minutes: int) -> List[List[str]]:
    today = _local_now(tz_offset_minutes).date()
    start_ref = _previous_month(today, 2)
    start_dt = _local_to_utc(datetime.combine(start_ref, datetime.min.time()), tz_offset_minutes)
    end_dt = _local_to_utc(datetime.combine(today + timedelta(days=1), datetime.min.time()), tz_offset_minutes)
    where_sql, params = _base_where(client, start_dt, end_dt)
    local_expr = _local_created_expr(tz_offset_minutes)
    sql = f"""
        SELECT
            DATE_FORMAT({local_expr}, '%%Y-%%m') AS month_key,
            COUNT(*) AS total,
            SUM(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS success_calls,
            SUM(CASE WHEN http_status_code >= 400 THEN 1 ELSE 0 END) AS error_calls,
            AVG(execution_time_ms) AS avg_response_ms
        FROM `{table}`
        WHERE {where_sql}
        GROUP BY DATE_FORMAT({local_expr}, '%%Y-%%m')
        ORDER BY month_key DESC
        LIMIT 3
    """
    rows = _fetch_all(cursor, sql, params)
    output: List[List[str]] = []
    for row in rows:
        month_key = str(row.get("month_key") or "")
        try:
            month_label = datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
        except Exception:
            month_label = month_key
        total = _safe_int(row.get("total"))
        success = _safe_int(row.get("success_calls"))
        success_rate = (success / total * 100.0) if total else 0.0
        quota_used = f"{(total / quota * 100.0):.0f}%" if quota else "Not Set"
        output.append([
            month_label,
            _fmt_num(total),
            _fmt_num(success),
            _fmt_num(row.get("error_calls")),
            _fmt_pct(success_rate),
            _fmt_ms(row.get("avg_response_ms")),
            quota_used,
        ])
    if not output:
        output.append([_local_now(tz_offset_minutes).strftime("%B %Y"), "0", "0", "0", "0.0%", "0ms", "Not Set" if not quota else "0%"] )
    return output


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


def _detailed_calls(cursor, table: str, client: Dict[str, Any], start_dt: datetime, end_dt: datetime, page: int, per_page: int, tz_offset_minutes: int) -> List[List[str]]:
    page = max(page, 1)
    per_page = max(min(per_page, 50), 1)
    offset = (page - 1) * per_page
    where_sql, params = _base_where(client, start_dt, end_dt)
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
    return [_format_call_row(row, tz_offset_minutes) for row in rows]


def _key_count(client: Dict[str, Any]) -> int:
    return sum(1 for key in [client.get("api_key"), client.get("sandbox_api_key"), client.get("staging_api_key"), client.get("production_api_key")] if key)


def _env_api_key(client: Dict[str, Any], env: str) -> str:
    if env == "sandbox":
        return _mask_key(client.get("sandbox_api_key") or client.get("api_key"))
    if env == "staging":
        return _mask_key(client.get("staging_api_key") or client.get("api_key"))
    return _mask_key(client.get("production_api_key") or client.get("api_key"))


def _build_environment_report(cursor, client: Dict[str, Any], env: str, range_key: str, date_from: Optional[str], date_to: Optional[str], page: int, per_page: int, timezone_name: str, timezone_offset_minutes: int, daily_date: Optional[str] = None) -> Dict[str, Any]:
    env_conf = ENVIRONMENTS[env]
    table = env_conf["table"]
    start_dt, end_dt = _range_dates(range_key, date_from, date_to, timezone_offset_minutes)
    summary = _summary(cursor, table, client, start_dt, end_dt)
    month_used = _month_used(cursor, table, client, timezone_offset_minutes)

    monthly_quota = _safe_float(client.get("monthly_quota"), 0.0)
    rate_limit = _safe_float(client.get("rate_limit"), 0.0)
    projected = _projected_usage(month_used, timezone_offset_minutes)

    top_error_status, top_error_text = _top_error(cursor, table, client, start_dt, end_dt)
    selected_day = _selected_daily_date(daily_date, timezone_offset_minutes)
    daily_label = _daily_label(selected_day, timezone_offset_minutes)
    today_extra = _day_extra_metrics(cursor, table, client, selected_day, timezone_offset_minutes)
    peak = _peak_hour_for_date(cursor, table, client, selected_day, timezone_offset_minutes)
    daily_success, daily_fail = _hourly_for_date(cursor, table, client, selected_day, timezone_offset_minutes)
    trend, fail = _daily_trend(cursor, table, client, start_dt, end_dt, timezone_offset_minutes)
    weekly_this, weekly_prev = _weekly_arrays(cursor, table, client, timezone_offset_minutes)
    endpoints = _top_endpoints(cursor, table, client, start_dt, end_dt, summary["total"])

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
        "weeklyThis": weekly_this,
        "weeklyPrev": weekly_prev,
        "weeklyRows": _weekly_rows(cursor, table, client, timezone_offset_minutes),
        "endpoints": endpoints,
        "endpointOptions": _endpoint_options(endpoints),
        "errorBuckets": _error_buckets(cursor, table, client, start_dt, end_dt, timezone_offset_minutes),
        "keys": str(_key_count(client)),
        "monthPast": _month_rows(cursor, table, client, monthly_quota, timezone_offset_minutes),
        "dailyRows": [_single_day_row(cursor, table, client, monthly_quota, selected_day, timezone_offset_minutes)],
        "calls": _detailed_calls(cursor, table, client, start_dt, end_dt, page, per_page, timezone_offset_minutes),
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
            envs[env] = _build_environment_report(cursor, client, env, range_key, date_from, date_to, page, per_page, timezone_name, timezone_offset, daily_date)

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
