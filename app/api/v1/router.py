from fastapi import APIRouter

from app.api.v1.endpoints import health, auth_test, accounts, contacts

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