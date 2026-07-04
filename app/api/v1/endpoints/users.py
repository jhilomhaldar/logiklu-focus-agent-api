import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.user_service import (
    SCHEMA_VERSION,
    USER_SEARCH_FIELDS,
    fetch_users,
    fetch_user_by_id,
)


router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "search",
    "search_by",
    "searchby",
    "page",
    "per_page",
    "filters",
    "include_archived",
    "sort_by",
    "sort_order",
}


NUMERIC_FILTER_FIELDS = {
    "id",
    "global_user_id",
    "client_user_id",
    "parent_id",
    "permission_group",
    "permission_group_id",
}


EXACT_FILTER_FIELDS = {
    "user_type",
    "role_code",
    "status",
    "product",
    "product_code",
}


def parse_filters(filters: Optional[str]) -> List[Dict[str, Any]]:
    if not filters:
        return []

    try:
        parsed = json.loads(filters)

        if isinstance(parsed, list):
            return parsed

        return []

    except Exception:
        return []


def parse_multi_field_filters(request: Request) -> List[Dict[str, Any]]:
    filters: List[Dict[str, Any]] = []

    for key in request.query_params.keys():
        clean_key = str(key or "").strip().lower()

        if not clean_key:
            continue

        if clean_key in RESERVED_QUERY_PARAMS:
            continue

        if clean_key not in USER_SEARCH_FIELDS:
            continue

        values = request.query_params.getlist(clean_key)
        cleaned_values: List[str] = []

        for value in values:
            if value is None:
                continue

            value_string = str(value).strip()

            if not value_string:
                continue

            if "," in value_string:
                cleaned_values.extend(
                    [item.strip() for item in value_string.split(",") if item.strip()]
                )
            else:
                cleaned_values.append(value_string)

        if not cleaned_values:
            continue

        if len(cleaned_values) > 1:
            filters.append(
                {
                    "field": clean_key,
                    "operator": "in",
                    "value": cleaned_values,
                }
            )
            continue

        operator = "like"

        if clean_key in NUMERIC_FILTER_FIELDS or clean_key in EXACT_FILTER_FIELDS:
            operator = "eq"

        filters.append(
            {
                "field": clean_key,
                "operator": operator,
                "value": cleaned_values[0],
            }
        )

    return filters


@router.get("/users")
def get_users(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    sort_by: Optional[str] = Query(default=None),
    sort_order: Optional[str] = Query(default="asc"),
):
    """
    Protected Users list API.

    URL:
    /users
    """

    try:
        client_database = auth_context.get("client_database")

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)
        final_filters = parsed_filters + query_filters

        result = fetch_users(
            client_database=client_database,
            search=search,
            search_by=search_by,
            page=page,
            per_page=per_page,
            filters=final_filters,
            include_archived=include_archived,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return success_response(
            message="Users fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "search": search,
                "search_by": search_by,
                "applied_filters": final_filters,
                "include_archived": include_archived,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": result["page"],
                "per_page": result["per_page"],
                "offset": result["offset"],
                "record_count": len(result["items"]),
                "total_records": result["total_records"],
                "total_pages": result["total_pages"],
                "has_next": result["has_next"],
                "has_previous": result["has_previous"],
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "users": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch users",
                error_code="USERS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/users/{id}")
def get_user_detail(
    id: int,
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    include_archived: bool = Query(default=False),
):
    """
    Protected User detail API.

    URL:
    /users/{id}
    """

    try:
        client_database = auth_context.get("client_database")

        user = fetch_user_by_id(
            client_database=client_database,
            user_id=id,
            include_archived=include_archived,
        )

        if not user:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="User not found",
                    error_code="USER_NOT_FOUND",
                    data={
                        "id": id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="User detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "id": id,
                "include_archived": include_archived,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "user": user,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch user detail",
                error_code="USER_DETAIL_FETCH_FAILED",
                data={
                    "id": id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
