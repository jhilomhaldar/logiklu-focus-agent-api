import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict

from fastapi import Request

from app.core.security import (
    base64url_decode,
    create_jwt_token,
    get_api_environment,
    get_jwt_issuer,
    get_jwt_secret_key,
)


MOBILE_TOKEN_AUDIENCE = "logiklu-mobile"
MOBILE_TOKEN_TYPE = "mobile_user_access"


class MobileTokenError(Exception):
    pass


def get_mobile_token_expire_seconds() -> int:
    try:
        value = int(os.getenv("MOBILE_AUTH_TOKEN_EXPIRE_SECONDS", "3600"))
    except Exception:
        value = 3600

    return value if value > 0 else 3600


def issue_mobile_user_token(
    user_id: int,
    group_code: str,
    login_point: int,
) -> Dict[str, Any]:
    now_ts = int(time.time())
    expires_in = get_mobile_token_expire_seconds()

    payload = {
        "iss": get_jwt_issuer(),
        "aud": MOBILE_TOKEN_AUDIENCE,
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "token_type": MOBILE_TOKEN_TYPE,
        "iat": now_ts,
        "exp": now_ts + expires_in,
        "api_environment": get_api_environment(),
        "user_id": int(user_id),
        "group_code": str(group_code or ""),
        "login_point": int(login_point or 0),
    }

    return {
        "access_token": create_jwt_token(payload),
        "token_type": "Bearer",
        "expires_in": expires_in,
    }


def decode_mobile_user_token(token: str) -> Dict[str, Any]:
    try:
        parts = str(token or "").split(".")
        if len(parts) != 3:
            raise MobileTokenError("Token must contain three parts")

        header_encoded, payload_encoded, signature_encoded = parts
        signing_input = f"{header_encoded}.{payload_encoded}"

        expected_signature = hmac.new(
            get_jwt_secret_key().encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        actual_signature = base64url_decode(signature_encoded)

        if not hmac.compare_digest(expected_signature, actual_signature):
            raise MobileTokenError("Invalid token signature")

        header = json.loads(base64url_decode(header_encoded).decode("utf-8"))
        payload = json.loads(base64url_decode(payload_encoded).decode("utf-8"))

        if header.get("alg") != "HS256":
            raise MobileTokenError("Invalid token algorithm")

        if int(payload.get("exp") or 0) < int(time.time()):
            raise MobileTokenError("Mobile access token has expired")

        if payload.get("iss") != get_jwt_issuer():
            raise MobileTokenError("Invalid token issuer")

        if payload.get("aud") != MOBILE_TOKEN_AUDIENCE:
            raise MobileTokenError("Invalid token audience")

        if payload.get("token_type") != MOBILE_TOKEN_TYPE:
            raise MobileTokenError("Invalid token type")

        if str(payload.get("api_environment") or "").lower() != get_api_environment():
            raise MobileTokenError("Mobile access token belongs to another API environment")

        user_id = int(payload.get("user_id") or 0)
        if user_id <= 0:
            raise MobileTokenError("Mobile access token does not contain a valid user")

        return payload

    except MobileTokenError:
        raise
    except Exception as exc:
        raise MobileTokenError("Invalid mobile access token") from exc


def get_mobile_bearer_token(request: Request) -> str:
    authorization = str(request.headers.get("Authorization") or "").strip()

    if not authorization:
        raise MobileTokenError("Missing bearer token")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise MobileTokenError("Invalid Authorization header")

    return parts[1].strip()


def authenticate_mobile_user(request: Request) -> Dict[str, Any]:
    token = get_mobile_bearer_token(request)
    payload = decode_mobile_user_token(token)
    request.state.mobile_auth_context = payload
    return payload
