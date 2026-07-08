# app/api/v1/endpoints/activities.py

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.activities_service import (
    SCHEMA_VERSION,
    fetch_activities_list,
    fetch_activity_detail,
)


router = APIRouter()


def build_filter_params(**kwargs: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and str(value).strip() != ""
    }


@router.get("/activities")
def get_activities(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    # Main scope/type filters
    activity_for: Optional[str] = Query(default="all", description="Allowed values: all, general, account, contact, deal."),
    activity_type: Optional[str] = Query(default=None, description="Allowed values: call, meeting, task, video_call."),
    activity_id: Optional[str] = Query(default=None),

    # Activity base fields
    activity_category: Optional[str] = Query(default=None),
    activity_name: Optional[str] = Query(default=None),
    activity_description: Optional[str] = Query(default=None),
    activity_location: Optional[str] = Query(default=None),
    join_url: Optional[str] = Query(default=None),
    calendar_id: Optional[str] = Query(default=None),
    all_day: Optional[str] = Query(default=None),

    # Status fields
    status: Optional[str] = Query(default=None, description="Allowed values: open, closed, cancelled."),
    active_status: Optional[str] = Query(default="active", description="Allowed values: active, archived, deleted, all."),

    # Date filters
    startdate_from: Optional[str] = Query(default=None),
    startdate_to: Optional[str] = Query(default=None),
    enddate_from: Optional[str] = Query(default=None),
    enddate_to: Optional[str] = Query(default=None),
    created_date_from: Optional[str] = Query(default=None),
    created_date_to: Optional[str] = Query(default=None),
    modified_date_from: Optional[str] = Query(default=None),
    modified_date_to: Optional[str] = Query(default=None),

    # User filters
    owner: Optional[str] = Query(default=None),
    owner_name: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    created_by_name: Optional[str] = Query(default=None),
    modified_by: Optional[str] = Query(default=None),
    modified_by_name: Optional[str] = Query(default=None),

    # Account filters
    account_id: Optional[str] = Query(default=None),
    lead_id: Optional[str] = Query(default=None),
    account_name: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    account_type: Optional[str] = Query(default=None),
    account_city: Optional[str] = Query(default=None),
    account_state: Optional[str] = Query(default=None),
    account_country: Optional[str] = Query(default=None),

    # Deal filters
    deal_id: Optional[str] = Query(default=None),
    opportunity_id: Optional[str] = Query(default=None),
    deal_name: Optional[str] = Query(default=None),
    opportunity_name: Optional[str] = Query(default=None),
    deal_status: Optional[str] = Query(default=None),

    # Contact activity filters. These target contact-role rows where contact_role = contact.
    contact_id: Optional[str] = Query(default=None),
    contact_name: Optional[str] = Query(default=None),
    contact_email: Optional[str] = Query(default=None),
    contact_phone: Optional[str] = Query(default=None),

    # Recipient filters. These target host/guest rows from lk_activity_contacts.
    recipient_type: Optional[str] = Query(default=None, description="Allowed values: host, guest."),
    recipient_source: Optional[str] = Query(default=None, description="Allowed values: user, contact. Reserved for documentation/search usage."),
    recipient_search: Optional[str] = Query(default=None),
    recipient_name: Optional[str] = Query(default=None),
    recipient_email: Optional[str] = Query(default=None),
    recipient_phone: Optional[str] = Query(default=None),
    recipient_user_id: Optional[str] = Query(default=None),
    recipient_contact_id: Optional[str] = Query(default=None),
    host_user_id: Optional[str] = Query(default=None),
    guest_user_id: Optional[str] = Query(default=None),
    guest_contact_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),

    # Follow-up filters
    is_followup: Optional[str] = Query(default=None),
    followup_date_from: Optional[str] = Query(default=None),
    followup_date_to: Optional[str] = Query(default=None),

    # Support filters
    is_support_call: Optional[str] = Query(default=None),
    support_call_type_id: Optional[str] = Query(default=None),
    support_call_type_name: Optional[str] = Query(default=None),
    support_call_criticality: Optional[str] = Query(default=None, description="Allowed values: P0, P1, P2, P3, P4."),

    # Activity record filters
    has_records: Optional[str] = Query(default=None),
    record_type: Optional[str] = Query(default=None, description="Allowed values: record, note."),
    record_name: Optional[str] = Query(default=None),
    record_details: Optional[str] = Query(default=None),
):
    """
    Protected Activities list API.

    URL:
    /activities
    """

    try:
        client_database = auth_context.get("client_database")

        filter_params = build_filter_params(
            activity_for=activity_for,
            activity_type=activity_type,
            activity_id=activity_id,
            activity_category=activity_category,
            activity_name=activity_name,
            activity_description=activity_description,
            activity_location=activity_location,
            join_url=join_url,
            calendar_id=calendar_id,
            all_day=all_day,
            status=status,
            active_status=active_status,
            startdate_from=startdate_from,
            startdate_to=startdate_to,
            enddate_from=enddate_from,
            enddate_to=enddate_to,
            created_date_from=created_date_from,
            created_date_to=created_date_to,
            modified_date_from=modified_date_from,
            modified_date_to=modified_date_to,
            owner=owner,
            owner_name=owner_name,
            created_by=created_by,
            created_by_name=created_by_name,
            modified_by=modified_by,
            modified_by_name=modified_by_name,
            account_id=account_id,
            lead_id=lead_id,
            account_name=account_name,
            lead_name=lead_name,
            account_type=account_type,
            account_city=account_city,
            account_state=account_state,
            account_country=account_country,
            deal_id=deal_id,
            opportunity_id=opportunity_id,
            deal_name=deal_name,
            opportunity_name=opportunity_name,
            deal_status=deal_status,
            contact_id=contact_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            recipient_type=recipient_type,
            recipient_source=recipient_source,
            recipient_search=recipient_search,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            recipient_user_id=recipient_user_id,
            recipient_contact_id=recipient_contact_id,
            host_user_id=host_user_id,
            guest_user_id=guest_user_id,
            guest_contact_id=guest_contact_id,
            user_id=user_id,
            is_followup=is_followup,
            followup_date_from=followup_date_from,
            followup_date_to=followup_date_to,
            is_support_call=is_support_call,
            support_call_type_id=support_call_type_id,
            support_call_type_name=support_call_type_name,
            support_call_criticality=support_call_criticality,
            has_records=has_records,
            record_type=record_type,
            record_name=record_name,
            record_details=record_details,
        )

        result = fetch_activities_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

        return success_response(
            message="Activities fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "activity_for": activity_for,
                "activity_type": activity_type,
                "search": search,
                "search_by": search_by,
                "applied_filters": filter_params,
                **result["pagination"],
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "activities": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch activities",
                error_code="LOGIKLU_ACTIVITIES_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/activities/{activity_id}")
def get_activity_detail(
    activity_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected Activity detail API.

    URL:
    /activities/{activity_id}
    """

    try:
        client_database = auth_context.get("client_database")

        activity = fetch_activity_detail(
            client_database=client_database,
            activity_id=activity_id,
        )

        if not activity:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Activity not found",
                    error_code="LOGIKLU_ACTIVITY_NOT_FOUND",
                    data={
                        "activity_id": activity_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Activity detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "activity_id": activity_id,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "activity": activity,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch activity detail",
                error_code="LOGIKLU_ACTIVITY_DETAIL_FETCH_FAILED",
                data={
                    "activity_id": activity_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
