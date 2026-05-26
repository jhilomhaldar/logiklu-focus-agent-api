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
    filters: Optional[str] = Query(default=None),
    include_details: bool = Query(default=True),
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
            filters=parsed_filters,
        )

        total_records = count_accounts(
            client_database=client_database,
            search=search,
            lead_publish_status=lead_publish_status,
            filters=parsed_filters,
        )

        if include_details and accounts:
            account_ids = [int(account["account_id"]) for account in accounts]

            dynamic_details = fetch_account_dynamic_details(
                client_database=client_database,
                account_ids=account_ids,
            )

            for account in accounts:
                account_id = int(account["account_id"])
                account["dynamic_fields"] = dynamic_details.get(account_id, {})

        return success_response(
            message="Accounts fetched successfully",
            meta={                
                "generated_at": current_utc_datetime(),                
                "limit": limit,
                "offset": offset,
                "search": search,
                "lead_publish_status": lead_publish_status,
                "include_details": include_details,
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