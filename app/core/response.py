from datetime import datetime, timezone
from typing import Any, Optional


def current_utc_datetime() -> str:
    return datetime.now(timezone.utc).isoformat()


def success_response(
    message: str,
    data: Any = None,
    meta: Optional[dict] = None,
) -> dict:
    return {
        "status": "success",
        "message": message,
        "meta": meta or {},
        "data": data,
    }


def error_response(
    message: str,
    error_code: str = "ERROR",
    data: Any = None,
    meta: Optional[dict] = None,
) -> dict:
    return {
        "status": "error",
        "message": message,
        "error_code": error_code,
        "meta": meta or {
            "timestamp": current_utc_datetime(),
        },
        "data": data,
    }


def validation_error_response(
    message: str = "Validation failed",
    errors: Any = None,
) -> dict:
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        data={
            "errors": errors or [],
        },
    )


def not_found_response(
    message: str = "Resource not found",
    data: Any = None,
) -> dict:
    return error_response(
        message=message,
        error_code="RESOURCE_NOT_FOUND",
        data=data,
    )


def server_error_response(
    message: str = "Internal server error",
    data: Any = None,
) -> dict:
    return error_response(
        message=message,
        error_code="INTERNAL_SERVER_ERROR",
        data=data,
    )