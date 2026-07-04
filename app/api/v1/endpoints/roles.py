from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.role_service import (
    SCHEMA_VERSION,
    fetch_roles,
    fetch_role_by_code,
)


router = APIRouter()


@router.get("/roles")
def get_roles(
    auth_context: dict = Depends(authenticate_request),
    search: Optional[str] = Query(default=None),
    role_code: Optional[str] = Query(default=None),
):
    """
    Protected static Roles list API.

    URL:
    /roles
    """

    try:
        roles = fetch_roles(
            search=search,
            role_code=role_code,
        )

        return success_response(
            message="Roles fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "search": search,
                "role_code": role_code,
                "record_count": len(roles),
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "roles": roles,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch roles",
                error_code="ROLES_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/roles/{role_code}")
def get_role_detail(
    role_code: str,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected static Role detail API.

    URL:
    /roles/{role_code}
    """

    try:
        role = fetch_role_by_code(role_code=role_code)

        if not role:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Role not found",
                    error_code="ROLE_NOT_FOUND",
                    data={
                        "role_code": role_code,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Role detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "role_code": role_code,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "role": role,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch role detail",
                error_code="ROLE_DETAIL_FETCH_FAILED",
                data={
                    "role_code": role_code,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )