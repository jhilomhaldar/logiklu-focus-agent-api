from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.request_logger import api_request_logger_middleware


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="External Agentic AI Data API for LogiKlu Focus.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ALLOWED_ORIGINS == "*" else settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(api_request_logger_middleware)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "status": "success",
        "message": "Welcome to LogiKlu Focus Agent API",
        "docs": "/docs",
        "health": f"/api/{settings.API_VERSION}/health",
    }