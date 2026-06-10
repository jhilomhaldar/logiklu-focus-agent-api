from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_handlers import (
    http_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.request_logger import api_request_logger_middleware
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="External Agentic AI Data API for LogiKlu Focus.",
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
        "message": "Welcome to LogiKlu Focus Agent API - Sandbox",
        "docs": "/docs",
        "health": f"/api/{settings.API_VERSION}/health",
    }
    