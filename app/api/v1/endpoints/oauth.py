from pydantic import BaseModel
from fastapi import APIRouter, Request

from app.core.security import issue_client_credentials_token


router = APIRouter()


class OAuthTokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


@router.post("/oauth/token")
def oauth_token(payload: OAuthTokenRequest, request: Request):
    return issue_client_credentials_token(
        client_id=payload.client_id,
        client_secret=payload.client_secret,
        grant_type=payload.grant_type,
        request=request,
    )