from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.core.mobile_auth_security import (
    MobileTokenError,
    authenticate_active_device_user,
)
from app.core.response import (
    current_utc_datetime,
    error_response,
    success_response,
)
from app.core.security import get_api_environment
from app.schemas.user_profile import UserChangePasswordRequest
from app.services.user_profile_service import (
    UserProfileServiceError,
    change_user_password,
    get_user_profile,
)


router = APIRouter(prefix="/user")


def _meta(authentication_status: str = ""):
    meta = {
        "generated_at": current_utc_datetime(),
        "mode": "user_profile",
        "environment": get_api_environment(),
        "schema_version": "logiklu_user_profile.v1",
    }

    if authentication_status:
        meta["authentication_status"] = authentication_status

    return meta


def _mobile_token_error_response(
    exc: MobileTokenError,
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_response(
            message=str(exc),
            error_code="MOBILE_AUTH_TOKEN_INVALID",
            data={
                "timestamp": current_utc_datetime(),
            },
        ),
    )


def _profile_error_response(
    exc: UserProfileServiceError,
) -> JSONResponse:
    data = dict(exc.data or {})
    data["timestamp"] = current_utc_datetime()

    return JSONResponse(
        status_code=exc.http_status,
        content=error_response(
            message=exc.message,
            error_code=exc.error_code,
            data=data,
        ),
    )


def _unhandled_error(
    message: str,
    error_code: str,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=error_response(
            message=message,
            error_code=error_code,
            data={
                "error": str(exc),
                "timestamp": current_utc_datetime(),
            },
        ),
    )


@router.get("/profile/")
def view_profile(
    request: Request,
    domain_id: int = Query(..., gt=0),
    account_id: int = Query(..., gt=0),
):
    """
    Return the currently logged-in user's profile for the selected account.

    Security:
    - Authorization: Bearer <Device Auth access token>
    - token must belong to a CURRENT active zp_user_login session
    - user_id comes only from the authenticated token
    - domain_id/account_id identify the selected LogiKlu account
    """
    try:
        auth_context = authenticate_active_device_user(
            request
        )

        result = get_user_profile(
            user_id=int(
                auth_context.get("user_id") or 0
            ),
            domain_id=domain_id,
            account_id=account_id,
        )

        return success_response(
            message="Profile fetched successfully",
            meta={
                **_meta("authenticated"),
                "domain_id": domain_id,
                "account_id": account_id,
            },
            data=result,
        )

    except MobileTokenError as exc:
        return _mobile_token_error_response(exc)
    except UserProfileServiceError as exc:
        return _profile_error_response(exc)
    except Exception as exc:
        return _unhandled_error(
            "Unable to fetch profile",
            "USER_PROFILE_FETCH_FAILED",
            exc,
        )


@router.post("/profile/change-password")
def change_password(
    payload: UserChangePasswordRequest,
    request: Request,
):
    """
    Change the currently logged-in user's LogiKlu password.

    Security:
    - Authorization: Bearer <Device Auth access token>
    - token must belong to a CURRENT active zp_user_login session
    - user_id is taken from the authenticated token only

    Storage in master zp_users:
    - password2 = new password directly
    - password = MD5(new password)
    """
    try:
        auth_context = authenticate_active_device_user(
            request
        )

        result = change_user_password(
            user_id=int(
                auth_context.get("user_id") or 0
            ),
            old_password=payload.old_password,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        )

        return success_response(
            message="Password changed successfully",
            meta=_meta("authenticated"),
            data=result,
        )

    except MobileTokenError as exc:
        return _mobile_token_error_response(exc)
    except UserProfileServiceError as exc:
        return _profile_error_response(exc)
    except Exception as exc:
        return _unhandled_error(
            "Unable to change password",
            "USER_PASSWORD_CHANGE_FAILED",
            exc,
        )

