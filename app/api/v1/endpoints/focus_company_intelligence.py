import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_company_intelligence_service import (
    fetch_focus_company_intelligence,
)


router = APIRouter()


@router.get("/demo/{client_database}/focus/companies/{lead_id}/intelligence")
def get_demo_focus_company_intelligence(
    client_database: str,
    lead_id: int,
):
    """
    Public browser-openable demo endpoint.

    No API key required.
    Database name is passed in URL.
    Returns pretty JSON for browser readability.
    """

    try:
        intelligence = fetch_focus_company_intelligence(
            client_database=client_database,
            lead_id=lead_id,
        )

        if not intelligence:
            response_data = error_response(
                message="Focus company intelligence not found for current report",
                error_code="FOCUS_COMPANY_INTELLIGENCE_NOT_FOUND",
                data={
                    "lead_id": lead_id,
                    "client_database": client_database,
                    "api_environment": auth_context.get("api_environment"),
                    "api_client_id": auth_context.get("api_client_id"),
                    "domain_id": auth_context.get("domain_id"),
                    "timestamp": current_utc_datetime(),
                },
            )

            return Response(
                content=json.dumps(response_data, indent=2, default=str),
                media_type="application/json",
                status_code=404,
            )

        response_data = success_response(
            message="Focus company intelligence fetched successfully",
           meta={
                "generated_at": current_utc_datetime(),
                "lead_id": lead_id,
                "mode": "protected",
                "client_database": client_database,
                "api_environment": auth_context.get("api_environment"),
                "api_client_id": auth_context.get("api_client_id"),
                "domain_id": auth_context.get("domain_id"),
            },
            data={
                "company_intelligence": intelligence,
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
        )

    except Exception as exc:
        response_data = error_response(
            message="Failed to fetch demo focus company intelligence",
            error_code="DEMO_FOCUS_COMPANY_INTELLIGENCE_FETCH_FAILED",
            data={
                "lead_id": lead_id,
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


@router.get("/focus/companies/{lead_id}/intelligence")
def get_focus_company_intelligence(
    lead_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected actual API endpoint.

    Requires X-API-KEY authentication.
    Uses authenticated client's database.
    """

    try:
        client_database = auth_context.get("client_database")

        intelligence = fetch_focus_company_intelligence(
            client_database=client_database,
            lead_id=lead_id,
        )

        if not intelligence:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Focus company intelligence not found for current report",
                    error_code="FOCUS_COMPANY_INTELLIGENCE_NOT_FOUND",
                    data={
                        "lead_id": lead_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Focus company intelligence fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "lead_id": lead_id,
                "mode": "protected",
            },
            data={
                "company_intelligence": intelligence,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch focus company intelligence",
                error_code="FOCUS_COMPANY_INTELLIGENCE_FETCH_FAILED",
                data={
                    "lead_id": lead_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )