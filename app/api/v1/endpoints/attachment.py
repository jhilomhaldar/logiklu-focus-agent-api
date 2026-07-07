# app/api/v1/endpoints/attachment.py

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.attachment_service import (
    ALLOWED_ATTACHMENT_SCOPES,
    SCHEMA_VERSION,
    fetch_user_attachment_detail,
    fetch_user_attachments_list,
)


router = APIRouter()


def build_filter_params(**kwargs: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and str(value).strip() != ""
    }


def _fetch_attachments_response(
    attachment_scope: Optional[str],
    auth_context: dict,
    page: int,
    per_page: int,
    search: Optional[str],
    search_by: Optional[str],
    filters: Optional[str],
    filter_params: Dict[str, Any],
):
    client_database = auth_context.get("client_database")

    result = fetch_user_attachments_list(
        client_database=client_database,
        attachment_scope=attachment_scope,
        page=page,
        per_page=per_page,
        search=search,
        search_by=search_by,
        filters=filters,
        filter_params=filter_params,
    )

    return success_response(
        message="Attachments fetched successfully",
        meta={
            "generated_at": current_utc_datetime(),
            "mode": "protected",
            "attachment_scope": attachment_scope or "all",
            "search": search,
            "search_by": search_by,
            "applied_filters": filter_params,
            **result["pagination"],
        },
        data={
            "schema_version": SCHEMA_VERSION,
            "attachments": result["items"],
        },
    )


COMMON_QUERY_PARAMS = None


def _build_attachment_filter_params(
    name: Optional[str], attachment_name: Optional[str], originalname: Optional[str],
    attachmentname: Optional[str], filetype: Optional[str], filesize_min: Optional[str], filesize_max: Optional[str],
    activity_name: Optional[str], lead_id: Optional[str], account_id: Optional[str], customer_id: Optional[str],
    company_id: Optional[str], lead_name: Optional[str], lead_city: Optional[str], lead_state: Optional[str],
    lead_country: Optional[str], contact_id: Optional[str], contact_name: Optional[str], contact_email: Optional[str],
    contact_phone: Optional[str], contact_role: Optional[str], deal_id: Optional[str], opportunity_id: Optional[str],
    deal_name: Optional[str], deal_status: Optional[str], deal_stage_id: Optional[str], deal_stage_title: Optional[str],
    owner: Optional[str], owner_name: Optional[str], created_by: Optional[str], created_by_name: Optional[str],
    modified_by: Optional[str], modified_by_name: Optional[str], created_date_from: Optional[str], created_date_to: Optional[str],
    modified_date_from: Optional[str], modified_date_to: Optional[str], startdate_from: Optional[str], startdate_to: Optional[str],
    enddate_from: Optional[str], enddate_to: Optional[str], status: Optional[str], active_status: Optional[str],
) -> Dict[str, Any]:
    return build_filter_params(
        name=name,
        attachment_name=attachment_name,
        originalname=originalname,
        attachmentname=attachmentname,
        filetype=filetype,
        filesize_min=filesize_min,
        filesize_max=filesize_max,
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


@router.get("/attachment")
def get_user_attachments(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    name: Optional[str] = Query(default=None),
    attachment_name: Optional[str] = Query(default=None),
    originalname: Optional[str] = Query(default=None),
    attachmentname: Optional[str] = Query(default=None),
    filetype: Optional[str] = Query(default=None),
    filesize_min: Optional[str] = Query(default=None),
    filesize_max: Optional[str] = Query(default=None),
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
    try:
        filter_params = _build_attachment_filter_params(
            name, attachment_name, originalname, attachmentname, filetype, filesize_min, filesize_max,
            activity_name, lead_id, account_id, customer_id, company_id, lead_name, lead_city, lead_state,
            lead_country, contact_id, contact_name, contact_email, contact_phone, contact_role, deal_id,
            opportunity_id, deal_name, deal_status, deal_stage_id, deal_stage_title, owner, owner_name,
            created_by, created_by_name, modified_by, modified_by_name, created_date_from, created_date_to,
            modified_date_from, modified_date_to, startdate_from, startdate_to, enddate_from, enddate_to,
            status, active_status,
        )
        return _fetch_attachments_response(None, auth_context, page, per_page, search, search_by, filters, filter_params)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch attachments",
                error_code="LOGIKLU_USER_ATTACHMENTS_FETCH_FAILED",
                data={"error": str(exc), "timestamp": current_utc_datetime()},
            ),
        )



@router.get("/attachment/{attachment_id:int}")
def get_user_attachment_by_id(
    attachment_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected User Attachment detail API.

    URL:
    /attachment/{attachment_id}
    """

    try:
        client_database = auth_context.get("client_database")
        item = fetch_user_attachment_detail(
            client_database=client_database,
            attachment_id=attachment_id,
        )

        if not item:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="User attachment not found",
                    error_code="LOGIKLU_USER_ATTACHMENT_NOT_FOUND",
                    data={
                        "attachment_id": attachment_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="User attachment fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "attachment_id": attachment_id,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "attachment": item,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch user attachment",
                error_code="LOGIKLU_USER_ATTACHMENT_FETCH_FAILED",
                data={
                    "attachment_id": attachment_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

@router.get("/attachment/{attachment_scope}")
def get_user_attachments_by_scope(
    attachment_scope: str,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    name: Optional[str] = Query(default=None),
    attachment_name: Optional[str] = Query(default=None),
    originalname: Optional[str] = Query(default=None),
    attachmentname: Optional[str] = Query(default=None),
    filetype: Optional[str] = Query(default=None),
    filesize_min: Optional[str] = Query(default=None),
    filesize_max: Optional[str] = Query(default=None),
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
    try:
        attachment_scope = str(attachment_scope or "").strip().lower()

        if attachment_scope not in ALLOWED_ATTACHMENT_SCOPES:
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message="Invalid attachments scope",
                    error_code="LOGIKLU_USER_ATTACHMENTS_INVALID_SCOPE",
                    data={"allowed_scopes": ALLOWED_ATTACHMENT_SCOPES, "timestamp": current_utc_datetime()},
                ),
            )

        filter_params = _build_attachment_filter_params(
            name, attachment_name, originalname, attachmentname, filetype, filesize_min, filesize_max,
            activity_name, lead_id, account_id, customer_id, company_id, lead_name, lead_city, lead_state,
            lead_country, contact_id, contact_name, contact_email, contact_phone, contact_role, deal_id,
            opportunity_id, deal_name, deal_status, deal_stage_id, deal_stage_title, owner, owner_name,
            created_by, created_by_name, modified_by, modified_by_name, created_date_from, created_date_to,
            modified_date_from, modified_date_to, startdate_from, startdate_to, enddate_from, enddate_to,
            status, active_status,
        )
        return _fetch_attachments_response(attachment_scope, auth_context, page, per_page, search, search_by, filters, filter_params)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch attachments",
                error_code="LOGIKLU_USER_ATTACHMENTS_SCOPE_FETCH_FAILED",
                data={"attachment_scope": attachment_scope, "error": str(exc), "timestamp": current_utc_datetime()},
            ),
        )
