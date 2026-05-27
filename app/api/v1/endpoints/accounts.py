import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.account_service import (
    fetch_accounts,
    count_accounts,
    fetch_account_dynamic_details,
    fetch_contacts_for_accounts,
    fetch_account_by_id,
)

router = APIRouter()


def parse_filters(filters: Optional[str]):
    if not filters:
        return None

    try:
        parsed = json.loads(filters)

        if isinstance(parsed, list):
            return parsed

        return None

    except Exception:
        return None


@router.get("/accounts")
def get_accounts(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    lead_publish_status: str = Query(default="active"),
    computed_lead_category: str = Query(default="all"),
    filters: Optional[str] = Query(default=None),
):
    try:
        client_database = auth_context.get("client_database")
        parsed_filters = parse_filters(filters)

        accounts = fetch_accounts(
            client_database=client_database,
            limit=limit,
            offset=offset,
            search=search,
            lead_publish_status=lead_publish_status,
            computed_lead_category=computed_lead_category,
            filters=parsed_filters,
        )

        total_records = count_accounts(
            client_database=client_database,
            search=search,
            lead_publish_status=lead_publish_status,
            computed_lead_category=computed_lead_category,
            filters=parsed_filters,
        )

        if accounts:
            account_ids = [int(account["account_id"]) for account in accounts]

            dynamic_details = fetch_account_dynamic_details(
                client_database=client_database,
                account_ids=account_ids,
            )

            contacts_by_account = fetch_contacts_for_accounts(
                client_database=client_database,
                account_ids=account_ids,
            )

            for account in accounts:
                account_id = int(account["account_id"])
                account["dynamic_fields"] = dynamic_details.get(account_id, {})
                account["contacts"] = contacts_by_account.get(account_id, [])

        return success_response(
            message="Accounts fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "limit": limit,
                "offset": offset,
                "search": search,
                "lead_publish_status": lead_publish_status,
                "computed_lead_category": computed_lead_category,
                "record_count": len(accounts),
                "total_records": total_records,
            },
            data={
                "accounts": accounts,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch accounts",
                error_code="ACCOUNTS_FETCH_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
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
                    data={
                        "account_id": account_id,
                        "timestamp": current_utc_datetime(),
                    },
                ),
            )

        return success_response(
            message="Account detail fetched successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "account_id": account_id,
            },
            data={
                "account": account,
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to fetch account detail",
                error_code="ACCOUNT_DETAIL_FETCH_FAILED",
                data={
                    "account_id": account_id,
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )