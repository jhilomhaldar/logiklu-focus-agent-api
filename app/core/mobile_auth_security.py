import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict

from fastapi import Request

from app.db.master import get_master_connection

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
    auth_version: int = 1,
    session_id: str = "",
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
        "auth_version": int(auth_version or 1),
    }

    # Device Auth tokens carry the exact zp_user_login.login_session.
    # Existing /auth/login callers may omit it and keep the old token contract.
    session_id = str(session_id or "").strip()
    if session_id:
        payload["session_id"] = session_id

    return {
        "access_token": create_jwt_token(payload),
        "token_type": "Bearer",
        "expires_in": expires_in,
    }



def _current_user_auth_version(user_id: int) -> int:
    """
    Return the current global user-token version.

    Incrementing zp_users.auth_token_version immediately invalidates every
    previously issued LogiKlu mobile/device access JWT for that user.
    """
    connection = None
    try:
        connection = get_master_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT auth_token_version
                FROM zp_users
                WHERE id = %s
                LIMIT 1
                """,
                (int(user_id),),
            )
            row = cursor.fetchone()

        if not row:
            raise MobileTokenError("User no longer exists")

        try:
            value = int(row.get("auth_token_version") or 1)
        except Exception:
            value = 1

        return value if value > 0 else 1

    except MobileTokenError:
        raise
    except Exception as exc:
        raise MobileTokenError(
            "Unable to validate mobile access token"
        ) from exc
    finally:
        if connection:
            connection.close()

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

        # Tokens issued before auth_token_version was added are treated as
        # version 1. Once logout-all/delete-all increments the database value,
        # those old tokens are invalid immediately.
        try:
            token_auth_version = int(payload.get("auth_version") or 1)
        except Exception:
            token_auth_version = 1

        current_auth_version = _current_user_auth_version(user_id)
        if token_auth_version != current_auth_version:
            raise MobileTokenError(
                "This login has been revoked. Please sign in again."
            )

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


def _validate_active_device_session(
    user_id: int,
    session_id: str,
) -> Dict[str, Any]:
    """
    Validate that the exact Device Auth login session carried in the JWT
    still exists and is active in zp_user_login.
    """
    session_id = str(session_id or "").strip()

    if not session_id:
        raise MobileTokenError(
            "This access token is not bound to a Device Auth session. Please sign in again."
        )

    connection = None

    try:
        connection = get_master_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    login_source,
                    device_id,
                    login_session,
                    refresh_expires_date,
                    revoked_date,
                    revoked_reason,
                    session_status,
                    login_time,
                    logout_time
                FROM zp_user_login
                WHERE user_id = %s
                  AND login_session = %s
                LIMIT 1
                """,
                (
                    int(user_id),
                    session_id,
                ),
            )
            session = cursor.fetchone()

        if not session:
            raise MobileTokenError(
                "This login session no longer exists. Please sign in again."
            )

        if str(session.get("session_status") or "").strip().lower() != "active":
            raise MobileTokenError(
                "This login session is no longer active. Please sign in again."
            )

        if session.get("revoked_date") is not None:
            raise MobileTokenError(
                "This login session has been revoked. Please sign in again."
            )

        if session.get("logout_time") is not None:
            raise MobileTokenError(
                "This login session has been logged out. Please sign in again."
            )

        refresh_expires_date = session.get("refresh_expires_date")
        if refresh_expires_date is not None:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            # PyMySQL normally returns naive DATETIME values.
            if getattr(refresh_expires_date, "tzinfo", None) is None:
                refresh_expires_date = refresh_expires_date.replace(
                    tzinfo=timezone.utc
                )

            if refresh_expires_date <= now:
                raise MobileTokenError(
                    "This login session has expired. Please sign in again."
                )

        return session

    except MobileTokenError:
        raise
    except Exception as exc:
        raise MobileTokenError(
            "Unable to validate the active Device Auth session"
        ) from exc
    finally:
        if connection:
            connection.close()


def authenticate_active_device_user(request: Request) -> Dict[str, Any]:
    """
    Strict authentication for APIs that must work only while the exact
    Device Auth session is currently logged in.

    Validates:
    - JWT signature / expiry / issuer / audience
    - API environment
    - auth_token_version
    - JWT session_id against zp_user_login
    - session_status = active
    - revoked_date IS NULL
    - logout_time IS NULL
    - refresh session has not expired
    """
    payload = authenticate_mobile_user(request)

    user_id = int(payload.get("user_id") or 0)
    session_id = str(payload.get("session_id") or "").strip()

    session = _validate_active_device_session(
        user_id=user_id,
        session_id=session_id,
    )

    context = dict(payload)
    context["active_session"] = {
        "id": int(session.get("id") or 0),
        "session_id": str(session.get("login_session") or ""),
        "device_id": str(session.get("device_id") or ""),
        "login_source": str(session.get("login_source") or ""),
    }

    request.state.mobile_auth_context = context
    return context

