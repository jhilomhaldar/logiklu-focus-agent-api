# app/api/v1/endpoints/focus_contacts.py

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_contacts_service import (
    FOCUS_CONTACT_SEARCH_FIELDS,
    SCHEMA_VERSION,
    count_focus_contacts,
    fetch_focus_contact_by_id,
    fetch_focus_contacts,
)


router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "account_id",
    "account_search",
    "associated_accounts_only",
    "search",
    "search_by",
    "searchby",
    "page",
    "per_page",
    "limit",
    "offset",
    "filters",
    "interaction_type",
    "has_lead_form_submission",
    "has_inner_form_submission",
    "has_email_link_click",
    "required_interactions",
    "excluded_interactions",
    "last_interaction_from",
    "last_interaction_to",
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

        if clean_key not in FOCUS_CONTACT_SEARCH_FIELDS:
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


@router.get("/focus/contacts")
def get_focus_contacts(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    account_id: Optional[int] = Query(default=None),
    account_search: Optional[str] = Query(default=None),
    associated_accounts_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),
    filters: Optional[str] = Query(default=None),
    interaction_type: Optional[str] = Query(default=None),
    has_lead_form_submission: Optional[str] = Query(default=None),
    has_inner_form_submission: Optional[str] = Query(default=None),
    has_email_link_click: Optional[str] = Query(default=None),
    required_interactions: Optional[str] = Query(default=None),
    excluded_interactions: Optional[str] = Query(default=None),
    last_interaction_from: Optional[str] = Query(default=None),
    last_interaction_to: Optional[str] = Query(default=None),
):
    """
    Protected Focus Contacts API.

    Returns only contacts who interacted with Focus signals:
    - Lead form submitted
    - Inner form submitted
    - Email link clicked
    """

    try:
        client_database = auth_context.get("client_database")

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)

        final_filters = parsed_filters + query_filters

        page = max(page, 1)
        per_page = max(10, min(per_page, 100))
        offset = (page - 1) * per_page

        contacts = fetch_focus_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
            page=page,
            per_page=per_page,
            filters=final_filters,
            interaction_type=interaction_type,
            has_lead_form_submission=has_lead_form_submission,
            has_inner_form_submission=has_inner_form_submission,
            has_email_link_click=has_email_link_click,
            required_interactions=required_interactions,
            excluded_interactions=excluded_interactions,
            last_interaction_from=last_interaction_from,
            last_interaction_to=last_interaction_to,
        )

        total_records = count_focus_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
            filters=final_filters,
            interaction_type=interaction_type,
            has_lead_form_submission=has_lead_form_submission,
            has_inner_form_submission=has_inner_form_submission,
            has_email_link_click=has_email_link_click,
            required_interactions=required_interactions,
            excluded_interactions=excluded_interactions,
            last_interaction_from=last_interaction_from,
            last_interaction_to=last_interaction_to,
        )

        total_pages = (total_records + per_page - 1) // per_page if total_records > 0 else 0

        return success_response(
            message="Focus contacts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "account_id": account_id,
                "account_search": account_search,
                "associated_accounts_only": associated_accounts_only,
                "search": search,
                "search_by": search_by,
                "interaction_type": interaction_type,
                "has_lead_form_submission": has_lead_form_submission,
                "has_inner_form_submission": has_inner_form_submission,
                "has_email_link_click": has_email_link_click,
                "required_interactions": required_interactions,
                "excluded_interactions": excluded_interactions,
                "last_interaction_from": last_interaction_from,
                "last_interaction_to": last_interaction_to,
                "applied_filters": final_filters,
                "page": page,
                "per_page": per_page,
                "offset": offset,
                "record_count": len(contacts),
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "focus_contacts": contacts,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch Focus contacts",
                error_code="FOCUS_CONTACTS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/focus/contacts/{contact_id}")
def get_focus_contact_detail(
    contact_id: int,
    request: Request,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected Focus Contact Detail API.

    Returns one contact only if that contact has Focus interaction.
    """

    try:
        client_database = auth_context.get("client_database")

        contact = fetch_focus_contact_by_id(
            client_database=client_database,
            contact_id=contact_id,
        )

        if not contact:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Focus contact not found for the requested contact_id",
                    error_code="FOCUS_CONTACT_NOT_FOUND",
                    data={
                        "contact_id": contact_id,
                        "reason": "The contact either does not exist or has no Focus interaction.",
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Focus contact detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "contact_id": contact_id,
                "schema_version": SCHEMA_VERSION,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "focus_contact": contact,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch Focus contact detail",
                error_code="FOCUS_CONTACT_DETAIL_FETCH_FAILED",
                data={
                    "contact_id": contact_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
