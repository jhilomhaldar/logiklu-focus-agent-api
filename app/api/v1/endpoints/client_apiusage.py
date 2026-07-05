from __future__ import annotations

import os
from typing import Optional
from urllib.parse import quote, parse_qs

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.client_apiusage_renderer import (
    render_client_apiusage_error_page,
    render_client_apiusage_login_page,
    render_client_apiusage_page,
)
from app.services.client_apiusage_service import (
    authenticate_usage_report_user,
    build_client_apiusage_report,
    get_usage_report_client,
    get_usage_session_cookie_name,
    verify_usage_report_session,
)

router = APIRouter()


def _safe_path_oauth(oauth_client_id: str) -> str:
    return quote(str(oauth_client_id or ""), safe="")


def _report_url(oauth_client_id: str) -> str:
    return f"/client/apiusage/{_safe_path_oauth(oauth_client_id)}"


def _login_url(oauth_client_id: str) -> str:
    return f"/client/apiusage/{_safe_path_oauth(oauth_client_id)}/login"


def _cookie_path(oauth_client_id: str) -> str:
    return _report_url(oauth_client_id)


def _cookie_secure() -> bool:
    return str(os.getenv("USAGE_SESSION_COOKIE_SECURE", "false")).strip().lower() in ["1", "true", "yes", "on"]


def _get_usage_session_token(request: Request, oauth_client_id: str) -> str:
    return request.cookies.get(get_usage_session_cookie_name(oauth_client_id), "")

async def _read_login_post_body(request: Request) -> tuple[str, str]:
    """Read normal HTML form post without depending on python-multipart."""
    try:
        raw_body = await request.body()
    except Exception:
        raw_body = b""

    if not raw_body:
        return "", ""

    try:
        parsed = parse_qs(raw_body.decode("utf-8", "ignore"), keep_blank_values=True)
    except Exception:
        return "", ""

    login_id = (
        parsed.get("login_id")
        or parsed.get("email")
        or parsed.get("username")
        or [""]
    )[0]
    password = (parsed.get("password") or [""])[0]
    return str(login_id or "").strip(), str(password or "")



def _is_usage_session_valid(request: Request, oauth_client_id: str) -> bool:
    token = _get_usage_session_token(request, oauth_client_id)
    result = verify_usage_report_session(oauth_client_id, token)
    return bool(result.get("valid"))


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


@router.get("/client/apiusage/{oauth_client_id}/login", response_class=HTMLResponse)
def client_apiusage_login_page(request: Request, oauth_client_id: str):
    client = get_usage_report_client(oauth_client_id)
    if not client:
        return HTMLResponse(
            content=render_client_apiusage_error_page("Invalid or inactive client access key."),
            status_code=404,
        )

    if _is_usage_session_valid(request, oauth_client_id):
        return RedirectResponse(url=_report_url(oauth_client_id), status_code=303)

    return HTMLResponse(
        content=render_client_apiusage_login_page(
            oauth_client_id=oauth_client_id,
            client_name=client.get("api_client_name") or "LogiKlu API Usage",
        ),
        status_code=200,
    )


@router.post("/client/apiusage/{oauth_client_id}/login", response_class=HTMLResponse)
async def client_apiusage_login_submit(request: Request, oauth_client_id: str):
    login_id, password = await _read_login_post_body(request)

    result = authenticate_usage_report_user(
        oauth_client_id=oauth_client_id,
        login_id=login_id,
        password=password,
    )

    if not result.get("valid"):
        return HTMLResponse(
            content=render_client_apiusage_login_page(
                oauth_client_id=oauth_client_id,
                message=result.get("message") or "Login failed.",
                login_id=login_id,
            ),
            status_code=401,
        )

    response = RedirectResponse(url=_report_url(oauth_client_id), status_code=303)
    response.set_cookie(
        key=get_usage_session_cookie_name(oauth_client_id),
        value=result.get("token") or "",
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path=_cookie_path(oauth_client_id),
    )
    return response


@router.get("/client/apiusage/{oauth_client_id}/logout")
def client_apiusage_logout(oauth_client_id: str):
    response = RedirectResponse(url=_login_url(oauth_client_id), status_code=303)
    response.delete_cookie(
        key=get_usage_session_cookie_name(oauth_client_id),
        path=_cookie_path(oauth_client_id),
    )
    return response


@router.get("/client/apiusage/{oauth_client_id}/data")
def client_apiusage_data(
    request: Request,
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
    if not _is_usage_session_valid(request, oauth_client_id):
        return JSONResponse(
            content={
                "valid": False,
                "login_required": True,
                "message": "Login required.",
                "login_url": _login_url(oauth_client_id),
            },
            status_code=401,
        )

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
    request: Request,
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
    if not _is_usage_session_valid(request, oauth_client_id):
        return RedirectResponse(url=_login_url(oauth_client_id), status_code=303)

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
