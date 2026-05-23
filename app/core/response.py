from datetime import datetime, timezone
from typing import Any, Optional


def success_response(
    message: str,
    data: Any = None,
    meta: Optional[dict] = None
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
    data: Any = None
) -> dict:
    return {
        "status": "error",
        "message": message,
        "error_code": error_code,
        "data": data,
    }


def current_utc_datetime() -> str:
    return datetime.now(timezone.utc).isoformat()