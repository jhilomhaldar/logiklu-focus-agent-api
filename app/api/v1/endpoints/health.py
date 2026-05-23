from fastapi import APIRouter
from app.config import settings
from app.core.response import success_response, current_utc_datetime

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