# app/api/v1/endpoints/focus_account_intelligence.py

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.focus_account_intelligence_service import (
    fetch_focus_account_intelligence_list,
)
from app.services.focus_company_intelligence_service import (
    fetch_focus_company_intelligence,
)


router = APIRouter()


def build_filter_params(**kwargs: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and str(value).strip() != ""
    }


@router.get("/demo/{client_database}/focus/account-intelligence")
def get_demo_focus_account_intelligence(
    client_database: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    account_id: Optional[str] = Query(default=None),
    lead_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    account_name: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    website: Optional[str] = Query(default=None),
    company_domain: Optional[str] = Query(default=None),
    industry: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    email: Optional[str] = Query(default=None),
    phone: Optional[str] = Query(default=None),
    owner: Optional[str] = Query(default=None),
    lead_category: Optional[str] = Query(default=None),
    lead_type: Optional[str] = Query(default=None),
    lead_status: Optional[str] = Query(default=None),
    active_status: Optional[str] = Query(default=None),

    contact_name: Optional[str] = Query(default=None),
    contact_email: Optional[str] = Query(default=None),
    contact_phone: Optional[str] = Query(default=None),

    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    priority_level: Optional[str] = Query(default=None),
    engagement_level: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),

    activity_score_min: Optional[float] = Query(default=None),
    activity_score_max: Optional[float] = Query(default=None),
    depth_score_min: Optional[float] = Query(default=None),
    depth_score_max: Optional[float] = Query(default=None),
    sustenance_score_min: Optional[float] = Query(default=None),
    sustenance_score_max: Optional[float] = Query(default=None),
    sustainment_score_min: Optional[float] = Query(default=None),
    sustainment_score_max: Optional[float] = Query(default=None),
    context_score_min: Optional[float] = Query(default=None),
    context_score_max: Optional[float] = Query(default=None),
    contextual_score_min: Optional[float] = Query(default=None),
    contextual_score_max: Optional[float] = Query(default=None),
    conversion_score_min: Optional[float] = Query(default=None),
    conversion_score_max: Optional[float] = Query(default=None),
    interest_score_min: Optional[float] = Query(default=None),
    interest_score_max: Optional[float] = Query(default=None),
    priority_score_min: Optional[float] = Query(default=None),
    priority_score_max: Optional[float] = Query(default=None),
    final_score_min: Optional[float] = Query(default=None),
    final_score_max: Optional[float] = Query(default=None),
    total_score_min: Optional[float] = Query(default=None),
    total_score_max: Optional[float] = Query(default=None),

    include_journey: bool = Query(default=True),
):
    """
    Demo endpoint remains available.

    Supports account-style search, contact search, priority filters,
    and score range filters.
    """

    try:
        filter_params = build_filter_params(
            account_id=account_id,
            lead_id=lead_id,
            company_name=company_name,
            account_name=account_name,
            lead_name=lead_name,
            website=website,
            company_domain=company_domain,
            industry=industry,
            city=city,
            state=state,
            country=country,
            email=email,
            phone=phone,
            owner=owner,
            lead_category=lead_category,
            lead_type=lead_type,
            lead_status=lead_status,
            active_status=active_status,

            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,

            priority_level=priority_level,
            engagement_level=engagement_level,

            activity_score_min=activity_score_min,
            activity_score_max=activity_score_max,
            depth_score_min=depth_score_min,
            depth_score_max=depth_score_max,
            sustenance_score_min=sustenance_score_min,
            sustenance_score_max=sustenance_score_max,
            sustainment_score_min=sustainment_score_min,
            sustainment_score_max=sustainment_score_max,
            context_score_min=context_score_min,
            context_score_max=context_score_max,
            contextual_score_min=contextual_score_min,
            contextual_score_max=contextual_score_max,
            conversion_score_min=conversion_score_min,
            conversion_score_max=conversion_score_max,
            interest_score_min=interest_score_min,
            interest_score_max=interest_score_max,
            priority_score_min=priority_score_min,
            priority_score_max=priority_score_max,
            final_score_min=final_score_min,
            final_score_max=final_score_max,
            total_score_min=total_score_min,
            total_score_max=total_score_max,
        )

        result = fetch_focus_account_intelligence_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
            include_journey=include_journey,
        )

        response_data = success_response(
            message="LogiKlu account intelligence list fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "client_database": client_database,
                "mode": "demo",
                "search": search,
                "search_by": search_by,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "include_journey": include_journey,
                "applied_filters": filter_params,
                **result["pagination"],
            },
            data={
                "logiklu_focus_account_intelligence": result["items"],
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
        )

    except Exception as exc:
        response_data = error_response(
            message="Failed to fetch demo LogiKlu Focus account intelligence list",
            error_code="DEMO_LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
            data={
                "client_database": client_database,
                "error": str(exc),
                "timestamp": current_utc_datetime(),
            },
        )

        return Response(
            content=json.dumps(response_data, indent=2, default=str),
            media_type="application/json",
            status_code=500,
        )


