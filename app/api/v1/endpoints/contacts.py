import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.contact_service import (
    fetch_contacts,
    count_contacts,
    fetch_contact_by_id,
    CONTACT_SEARCH_FIELDS,
)

router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "account_id",
    "account_search",
    "associated_accounts_only",
    "search",
    "search_by",
    "searchby",
    "limit",
    "offset",
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
    filters: List[Dict[str, Any]] = []

    for key in request.query_params.keys():
        clean_key = str(key or "").strip().lower()

        if not clean_key:
            continue

        if clean_key in RESERVED_QUERY_PARAMS:
            continue

        if clean_key not in CONTACT_SEARCH_FIELDS:
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

        if clean_key in [
            "contact_type",
            "source",
            "owner",
            "created_by",
            "modified_by",
        ]:
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


@router.get("/contacts")
def get_contacts(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    account_id: Optional[int] = Query(default=None),
    account_search: Optional[str] = Query(default=None),
    associated_accounts_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    filters: Optional[str] = Query(default=None),
):
    try:
        client_database = auth_context.get("client_database")

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)

        final_filters = parsed_filters + query_filters

        contacts = fetch_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
            limit=limit,
            offset=offset,
            filters=final_filters,
        )

        total_records = count_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
            filters=final_filters,
        )

        return success_response(
            message="Contacts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "account_id": account_id,
                "account_search": account_search,
                "associated_accounts_only": associated_accounts_only,
                "search": search,
                "search_by": search_by,
                "applied_filters": final_filters,
                "limit": limit,
                "offset": offset,
                "record_count": len(contacts),
                "total_records": total_records,
            },
            data={
                "contacts": contacts,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch contacts",
                error_code="CONTACTS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/contacts/{contact_id}")
def get_contact_detail(
    contact_id: int,
    request: Request,
    auth_context: dict = Depends(authenticate_request),
):
    try:
        client_database = auth_context.get("client_database")

        contact = fetch_contact_by_id(
            client_database=client_database,
            contact_id=contact_id,
        )

        if not contact:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Contact not found",
                    error_code="CONTACT_NOT_FOUND",
                    data={
                        "contact_id": contact_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Contact detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "contact_id": contact_id,
            },
            data={
                "contact": contact,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch contact detail",
                error_code="CONTACT_DETAIL_FETCH_FAILED",
                data={
                    "contact_id": contact_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )