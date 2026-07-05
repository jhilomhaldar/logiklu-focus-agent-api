from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.client_apiusage_renderer import (
    render_client_apiusage_error_page,
    render_client_apiusage_page,
)
from app.services.client_apiusage_service import build_client_apiusage_report

router = APIRouter()


def _build_report(
    oauth_client_id: str,
    environment: Optional[str],
    range_key: str,
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    per_page: int,
    timezone: Optional[str],
    timezone_offset: Optional[int],
    daily_date: Optional[str],
    weekly_range: Optional[str],
    monthly_month: Optional[str],
    call_search: Optional[str],
    call_methods: Optional[str],
    call_statuses: Optional[str],
    calls_range: Optional[str],
    calls_date_from: Optional[str],
    calls_date_to: Optional[str],
):
    return build_client_apiusage_report(
        oauth_client_id=oauth_client_id,
        environment=environment,
        range_key=range_key,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
        timezone=timezone,
        timezone_offset_minutes=timezone_offset,
        daily_date=daily_date,
        weekly_range=weekly_range,
        monthly_month=monthly_month,
        call_search=call_search,
        call_methods=call_methods,
        call_statuses=call_statuses,
        calls_range=calls_range,
        calls_date_from=calls_date_from,
        calls_date_to=calls_date_to,
    )


@router.get("/client/apiusage/{oauth_client_id}/data")
def client_apiusage_data(
    oauth_client_id: str,
    environment: Optional[str] = Query(default=None, description="sandbox, staging, or production"),
    range_key: str = Query(default="last_30_days", alias="range"),
    date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    timezone: Optional[str] = Query(default=None, description="Browser IANA timezone, for example Asia/Calcutta"),
    timezone_offset: Optional[int] = Query(default=None, description="Browser timezone offset in minutes east of UTC"),
    daily_date: Optional[str] = Query(default=None, description="YYYY-MM-DD date for Daily report"),
    weekly_range: Optional[str] = Query(default="this_week", description="this_week, last_week, or last_4_weeks"),
    monthly_month: Optional[str] = Query(default=None, description="YYYY-MM month for Monthly report"),
    call_search: Optional[str] = Query(default=None, description="Detailed calls search text"),
    call_methods: Optional[str] = Query(default=None, description="Comma separated methods: GET,POST,PUT,PATCH,DELETE"),
    call_statuses: Optional[str] = Query(default=None, description="Comma separated status groups: 2xx,3xx,4xx,5xx"),
    calls_range: Optional[str] = Query(default="last_24_hours", description="last_24_hours,last_7_days,last_15_days,last_30_days,custom_range"),
    calls_date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD for detailed calls custom range"),
    calls_date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD for detailed calls custom range"),
):
    try:
        report = _build_report(
            oauth_client_id=oauth_client_id,
            environment=environment,
            range_key=range_key,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
            timezone=timezone,
            timezone_offset=timezone_offset,
            daily_date=daily_date,
            weekly_range=weekly_range,
            monthly_month=monthly_month,
            call_search=call_search,
            call_methods=call_methods,
            call_statuses=call_statuses,
            calls_range=calls_range,
            calls_date_from=calls_date_from,
            calls_date_to=calls_date_to,
        )
        status_code = 200 if report.get("valid") else 404
        return JSONResponse(content=report, status_code=status_code)
    except Exception:
        return JSONResponse(
            content={
                "valid": False,
                "message": "The usage report could not be generated right now.",
            },
            status_code=500,
        )


@router.get("/client/apiusage/{oauth_client_id}", response_class=HTMLResponse)
def client_apiusage_page(
    oauth_client_id: str,
    environment: Optional[str] = Query(default=None, description="sandbox, staging, or production"),
    range_key: str = Query(default="last_30_days", alias="range"),
    date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    timezone: Optional[str] = Query(default=None, description="Browser IANA timezone, for example Asia/Calcutta"),
    timezone_offset: Optional[int] = Query(default=None, description="Browser timezone offset in minutes east of UTC"),
    daily_date: Optional[str] = Query(default=None, description="YYYY-MM-DD date for Daily report"),
    weekly_range: Optional[str] = Query(default="this_week", description="this_week, last_week, or last_4_weeks"),
    monthly_month: Optional[str] = Query(default=None, description="YYYY-MM month for Monthly report"),
    call_search: Optional[str] = Query(default=None, description="Detailed calls search text"),
    call_methods: Optional[str] = Query(default=None, description="Comma separated methods: GET,POST,PUT,PATCH,DELETE"),
    call_statuses: Optional[str] = Query(default=None, description="Comma separated status groups: 2xx,3xx,4xx,5xx"),
    calls_range: Optional[str] = Query(default="last_24_hours", description="last_24_hours,last_7_days,last_15_days,last_30_days,custom_range"),
    calls_date_from: Optional[str] = Query(default=None, description="YYYY-MM-DD for detailed calls custom range"),
    calls_date_to: Optional[str] = Query(default=None, description="YYYY-MM-DD for detailed calls custom range"),
):
    try:
        report = _build_report(
            oauth_client_id=oauth_client_id,
            environment=environment,
            range_key=range_key,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page,
            timezone=timezone,
            timezone_offset=timezone_offset,
            daily_date=daily_date,
            weekly_range=weekly_range,
            monthly_month=monthly_month,
            call_search=call_search,
            call_methods=call_methods,
            call_statuses=call_statuses,
            calls_range=calls_range,
            calls_date_from=calls_date_from,
            calls_date_to=calls_date_to,
        )
        if not report.get("valid"):
            return HTMLResponse(
                content=render_client_apiusage_error_page(report.get("message") or "Invalid OAuth client ID."),
                status_code=404,
            )
        return HTMLResponse(content=render_client_apiusage_page(report), status_code=200)
    except Exception:
        return HTMLResponse(
            content=render_client_apiusage_error_page("The usage report could not be generated right now."),
            status_code=500,
        )