@router.get("/focus/account-intelligence")
def get_focus_account_intelligence(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    account_id: Optional[str] = Query(default=None),
    lead_id: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    account_name: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    website: Optional[str] = Query(default=None),
    company_domain: Optional[str] = Query(default=None),
    industry: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    email: Optional[str] = Query(default=None),
    phone: Optional[str] = Query(default=None),
    owner: Optional[str] = Query(default=None),
    lead_category: Optional[str] = Query(default=None),
    lead_type: Optional[str] = Query(default=None),
    lead_status: Optional[str] = Query(default=None),
    active_status: Optional[str] = Query(default=None),

    contact_name: Optional[str] = Query(default=None),
    contact_email: Optional[str] = Query(default=None),
    contact_phone: Optional[str] = Query(default=None),

    interest_level: Optional[str] = Query(default=None),
    priority_label: Optional[str] = Query(default=None),
    priority_level: Optional[str] = Query(default=None),
    engagement_level: Optional[str] = Query(default=None),
    is_shortlisted: Optional[str] = Query(default=None),

    activity_score_min: Optional[float] = Query(default=None),
    activity_score_max: Optional[float] = Query(default=None),
    depth_score_min: Optional[float] = Query(default=None),
    depth_score_max: Optional[float] = Query(default=None),
    sustenance_score_min: Optional[float] = Query(default=None),
    sustenance_score_max: Optional[float] = Query(default=None),
    sustainment_score_min: Optional[float] = Query(default=None),
    sustainment_score_max: Optional[float] = Query(default=None),
    context_score_min: Optional[float] = Query(default=None),
    context_score_max: Optional[float] = Query(default=None),
    contextual_score_min: Optional[float] = Query(default=None),
    contextual_score_max: Optional[float] = Query(default=None),
    conversion_score_min: Optional[float] = Query(default=None),
    conversion_score_max: Optional[float] = Query(default=None),
    interest_score_min: Optional[float] = Query(default=None),
    interest_score_max: Optional[float] = Query(default=None),
    priority_score_min: Optional[float] = Query(default=None),
    priority_score_max: Optional[float] = Query(default=None),
    final_score_min: Optional[float] = Query(default=None),
    final_score_max: Optional[float] = Query(default=None),
    total_score_min: Optional[float] = Query(default=None),
    total_score_max: Optional[float] = Query(default=None),
):
    """
    Protected actual API endpoint.

    URL:
    /focus/account-intelligence

    Journey is included by default.
    Caller does not need to pass include_journey=true.
    """

    try:
        client_database = auth_context.get("client_database")

        filter_params = build_filter_params(
            account_id=account_id,
            lead_id=lead_id,
            company_name=company_name,
            account_name=account_name,
            lead_name=lead_name,
            website=website,
            company_domain=company_domain,
            industry=industry,
            city=city,
            state=state,
            country=country,
            email=email,
            phone=phone,
            owner=owner,
            lead_category=lead_category,
            lead_type=lead_type,
            lead_status=lead_status,
            active_status=active_status,

            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,

            priority_level=priority_level,
            engagement_level=engagement_level,

            activity_score_min=activity_score_min,
            activity_score_max=activity_score_max,
            depth_score_min=depth_score_min,
            depth_score_max=depth_score_max,
            sustenance_score_min=sustenance_score_min,
            sustenance_score_max=sustenance_score_max,
            sustainment_score_min=sustainment_score_min,
            sustainment_score_max=sustainment_score_max,
            context_score_min=context_score_min,
            context_score_max=context_score_max,
            contextual_score_min=contextual_score_min,
            contextual_score_max=contextual_score_max,
            conversion_score_min=conversion_score_min,
            conversion_score_max=conversion_score_max,
            interest_score_min=interest_score_min,
            interest_score_max=interest_score_max,
            priority_score_min=priority_score_min,
            priority_score_max=priority_score_max,
            final_score_min=final_score_min,
            final_score_max=final_score_max,
            total_score_min=total_score_min,
            total_score_max=total_score_max,
        )

        result = fetch_focus_account_intelligence_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
            interest_level=interest_level,
            priority_label=priority_label,
            is_shortlisted=is_shortlisted,
            include_journey=True,
        )

        return success_response(
            message="LogiKlu account intelligence list fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "search": search,
                "search_by": search_by,
                "interest_level": interest_level,
                "priority_label": priority_label,
                "is_shortlisted": is_shortlisted,
                "include_journey": True,
                "applied_filters": filter_params,
                **result["pagination"],
            },
            data={
                "logiklu_focus_account_intelligence": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch LogiKlu account intelligence list",
                error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_LIST_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/focus/account-intelligence/{account_id}")
def get_focus_account_intelligence_detail(
    account_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected actual API endpoint for one account intelligence.

    New URL:
    /focus/account-intelligence/{account_id}
    """

    try:
        client_database = auth_context.get("client_database")

        intelligence = fetch_focus_company_intelligence(
            client_database=client_database,
            lead_id=account_id,
        )

        if not intelligence:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="No LogiKlu account intelligence found for the requested account_id",
                    error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_NOT_FOUND",
                    data={
                        "account_id": account_id,
                        "reason": "The requested account_id is not available in the current LogiKlu Focus intelligence dataset.",
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="LogiKlu Focus account intelligence fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "account_id": account_id,
                "mode": "protected",
            },
            data={
                "logiklu_focus_account_inetellegence": intelligence,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch LogiKlu Focus account intelligence",
                error_code="LOGIKLU_FOCUS_ACCOUNT_INTELLIGENCE_FETCH_FAILED",
                data={
                    "account_id": account_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
