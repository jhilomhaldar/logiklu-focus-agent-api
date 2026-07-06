# app/api/v1/endpoints/deals.py

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.deal_service import (
    SCHEMA_VERSION,
    fetch_deal_detail,
    fetch_deals_list,
)


router = APIRouter()


def build_filter_params(**kwargs: Any) -> Dict[str, Any]:
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and str(value).strip() != ""
    }


@router.get("/deals")
def get_deals(
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=10, le=100),

    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    filters: Optional[str] = Query(default=None),

    deal_id: Optional[str] = Query(default=None),
    opportunity_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    lead_id: Optional[str] = Query(default=None),
    company_id: Optional[str] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
    contact_id: Optional[str] = Query(default=None),
    lead_contact_id: Optional[str] = Query(default=None),

    deal_name: Optional[str] = Query(default=None),
    opportunity_name: Optional[str] = Query(default=None),
    deal_description: Optional[str] = Query(default=None),
    opportunity_description: Optional[str] = Query(default=None),
    account_name: Optional[str] = Query(default=None),
    lead_name: Optional[str] = Query(default=None),
    lead_type: Optional[str] = Query(default=None),

    status: Optional[str] = Query(default=None),
    deal_status: Optional[str] = Query(default=None),
    opportunity_status: Optional[str] = Query(default=None),
    opportunity_status_id: Optional[str] = Query(default=None),
    status_id: Optional[str] = Query(default=None),
    opportunity_type: Optional[str] = Query(default=None),
    deal_type: Optional[str] = Query(default=None),
    active_status: Optional[str] = Query(default=None),
    is_important: Optional[str] = Query(default=None),
    pre_deal: Optional[str] = Query(default=None),
    converted_customer_deal: Optional[str] = Query(default=None),
    situational_barometer: Optional[str] = Query(default=None),

    currency: Optional[str] = Query(default=None),
    revenue_min: Optional[float] = Query(default=None),
    revenue_max: Optional[float] = Query(default=None),
    confidencelevel_min: Optional[float] = Query(default=None),
    confidencelevel_max: Optional[float] = Query(default=None),
    confidence_level_min: Optional[float] = Query(default=None),
    confidence_level_max: Optional[float] = Query(default=None),

    closing_date_from: Optional[str] = Query(default=None),
    closing_date_to: Optional[str] = Query(default=None),
    closingdate_from: Optional[str] = Query(default=None),
    closingdate_to: Optional[str] = Query(default=None),
    created_date_from: Optional[str] = Query(default=None),
    created_date_to: Optional[str] = Query(default=None),
    modified_date_from: Optional[str] = Query(default=None),
    modified_date_to: Optional[str] = Query(default=None),
    closed_date_from: Optional[str] = Query(default=None),
    closed_date_to: Optional[str] = Query(default=None),
    official_closed_date_from: Optional[str] = Query(default=None),
    official_closed_date_to: Optional[str] = Query(default=None),

    owner: Optional[str] = Query(default=None),
    created_by: Optional[str] = Query(default=None),
    modified_by: Optional[str] = Query(default=None),
    closed_by: Optional[str] = Query(default=None),
    channel_partner: Optional[str] = Query(default=None),
    next_stage: Optional[str] = Query(default=None),
    assigned_to: Optional[str] = Query(default=None),
    assigned_user_id: Optional[str] = Query(default=None),
    assign_by: Optional[str] = Query(default=None),

    competitors: Optional[str] = Query(default=None),
    note: Optional[str] = Query(default=None),

    product_name: Optional[str] = Query(default=None),
    product_category_id: Optional[str] = Query(default=None),
    product_id: Optional[str] = Query(default=None),
    page_id: Optional[str] = Query(default=None),
    product_total_min: Optional[float] = Query(default=None),
    product_total_max: Optional[float] = Query(default=None),
    product_base_price_min: Optional[float] = Query(default=None),
    product_base_price_max: Optional[float] = Query(default=None),
    qty_min: Optional[float] = Query(default=None),
    qty_max: Optional[float] = Query(default=None),

    closed_state: Optional[str] = Query(default=None),
    closed_currency: Optional[str] = Query(default=None),
    closed_amount_min: Optional[float] = Query(default=None),
    closed_amount_max: Optional[float] = Query(default=None),
):
    """
    Protected Deals list API.

    URL:
    /deals
    """

    try:
        client_database = auth_context.get("client_database")

        filter_params = build_filter_params(
            deal_id=deal_id,
            opportunity_id=opportunity_id,
            account_id=account_id,
            lead_id=lead_id,
            company_id=company_id,
            customer_id=customer_id,
            contact_id=contact_id,
            lead_contact_id=lead_contact_id,

            deal_name=deal_name,
            opportunity_name=opportunity_name,
            deal_description=deal_description,
            opportunity_description=opportunity_description,
            account_name=account_name,
            lead_name=lead_name,
            lead_type=lead_type,

            status=status,
            deal_status=deal_status,
            opportunity_status=opportunity_status,
            opportunity_status_id=opportunity_status_id,
            status_id=status_id,
            opportunity_type=opportunity_type,
            deal_type=deal_type,
            active_status=active_status,
            is_important=is_important,
            pre_deal=pre_deal,
            converted_customer_deal=converted_customer_deal,
            situational_barometer=situational_barometer,

            currency=currency,
            revenue_min=revenue_min,
            revenue_max=revenue_max,
            confidencelevel_min=confidencelevel_min,
            confidencelevel_max=confidencelevel_max,
            confidence_level_min=confidence_level_min,
            confidence_level_max=confidence_level_max,

            closing_date_from=closing_date_from,
            closing_date_to=closing_date_to,
            closingdate_from=closingdate_from,
            closingdate_to=closingdate_to,
            created_date_from=created_date_from,
            created_date_to=created_date_to,
            modified_date_from=modified_date_from,
            modified_date_to=modified_date_to,
            closed_date_from=closed_date_from,
            closed_date_to=closed_date_to,
            official_closed_date_from=official_closed_date_from,
            official_closed_date_to=official_closed_date_to,

            owner=owner,
            created_by=created_by,
            modified_by=modified_by,
            closed_by=closed_by,
            channel_partner=channel_partner,
            next_stage=next_stage,
            assigned_to=assigned_to,
            assigned_user_id=assigned_user_id,
            assign_by=assign_by,

            competitors=competitors,
            note=note,

            product_name=product_name,
            product_category_id=product_category_id,
            product_id=product_id,
            page_id=page_id,
            product_total_min=product_total_min,
            product_total_max=product_total_max,
            product_base_price_min=product_base_price_min,
            product_base_price_max=product_base_price_max,
            qty_min=qty_min,
            qty_max=qty_max,

            closed_state=closed_state,
            closed_currency=closed_currency,
            closed_amount_min=closed_amount_min,
            closed_amount_max=closed_amount_max,
        )

        result = fetch_deals_list(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            filters=filters,
            filter_params=filter_params,
        )

        return success_response(
            message="Deals fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "search": search,
                "search_by": search_by,
                "applied_filters": filter_params,
                **result["pagination"],
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "deals": result["items"],
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch deals",
                error_code="LOGIKLU_DEALS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/deals/{deal_id}")
def get_deal_detail(
    deal_id: int,
    auth_context: dict = Depends(authenticate_request),
):
    """
    Protected Deal detail API.

    URL:
    /deals/{deal_id}
    """

    try:
        client_database = auth_context.get("client_database")

        deal = fetch_deal_detail(
            client_database=client_database,
            deal_id=deal_id,
        )

        if not deal:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Deal not found",
                    error_code="LOGIKLU_DEAL_NOT_FOUND",
                    data={
                        "deal_id": deal_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Deal detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "protected",
                "deal_id": deal_id,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "deal": deal,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch deal detail",
                error_code="LOGIKLU_DEAL_DETAIL_FETCH_FAILED",
                data={
                    "deal_id": deal_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
