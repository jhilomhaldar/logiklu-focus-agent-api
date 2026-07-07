import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.accounts_service import (
    ALLOWED_FILTER_FIELDS,
    SCHEMA_VERSION,
    count_accounts,
    fetch_account_by_id,
    fetch_accounts,
)

router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "page",
    "per_page",
    "limit",
    "offset",
    "search",
    "search_by",
    "searchby",
    "account_publish_status",
    "computed_account_category",
    "lead_publish_status",        # backward-compatible alias
    "computed_lead_category",     # backward-compatible alias
    "filters",
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
    """
    Converts normal query params into filter objects.

    Example:
    /accounts?industry=Software&city=Kolkata&country=India
    """

    filters: List[Dict[str, Any]] = []

    for key in request.query_params.keys():
        clean_key = str(key or "").strip()

        if not clean_key:
            continue

        if clean_key in RESERVED_QUERY_PARAMS:
            continue

        if clean_key not in ALLOWED_FILTER_FIELDS:
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
                cleaned_values.extend([item.strip() for item in value_string.split(",") if item.strip()])
            else:
                cleaned_values.append(value_string)

        if not cleaned_values:
            continue

        if len(cleaned_values) > 1:
            filters.append({"field": clean_key, "operator": "in", "value": cleaned_values})
            continue

        single_value = cleaned_values[0]

        if clean_key in [
            "account_id",
            "lead_id",
            "account_status_id",
            "lead_status_id",
            "owner",
            "created_by",
            "modified_by",
            "account_segment",
            "lead_segment",
            "account_category",
            "lead_category",
            "account_type",
            "lead_type",
            "source",
            "assigned_to",
            "product_id",
            "product_category_id",
            "page_id",
        ]:
            filters.append({"field": clean_key, "operator": "eq", "value": single_value})
        else:
            filters.append({"field": clean_key, "operator": "like", "value": single_value})

    return filters


@router.get("/accounts")
def get_accounts(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    # Backward-compatible aliases for old accounts pagination.
    # Response meta will still use page/per_page.
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    offset: Optional[int] = Query(default=None, ge=0),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    account_publish_status: str = Query(default="active"),
    computed_account_category: str = Query(default="all"),
    lead_publish_status: Optional[str] = Query(default=None),
    computed_lead_category: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),
):
    try:
        client_database = auth_context.get("client_database")

        resolved_per_page = limit if limit is not None else per_page
        resolved_offset = offset if offset is not None else ((page - 1) * resolved_per_page)
        resolved_page = int(resolved_offset / resolved_per_page) + 1 if offset is not None else page

        resolved_account_publish_status = lead_publish_status if lead_publish_status is not None else account_publish_status
        resolved_computed_account_category = computed_lead_category if computed_lead_category is not None else computed_account_category

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)
        final_filters = parsed_filters + query_filters

        accounts = fetch_accounts(
            client_database=client_database,
            limit=resolved_per_page,
            offset=resolved_offset,
            search=search,
            search_by=search_by,
            account_publish_status=resolved_account_publish_status,
            computed_account_category=resolved_computed_account_category,
            filters=final_filters,
        )

        total_records = count_accounts(
            client_database=client_database,
            search=search,
            search_by=search_by,
            account_publish_status=resolved_account_publish_status,
            computed_account_category=resolved_computed_account_category,
            filters=final_filters,
        )
        total_pages = (total_records + resolved_per_page - 1) // resolved_per_page if total_records > 0 else 0

        return success_response(
            message="Accounts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "page": resolved_page,
                "per_page": resolved_per_page,
                "offset": resolved_offset,
                "record_count": len(accounts),
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": resolved_page < total_pages,
                "has_previous": resolved_page > 1,
                "search": search,
                "search_by": search_by,
                "account_publish_status": resolved_account_publish_status,
                "computed_account_category": resolved_computed_account_category,
                "applied_filters": final_filters,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "accounts": accounts,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch accounts",
                error_code="ACCOUNTS_FETCH_FAILED",
                data={"error": str(exc), "timestamp": current_utc_datetime()},
            ),
        )


@router.get("/accounts/{account_id}")
def get_account_detail(
    account_id: int,
    request: Request,
    auth_context: dict = Depends(authenticate_request),
):
    try:
        client_database = auth_context.get("client_database")

        account = fetch_account_by_id(
            client_database=client_database,
            account_id=account_id,
        )

        if not account:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Account not found",
                    error_code="ACCOUNT_NOT_FOUND",
                    data={"account_id": account_id, "timestamp": current_utc_datetime()},
                ),
            )

        return success_response(
            message="Account detail fetched successfully",
            meta={"generated_at": current_utc_datetime(), "account_id": account_id},
            data={"schema_version": SCHEMA_VERSION, "account": account},
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch account detail",
                error_code="ACCOUNT_DETAIL_FETCH_FAILED",
                data={"account_id": account_id, "error": str(exc), "timestamp": current_utc_datetime()},
            ),
        )
