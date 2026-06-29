from fastapi import APIRouter

from app.api.v1.endpoints import health, auth_test, accounts, contacts, usage, focus_company_intelligence, focus_accounts


api_router = APIRouter()

api_router.include_router(
    health.router,
    tags=["Health"]
)

api_router.include_router(
    auth_test.router,
    tags=["Authentication"]
)

api_router.include_router(
    accounts.router,
    tags=["Accounts"]
)

api_router.include_router(
    contacts.router,
    tags=["Contacts"]
)

api_router.include_router(
    usage.router,
    tags=["Usage"]
)

api_router.include_router(
    focus_company_intelligence.router,
    tags=["Focus Intelligence"]
)

api_router.include_router(
    focus_accounts.router,
    tags=["Focus Accounts"]
)