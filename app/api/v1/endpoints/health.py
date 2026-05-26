from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.response import success_response, error_response, current_utc_datetime
from app.db.master import test_master_connection

from fastapi import Depends, Request
from app.core.security import authenticate_request
from app.db.client import test_client_connection

router = APIRouter()


@router.get("/health")
def health_check():
    return success_response(
        message="API is running",
        data={
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "api_version": settings.API_VERSION,
            "timestamp": current_utc_datetime(),
        },
    )


@router.get("/health/db")
def database_health_check():
    db_result = test_master_connection()

    if not db_result.get("connected"):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response(
                message="Master database connection failed",
                error_code="MASTER_DB_CONNECTION_FAILED",
                data={
                    "environment": settings.APP_ENV,
                    "database": settings.MASTER_DB_NAME,
                    "host": settings.MASTER_DB_HOST,
                    "error": db_result.get("error"),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    return success_response(
        message="Master database connection successful",
        data={
            "environment": settings.APP_ENV,
            "database": db_result.get("database_name"),
            "server_time": db_result.get("server_time"),
            "timestamp": current_utc_datetime(),
        },
    )

@router.get("/health/client-db")
def client_database_health_check(
    request: Request,
    auth_context: dict = Depends(authenticate_request),
):
    client_database = auth_context.get("client_database")

    db_result = test_client_connection(client_database)

    if not db_result.get("connected"):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response(
                message="Client database connection failed",
                error_code="CLIENT_DB_CONNECTION_FAILED",
                data={
                    "client_database": client_database,
                    "error": db_result.get("error"),
                    "timestamp": current_utc_datetime(),
                },
            ),
        )

    return success_response(
        message="Client database connection successful",
        data={
            "client_database": db_result.get("database_name"),
            "server_time": db_result.get("server_time"),
            "timestamp": current_utc_datetime(),
        },
    )