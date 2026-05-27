from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.response import success_response, error_response, current_utc_datetime
from app.core.security import authenticate_request
from app.services.contact_service import fetch_contacts, count_contacts, fetch_contact_by_id

router = APIRouter()


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
):
    try:
        client_database = auth_context.get("client_database")

        contacts = fetch_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
            limit=limit,
            offset=offset,
        )

        total_records = count_contacts(
            client_database=client_database,
            account_id=account_id,
            account_search=account_search,
            associated_accounts_only=associated_accounts_only,
            search=search,
            search_by=search_by,
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