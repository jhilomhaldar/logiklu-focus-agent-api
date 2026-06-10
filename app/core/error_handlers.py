from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import (
    error_response,
    validation_error_response,
    not_found_response,
    server_error_response,
    current_utc_datetime,
)


async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail

    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=detail,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(detail),
            error_code=f"HTTP_{exc.status_code}",
            data={
                "path": str(request.url.path),
                "timestamp": current_utc_datetime(),
            },
        ),
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content=not_found_response(
                message="Endpoint not found",
                data={
                    "path": str(request.url.path),
                    "method": request.method,
                },
            ),
        )

    if exc.status_code == 405:
        return JSONResponse(
            status_code=405,
            content=error_response(
                message="Method not allowed",
                error_code="METHOD_NOT_ALLOWED",
                data={
                    "path": str(request.url.path),
                    "method": request.method,
                },
            ),
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
            data={
                "path": str(request.url.path),
                "method": request.method,
            },
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=validation_error_response(
            message="Invalid request parameters",
            errors=exc.errors(),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=server_error_response(
            message="Internal server error",
            data={
                "path": str(request.url.path),
                "method": request.method,
            },
        ),
    )