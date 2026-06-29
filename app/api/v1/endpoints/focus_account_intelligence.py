import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_account_intelligence_service import (
    fetch_focus_account_intelligence_list,
)


router = APIRouter()


@router.get("/demo/{client_database}/focus/account-intelligence")
def get_demo_focus_account_intelligence(
    client_database: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),
    search: Optional[str] = Query(default=None),
    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),
    include_journey: bool = Query(default=False),
):
    try:
        result = fetch_focus_account_intelligence_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
            include_journey=include_journey,
        )

        response_data = success_response(
            message="Focus account intelligence list fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "client_database": client_database,
                "mode": "demo",
                "search": search,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "include_journey": include_journey,
                **result["pagination"],
            },
            data={
                "focus_account_intelligence": result["items"],
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
        )

    except Exception as exc:
        response_data = error_response(
            message="Failed to fetch demo focus account intelligence list",
            error_code="DEMO_FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
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


@router.get("/focus/account-intelligence")
def get_focus_account_intelligence(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),
    search: Optional[str] = Query(default=None),
    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),
    include_journey: bool = Query(default=False),
):
    try:
        client_database = auth_context.get("client_database")

        result = fetch_focus_account_intelligence_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
            include_journey=include_journey,
        )

        return success_response(
            message="Focus account intelligence list fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "search": search,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "include_journey": include_journey,
                **result["pagination"],
            },
            data={
                "focus_account_intelligence": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch focus account intelligence list",
                error_code="FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )