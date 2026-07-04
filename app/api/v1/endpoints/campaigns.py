import json
import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.campaign_service import (
    SCHEMA_VERSION,
    CAMPAIGN_SEARCH_FIELDS,
    fetch_campaigns,
    count_campaigns,
    fetch_campaign_by_id,
)


router = APIRouter()


RESERVED_QUERY_PARAMS = {
    "page",
    "per_page",
    "search",
    "search_by",
    "searchby",
    "filters",
    "include_details",
    "created_date_from",
    "created_date_to",
    "sent_date_from",
    "sent_date_to",
    "sort_by",
    "sort_order",
    "total_recipients_min",
    "total_recipients_max",
    "delivered_min",
    "delivered_max",
    "not_opened_min",
    "not_opened_max",
    "opened_min",
    "opened_max",
    "clicked_min",
    "clicked_max",
    "hard_bounced_min",
    "hard_bounced_max",
    "soft_bounced_min",
    "soft_bounced_max",
    "total_bounced_min",
    "total_bounced_max",
    "unsubscribed_min",
    "unsubscribed_max",
}


EXACT_QUERY_FIELDS = {
    "campaign_id",
    "id",
    "status",
    "active_status",
    "created_by",
    "updated_by",
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

        if clean_key not in CAMPAIGN_SEARCH_FIELDS:
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


@router.get("/campaigns")
def get_campaigns(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    search_by: Optional[str] = Query(default=None),
    include_details: bool = Query(default=True),
    created_date_from: Optional[str] = Query(default=None),
    created_date_to: Optional[str] = Query(default=None),
    sent_date_from: Optional[str] = Query(default=None),
    sent_date_to: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default=None),
    sort_order: str = Query(default="asc"),
    total_recipients_min: Optional[int] = Query(default=None),
    total_recipients_max: Optional[int] = Query(default=None),
    delivered_min: Optional[int] = Query(default=None),
    delivered_max: Optional[int] = Query(default=None),
    not_opened_min: Optional[int] = Query(default=None),
    not_opened_max: Optional[int] = Query(default=None),
    opened_min: Optional[int] = Query(default=None),
    opened_max: Optional[int] = Query(default=None),
    clicked_min: Optional[int] = Query(default=None),
    clicked_max: Optional[int] = Query(default=None),
    hard_bounced_min: Optional[int] = Query(default=None),
    hard_bounced_max: Optional[int] = Query(default=None),
    soft_bounced_min: Optional[int] = Query(default=None),
    soft_bounced_max: Optional[int] = Query(default=None),
    total_bounced_min: Optional[int] = Query(default=None),
    total_bounced_max: Optional[int] = Query(default=None),
    unsubscribed_min: Optional[int] = Query(default=None),
    unsubscribed_max: Optional[int] = Query(default=None),
    filters: Optional[str] = Query(default=None),
):
    """
    Protected Campaign list API.

    URL:
    /campaigns

    Pagination standard:
    page + per_page
    """

    try:
        client_database = auth_context.get("client_database")

        parsed_filters = parse_filters(filters)
        query_filters = parse_multi_field_filters(request)
        final_filters = parsed_filters + query_filters

        campaigns = fetch_campaigns(
            client_database=client_database,
            page=page,
            per_page=per_page,
            search=search,
            search_by=search_by,
            include_details=include_details,
            created_date_from=created_date_from,
            created_date_to=created_date_to,
            sent_date_from=sent_date_from,
            sent_date_to=sent_date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            total_recipients_min=total_recipients_min,
            total_recipients_max=total_recipients_max,
            delivered_min=delivered_min,
            delivered_max=delivered_max,
            not_opened_min=not_opened_min,
            not_opened_max=not_opened_max,
            opened_min=opened_min,
            opened_max=opened_max,
            clicked_min=clicked_min,
            clicked_max=clicked_max,
            hard_bounced_min=hard_bounced_min,
            hard_bounced_max=hard_bounced_max,
            soft_bounced_min=soft_bounced_min,
            soft_bounced_max=soft_bounced_max,
            total_bounced_min=total_bounced_min,
            total_bounced_max=total_bounced_max,
            unsubscribed_min=unsubscribed_min,
            unsubscribed_max=unsubscribed_max,
            filters=final_filters,
        )

        total_records = count_campaigns(
            client_database=client_database,
            search=search,
            search_by=search_by,
            created_date_from=created_date_from,
            created_date_to=created_date_to,
            sent_date_from=sent_date_from,
            sent_date_to=sent_date_to,
            total_recipients_min=total_recipients_min,
            total_recipients_max=total_recipients_max,
            delivered_min=delivered_min,
            delivered_max=delivered_max,
            not_opened_min=not_opened_min,
            not_opened_max=not_opened_max,
            opened_min=opened_min,
            opened_max=opened_max,
            clicked_min=clicked_min,
            clicked_max=clicked_max,
            hard_bounced_min=hard_bounced_min,
            hard_bounced_max=hard_bounced_max,
            soft_bounced_min=soft_bounced_min,
            soft_bounced_max=soft_bounced_max,
            total_bounced_min=total_bounced_min,
            total_bounced_max=total_bounced_max,
            unsubscribed_min=unsubscribed_min,
            unsubscribed_max=unsubscribed_max,
            filters=final_filters,
        )

        total_pages = math.ceil(total_records / per_page) if total_records > 0 else 0
        offset = (page - 1) * per_page

        return success_response(
            message="Campaigns fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "search": search,
                "search_by": search_by,
                "include_details": include_details,
                "created_date_from": created_date_from,
                "created_date_to": created_date_to,
                "sent_date_from": sent_date_from,
                "sent_date_to": sent_date_to,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "applied_filters": final_filters,
                "stats_filters": {
                    "total_recipients_min": total_recipients_min,
                    "total_recipients_max": total_recipients_max,
                    "delivered_min": delivered_min,
                    "delivered_max": delivered_max,
                    "not_opened_min": not_opened_min,
                    "not_opened_max": not_opened_max,
                    "opened_min": opened_min,
                    "opened_max": opened_max,
                    "clicked_min": clicked_min,
                    "clicked_max": clicked_max,
                    "hard_bounced_min": hard_bounced_min,
                    "hard_bounced_max": hard_bounced_max,
                    "soft_bounced_min": soft_bounced_min,
                    "soft_bounced_max": soft_bounced_max,
                    "total_bounced_min": total_bounced_min,
                    "total_bounced_max": total_bounced_max,
                    "unsubscribed_min": unsubscribed_min,
                    "unsubscribed_max": unsubscribed_max,
                },
                "page": page,
                "per_page": per_page,
                "offset": offset,
                "record_count": len(campaigns),
                "total_records": total_records,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "campaigns": campaigns,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch campaigns",
                error_code="CAMPAIGNS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.get("/campaigns/{campaign_id}")
def get_campaign_detail(
    campaign_id: int,
    auth_context: dict = Depends(authenticate_request),
    include_details: bool = Query(default=True),
):
    """
    Protected Campaign detail API.

    URL:
    /campaigns/{campaign_id}
    """

    try:
        client_database = auth_context.get("client_database")

        campaign = fetch_campaign_by_id(
            client_database=client_database,
            campaign_id=campaign_id,
            include_details=include_details,
        )

        if not campaign:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    message="Campaign not found",
                    error_code="CAMPAIGN_NOT_FOUND",
                    data={
                        "campaign_id": campaign_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Campaign detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "campaign_id": campaign_id,
                "include_details": include_details,
            },
            data={
                "schema_version": SCHEMA_VERSION,
                "campaign": campaign,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch campaign detail",
                error_code="CAMPAIGN_DETAIL_FETCH_FAILED",
                data={
                    "campaign_id": campaign_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
