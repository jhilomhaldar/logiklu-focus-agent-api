from fastapi import APIRouter, Depends

from app.config import settings
from app.core.response import success_response, current_utc_datetime
from app.core.security import authenticate_request


router = APIRouter()

DEPLOY_CHECK_MARKER = "deploy-check-2026-07-23-v1"


@router.get("/deployment/check")
def get_deployment_check(
    auth_context: dict = Depends(authenticate_request),
):
    """
    Lightweight protected endpoint used only to verify that the latest
    Docker image was pulled and the container was recreated in each environment.
    """

    return success_response(
        message="Deployment check fetched successfully",
        meta={
            "generated_at": current_utc_datetime(),
        },
        data={
            "schema_version": "logiklu_deployment_check.v1",
            "deployment_check": {
                "marker": DEPLOY_CHECK_MARKER,
                "api_env": str(getattr(settings, "API_ENV", "production") or "production"),
                "app_env": str(getattr(settings, "APP_ENV", "") or ""),
                "app_name": str(getattr(settings, "APP_NAME", "LogiKlu API") or "LogiKlu API"),
                "client_database": auth_context.get("client_database"),
                "oauth_client_id": auth_context.get("oauth_client_id"),
                "focus_report_route_expected": True,
                "zero_limit_means_unlimited": True,
            },
        },
    )
