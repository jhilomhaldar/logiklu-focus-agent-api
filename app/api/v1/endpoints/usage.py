from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.api_usage_data import API_USAGE_DATA
from app.core.api_usage_renderer import render_usage_page

router = APIRouter()


@router.get("/usage", response_class=HTMLResponse)
def api_usage_page():
    return HTMLResponse(content=render_usage_page(API_USAGE_DATA))