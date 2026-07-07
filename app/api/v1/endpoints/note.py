# app/api/v1/endpoints/note.py

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.note_service import (
    ALLOWED_NOTE_SCOPES,
    SCHEMA_VERSION,
    fetch_user_note_detail,
    fetch_user_notes_list,
)


router = APIRouter()


def build_filter_params(**kwargs: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and str(value).strip() != ""
    }


def _fetch_notes_response(
    note_scope: Optional[str],
    auth_context: dict,
    page: int,
    per_page: int,
    search: Optional[str],
    search_by: Optional[str],
    filters: Optional[str],
    filter_params: Dict[str, Any],
):
    client_database = auth_context.get("client_database")

    result = fetch_user_notes_list(
        client_database=client_database,
        note_scope=note_scope,
        page=page,
        per_page=per_page,
        search=search,
        search_by=search_by,
        filters=filters,
        filter_params=filter_params,
    )

    return success_response(
        message="Notes fetched successfully",
        meta={
            "generated_at": current_utc_datetime(),
            "mode": "protected",
            "note_scope": note_scope or "all",
            "search": search,
            "search_by": search_by,
            "applied_filters": filter_params,
            **result["pagination"],
        },
        data={
            "schema_version": SCHEMA_VERSION,
            "notes": result["items"],
        },
    )


