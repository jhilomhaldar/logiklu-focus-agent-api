# app/api/v1/endpoints/focus_account_intelligence.py

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_account_intelligence_service import (
    fetch_focus_account_intelligence_list,
)
from app.services.focus_company_intelligence_service import (
    fetch_focus_company_intelligence,
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
    include_journey: bool = Query(default=True),
):
    """
    Demo endpoint remains available.
    """

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
            message="LogiKlu account intelligence list fetched successfully",
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
                "logiklu_focus_account_intelligence": result["items"],
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
        )

    except Exception as exc:
        response_data = error_response(
            message="Failed to fetch demo LogiKlu Focus account intelligence list",
            error_code="DEMO_LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
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
):
    """
    Protected actual API endpoint.

    URL:
    /focus/account-intelligence

    Journey is included by default.
    Caller does not need to pass include_journey=true.
    """

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
            include_journey=True,
        )

        return success_response(
            message="LogiKlu account intelligence list fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "search": search,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "include_journey": True,
                **result["pagination"],
            },
            data={
                "logiklu_focus_account_intelligence": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch LogiKlu account intelligence list",
                error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/focus/account-intelligence/{account_id}")
def get_focus_account_intelligence_detail(
    account_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected actual API endpoint for one account intelligence.

    New URL:
    /focus/account-intelligence/{account_id}
    """

    try:
        client_database = auth_context.get("client_database")

        intelligence = fetch_focus_company_intelligence(
            client_database=client_database,
            lead_id=account_id,
        )

        if not intelligence:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="No LogiKlu account intelligence found for the requested account_id",
                    error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_NOT_FOUND",
                    data={
                        "account_id": account_id,
                        "reason": "The requested account_id is not available in the current LogiKlu Focus intelligence dataset.",
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="LogiKlu Focus account intelligence fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "account_id": account_id,
                "mode": "protected",
            },
            data={
                "logiklu_focus_account_inetellegence": intelligence,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch LogiKlu Focus account intelligence",
                error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_FETCH_FAILED",
                data={
                    "account_id": account_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )