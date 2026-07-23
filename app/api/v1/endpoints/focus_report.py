# app/api/v1/endpoints/focus_report.py

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_report_service import (
    SCHEMA_VERSION,
    FocusReportNotFoundError,
    FocusReportStorageError,
    FocusReportValidationError,
    get_current_focus_report,
    save_current_focus_report,
)


router = APIRouter()


@router.post("/focus/report")
def update_current_focus_report(
    payload: Dict[str, Any] = Body(...),
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected API used by Agentic AI to replace the current Focus report.

    URL:
    POST /focus/report
    """

    try:
        client_database = auth_context.get("client_database")

        result = save_current_focus_report(
            client_database=client_database,
            payload=payload,
            auth_context=auth_context,
        )

        return success_response(
            message="Focus report updated successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "schema_version": SCHEMA_VERSION,
            },
            data={
                "report": result,
            },
        )

    except FocusReportValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message=str(exc),
                error_code="FOCUS_REPORT_VALIDATION_FAILED",
                data={
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    except FocusReportStorageError as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to update Focus report",
                error_code="FOCUS_REPORT_UPDATE_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to update Focus report",
                error_code="FOCUS_REPORT_UPDATE_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/focus/report")
def fetch_current_focus_report(
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected API used by frontend/report page to fetch the current Focus report.

    URL:
    GET /focus/report
    """

    try:
        client_database = auth_context.get("client_database")

        result = get_current_focus_report(
            client_database=client_database,
            auth_context=auth_context,
        )

        return success_response(
            message="Focus report fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "schema_version": SCHEMA_VERSION,
            },
            data={
                "report": result,
            },
        )

    except FocusReportNotFoundError as exc:
        return JSONResponse(
            status_code=404,
            content=error_response(
                message=str(exc),
                error_code="FOCUS_REPORT_NOT_FOUND",
                data={
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    except FocusReportValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=error_response(
                message=str(exc),
                error_code="FOCUS_REPORT_VALIDATION_FAILED",
                data={
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    except FocusReportStorageError as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch Focus report",
                error_code="FOCUS_REPORT_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch Focus report",
                error_code="FOCUS_REPORT_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