@router.get("/note")
def get_user_notes(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    subject: Optional[str] = Query(default=None),
    note: Optional[str] = Query(default=None),
    notes_subject: Optional[str] = Query(default=None),
    notes_text: Optional[str] = Query(default=None),
    activity_name: Optional[str] = Query(default=None),

    lead_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
    company_id: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    lead_city: Optional[str] = Query(default=None),
    lead_state: Optional[str] = Query(default=None),
    lead_country: Optional[str] = Query(default=None),

    contact_id: Optional[str] = Query(default=None),
    contact_name: Optional[str] = Query(default=None),
    contact_email: Optional[str] = Query(default=None),
    contact_phone: Optional[str] = Query(default=None),
    contact_role: Optional[str] = Query(default=None),

    deal_id: Optional[str] = Query(default=None),
    opportunity_id: Optional[str] = Query(default=None),
    deal_name: Optional[str] = Query(default=None),
    deal_status: Optional[str] = Query(default=None),
    deal_stage_id: Optional[str] = Query(default=None),
    deal_stage_title: Optional[str] = Query(default=None),

    owner: Optional[str] = Query(default=None),
    owner_name: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    created_by_name: Optional[str] = Query(default=None),
    modified_by: Optional[str] = Query(default=None),
    modified_by_name: Optional[str] = Query(default=None),

    created_date_from: Optional[str] = Query(default=None),
    created_date_to: Optional[str] = Query(default=None),
    modified_date_from: Optional[str] = Query(default=None),
    modified_date_to: Optional[str] = Query(default=None),
    startdate_from: Optional[str] = Query(default=None),
    startdate_to: Optional[str] = Query(default=None),
    enddate_from: Optional[str] = Query(default=None),
    enddate_to: Optional[str] = Query(default=None),

    status: Optional[str] = Query(default=None),
    active_status: Optional[str] = Query(default=None),
):
    """
    Protected Notes list API.

    URL:
    /note
    """

    try:
        filter_params = build_filter_params(
            subject=subject,
            note=note,
            notes_subject=notes_subject,
            notes_text=notes_text,
            activity_name=activity_name,

            lead_id=lead_id,
            account_id=account_id,
            customer_id=customer_id,
            company_id=company_id,
            lead_name=lead_name,
            lead_city=lead_city,
            lead_state=lead_state,
            lead_country=lead_country,

            contact_id=contact_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_role=contact_role,

            deal_id=deal_id,
            opportunity_id=opportunity_id,
            deal_name=deal_name,
            deal_status=deal_status,
            deal_stage_id=deal_stage_id,
            deal_stage_title=deal_stage_title,

            owner=owner,
            owner_name=owner_name,
            created_by=created_by,
            created_by_name=created_by_name,
            modified_by=modified_by,
            modified_by_name=modified_by_name,

            created_date_from=created_date_from,
            created_date_to=created_date_to,
            modified_date_from=modified_date_from,
            modified_date_to=modified_date_to,
            startdate_from=startdate_from,
            startdate_to=startdate_to,
            enddate_from=enddate_from,
            enddate_to=enddate_to,

            status=status,
            active_status=active_status,
        )

        return _fetch_notes_response(
            note_scope=None,
            auth_context=auth_context,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch notes",
                error_code="LOGIKLU_USER_NOTES_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )



@router.get("/note/{note_id:int}")
def get_user_note_by_id(
    note_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected Note detail API.

    URL:
    /note/{note_id}
    """

    try:
        client_database = auth_context.get("client_database")
        item = fetch_user_note_detail(
            client_database=client_database,
            note_id=note_id,
        )

        if not item:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Note not found",
                    error_code="LOGIKLU_USER_NOTE_NOT_FOUND",
                    data={
                        "note_id": note_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Note fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "note_id": note_id,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "note": item,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch note",
                error_code="LOGIKLU_USER_NOTE_FETCH_FAILED",
                data={
                    "note_id": note_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

@router.get("/note/{note_scope}")
def get_user_notes_by_scope(
    note_scope: str,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    subject: Optional[str] = Query(default=None),
    note: Optional[str] = Query(default=None),
    notes_subject: Optional[str] = Query(default=None),
    notes_text: Optional[str] = Query(default=None),
    activity_name: Optional[str] = Query(default=None),

    lead_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
    company_id: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    lead_city: Optional[str] = Query(default=None),
    lead_state: Optional[str] = Query(default=None),
    lead_country: Optional[str] = Query(default=None),

    contact_id: Optional[str] = Query(default=None),
    contact_name: Optional[str] = Query(default=None),
    contact_email: Optional[str] = Query(default=None),
    contact_phone: Optional[str] = Query(default=None),
    contact_role: Optional[str] = Query(default=None),

    deal_id: Optional[str] = Query(default=None),
    opportunity_id: Optional[str] = Query(default=None),
    deal_name: Optional[str] = Query(default=None),
    deal_status: Optional[str] = Query(default=None),
    deal_stage_id: Optional[str] = Query(default=None),
    deal_stage_title: Optional[str] = Query(default=None),

    owner: Optional[str] = Query(default=None),
    owner_name: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    created_by_name: Optional[str] = Query(default=None),
    modified_by: Optional[str] = Query(default=None),
    modified_by_name: Optional[str] = Query(default=None),

    created_date_from: Optional[str] = Query(default=None),
    created_date_to: Optional[str] = Query(default=None),
    modified_date_from: Optional[str] = Query(default=None),
    modified_date_to: Optional[str] = Query(default=None),
    startdate_from: Optional[str] = Query(default=None),
    startdate_to: Optional[str] = Query(default=None),
    enddate_from: Optional[str] = Query(default=None),
    enddate_to: Optional[str] = Query(default=None),

    status: Optional[str] = Query(default=None),
    active_status: Optional[str] = Query(default=None),
):
    """
    Protected Notes by scope API.

    URLs:
    /note/lead
    /note/contact
    /note/deal
    """

    try:
        note_scope = str(note_scope or "").strip().lower()

        if note_scope not in ALLOWED_NOTE_SCOPES:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message="Invalid notes scope",
                    error_code="LOGIKLU_USER_NOTES_INVALID_SCOPE",
                    data={
                        "allowed_scopes": ALLOWED_NOTE_SCOPES,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        filter_params = build_filter_params(
            subject=subject,
            note=note,
            notes_subject=notes_subject,
            notes_text=notes_text,
            activity_name=activity_name,

            lead_id=lead_id,
            account_id=account_id,
            customer_id=customer_id,
            company_id=company_id,
            lead_name=lead_name,
            lead_city=lead_city,
            lead_state=lead_state,
            lead_country=lead_country,

            contact_id=contact_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            contact_role=contact_role,

            deal_id=deal_id,
            opportunity_id=opportunity_id,
            deal_name=deal_name,
            deal_status=deal_status,
            deal_stage_id=deal_stage_id,
            deal_stage_title=deal_stage_title,

            owner=owner,
            owner_name=owner_name,
            created_by=created_by,
            created_by_name=created_by_name,
            modified_by=modified_by,
            modified_by_name=modified_by_name,

            created_date_from=created_date_from,
            created_date_to=created_date_to,
            modified_date_from=modified_date_from,
            modified_date_to=modified_date_to,
            startdate_from=startdate_from,
            startdate_to=startdate_to,
            enddate_from=enddate_from,
            enddate_to=enddate_to,

            status=status,
            active_status=active_status,
        )

        return _fetch_notes_response(
            note_scope=note_scope,
            auth_context=auth_context,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch notes",
                error_code="LOGIKLU_USER_NOTES_SCOPE_FETCH_FAILED",
                data={
                    "note_scope": note_scope,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
