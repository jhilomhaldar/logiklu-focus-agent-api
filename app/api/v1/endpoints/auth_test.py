from fastapi import APIRouter, Depends, Request

from app.core.response import success_response, current_utc_datetime
from app.core.security import authenticate_request

router = APIRouter()


@router.get("/auth/test")
async def auth_test(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
):
    return success_response(
        message="Authentication successful",
        data={
            "api_client_id": auth_context.get("api_client_id"),
            "domain_id": auth_context.get("domain_id"),
            "api_client_name": auth_context.get("api_client_name"),
            "account_name": auth_context.get("account_name"),
            "client_database": auth_context.get("client_database"),
            "websitename": auth_context.get("websitename"),
            "timezone": auth_context.get("timezone"),
            "timestamp": current_utc_datetime(),
        },
    )