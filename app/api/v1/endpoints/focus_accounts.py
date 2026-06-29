# app/api/v1/endpoints/focus_accounts.py

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_account_service import (
    fetch_focus_accounts,
    count_focus_accounts,
)


router = APIRouter()


@router.get("/demo/{client_database}/focus/accounts")
def get_demo_focus_accounts(
    client_database: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),
):
    """
    Public browser-openable demo endpoint.
    No API key required.
    Database name is passed in URL.
    Returns pretty JSON.
    """

    try:
        accounts = fetch_focus_accounts(
            client_database=client_database,
            limit=limit,
            offset=offset,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        total_records = count_focus_accounts(
            client_database=client_database,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        response_data = success_response(
            message="Focus accounts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "client_database": client_database,
                "mode": "demo",
                "limit": limit,
                "offset": offset,
                "search": search,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "record_count": len(accounts),
                "total_records": total_records,
            },
            data={
                "focus_accounts": accounts,
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
        )

    except Exception as exc:
        response_data = error_response(
            message="Failed to fetch demo focus accounts",
            error_code="DEMO_FOCUS_ACCOUNTS_FETCH_FAILED",
            data={
                "client_database": client_database,
                "error": str(exc),
                "timestamp": current_utc_datetime(),
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
            status_code=500,
        )


@router.get("/focus/accounts")
def get_focus_accounts(
    auth_context: dict = Depends(authenticate_request),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),
):
    """
    Protected actual API endpoint.
    Requires X-API-KEY authentication.
    Uses authenticated client's database.
    """

    try:
        client_database = auth_context.get("client_database")

        accounts = fetch_focus_accounts(
            client_database=client_database,
            limit=limit,
            offset=offset,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        total_records = count_focus_accounts(
            client_database=client_database,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
        )

        return success_response(
            message="Focus accounts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "limit": limit,
                "offset": offset,
                "search": search,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "record_count": len(accounts),
                "total_records": total_records,
            },
            data={
                "focus_accounts": accounts,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch focus accounts",
                error_code="FOCUS_ACCOUNTS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )