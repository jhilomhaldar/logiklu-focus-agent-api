from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.mobile_auth_security import (
    MobileTokenError,
    authenticate_mobile_user,
)
from app.core.response import (
    current_utc_datetime,
    error_response,
    success_response,
)
from app.core.security import get_api_environment, get_client_ip
from app.schemas.mobile_auth import (
    MobileLoginRequest,
    MobileWebSessionConsumeRequest,
    MobileWebSessionRequest,
)
from app.services.mobile_auth_service import (
    MobileAuthServiceError,
    authenticate_mobile_login,
    consume_web_session_handoff,
    create_web_session_handoff,
)


router = APIRouter()


def _service_error_response(exc: MobileAuthServiceError) -> JSONResponse:
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


def _mobile_token_error_response(exc: MobileTokenError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_response(
            message=str(exc),
            error_code="MOBILE_AUTH_TOKEN_INVALID",
            data={"timestamp": current_utc_datetime()},
        ),
    )


@router.post("/auth/login")
def mobile_login(payload: MobileLoginRequest, request: Request):
    try:
        result = authenticate_mobile_login(
            username=payload.username,
            password=payload.password,
            current_timezone=payload.current_timezone or "UTC",
            client_ip=get_client_ip(request),
        )

        return success_response(
            message="Login successful",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "public",
                "environment": get_api_environment(),
                "schema_version": "logiklu_mobile_auth.v1",
            },
            data=result,
        )

    except MobileAuthServiceError as exc:
        return _service_error_response(exc)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Login failed",
                error_code="MOBILE_AUTH_LOGIN_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.post("/auth/web-session")
def create_mobile_web_session(
    payload: MobileWebSessionRequest,
    request: Request,
):
    try:
        mobile_context = authenticate_mobile_user(request)

        result = create_web_session_handoff(
            user_id=int(mobile_context.get("user_id") or 0),
            token_login_point=int(mobile_context.get("login_point") or 0),
            domain_id=payload.domain_id,
            account_id=payload.account_id,
            current_timezone=payload.current_timezone or "UTC",
            check_os=payload.check_os or "",
            check_version=payload.check_version or "",
            client_ip=get_client_ip(request),
        )

        return success_response(
            message="Web session handoff created successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "mobile_user",
                "environment": get_api_environment(),
                "schema_version": "logiklu_mobile_web_session.v1",
            },
            data=result,
        )

    except MobileTokenError as exc:
        return _mobile_token_error_response(exc)
    except MobileAuthServiceError as exc:
        return _service_error_response(exc)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to create web session handoff",
                error_code="MOBILE_WEB_SESSION_CREATE_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )


@router.post("/auth/web-session/consume")
def consume_mobile_web_session(payload: MobileWebSessionConsumeRequest):
    try:
        result = consume_web_session_handoff(payload.token)

        return success_response(
            message="Web session handoff consumed successfully",
            meta={
                "generated_at": current_utc_datetime(),
                "mode": "handoff",
                "environment": get_api_environment(),
                "schema_version": "logiklu_mobile_web_session.v1",
            },
            data=result,
        )

    except MobileAuthServiceError as exc:
        return _service_error_response(exc)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Failed to consume web session handoff",
                error_code="MOBILE_WEB_SESSION_CONSUME_FAILED",
                data={
                    "error": str(exc),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )
