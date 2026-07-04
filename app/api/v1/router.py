from fastapi import APIRouter

from app.api.v1.endpoints import health, auth_test, accounts, contacts, oauth, usage, focus_company_intelligence, focus_accounts, focus_account_intelligence, focus_contacts, leadforms, campaigns


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
    oauth.router,
    tags=["OAuth"]
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

api_router.include_router(
    focus_account_intelligence.router,
    tags=["Focus Account Intelligence"]
)

api_router.include_router(
    focus_contacts.router,
    tags=["Focus Contacts"]
)

api_router.include_router(
    leadforms.router,
    tags=["Leadforms"]
)

api_router.include_router(
    campaigns.router,
    tags=["Emaikl Campaigns"]
)



