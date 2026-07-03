import json
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.leadform_service import (
    fetch_leadforms,
    count_leadforms,
    fetch_leadform_by_id,
    LEADFORM_SEARCH_FIELDS,
)


router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "page",
    "per_page",
    "search",
    "search_by",
    "searchby",
    "filters",
    "has_embeds",
    "has_submissions",
    "submission_date_from",
    "submission_date_to",
}


EXACT_QUERY_FIELDS = {
    "form_id",
    "id",
    "embed_id",
    "is_active",
    "active_status",
    "created_by",
    "modified_by",
    "assign_owner",
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

        if clean_key not in LEADFORM_SEARCH_FIELDS:
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
                    [
                        item.strip()
                        for item in value_string.split(",")
                        if item.strip()
                    ]
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

        single_value = cleaned_values[0]

        if clean_key in EXACT_QUERY_FIELDS:
            filters.append(
                {
                    "field": clean_key,
                    "operator": "eq",
                    "value": single_value,
                }
            )
        else:
            filters.append(
                {
                    "field": clean_key,
                    "operator": "like",
                    "value": single_value,
                }
            )

    return filters


@router.get("/leadforms")
def get_leadforms(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    has_embeds: Optional[bool] = Query(default=None),
    has_submissions: Optional[bool] = Query(default=None),
    submission_date_from: Optional[str] = Query(default=None),
    submission_date_to: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),
):
    """
    Protected Leadforms list API.

    URL:
    /leadforms

    Pagination standard:
    page + per_page
    """

    try:
        client_database = auth_context.get("client_database")

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)
        final_filters = parsed_filters + query_filters

        result = fetch_leadforms(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            has_embeds=has_embeds,
            has_submissions=has_submissions,
            submission_date_from=submission_date_from,
            submission_date_to=submission_date_to,
            filters=final_filters,
        )

        return success_response(
            message="Leadforms fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "search": search,
                "search_by": search_by,
                "has_embeds": has_embeds,
                "has_submissions": has_submissions,
                "submission_date_from": submission_date_from,
                "submission_date_to": submission_date_to,
                "applied_filters": final_filters,
                **result["pagination"],
            },
            data={
                "schema_version": "logiklu_leadform.v1",
                "leadforms": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch leadforms",
                error_code="LEADFORMS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/leadforms/{form_id}")
def get_leadform_detail(
    form_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected Leadform detail API.

    URL:
    /leadforms/{form_id}
    """

    try:
        client_database = auth_context.get("client_database")

        leadform = fetch_leadform_by_id(
            client_database=client_database,
            form_id=form_id,
        )

        if not leadform:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Leadform not found",
                    error_code="LEADFORM_NOT_FOUND",
                    data={
                        "form_id": form_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Leadform detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "form_id": form_id,
            },
            data={
                "schema_version": "logiklu_leadform.v1",
                "leadform": leadform,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch leadform detail",
                error_code="LEADFORM_DETAIL_FETCH_FAILED",
                data={
                    "form_id": form_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
