import base64
import copy
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.core.api_instruction_data import API_INSTRUCTION_DATA
from app.core.api_master_instruction_data import API_MASTER_INSTRUCTION_DATA
from app.core.api_instruction_renderer import render_instruction_page


router = APIRouter()


def get_master_usage_username() -> str:
    return str(getattr(settings, "MASTER_USAGE_USERNAME", "") or "").strip()


def get_master_usage_password() -> str:
    return str(getattr(settings, "MASTER_USAGE_PASSWORD", "") or "").strip()


def get_request_base_url(request: Request) -> str:
    """
    Build base URL from the actual browser/API request.

    This fixes:
    - sandboxapi.logiklu.com/usage showing api.logiklu.com
    - local usage showing production URL
    - production usage still showing production URL correctly
    """

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")

    scheme = (forwarded_proto or request.url.scheme or "https").split(",")[0].strip()
    host = (forwarded_host or request.headers.get("host") or "").split(",")[0].strip()

    if not host:
        return str(request.base_url).rstrip("/")

    return f"{scheme}://{host}".rstrip("/")


def prepare_usage_data_for_current_request(data: dict, request: Request) -> dict:
    """
    Use the same usage data, but force all rendered examples and Try Out URLs
    to use the current request domain.
    """

    current_base_url = get_request_base_url(request)

    prepared_data = copy.deepcopy(data)

    prepared_data["base_url"] = current_base_url
    prepared_data["sandbox_base_url"] = current_base_url
    prepared_data["local_base_url"] = current_base_url

    prepared_data["current_base_url"] = current_base_url

    return prepared_data


def unauthorized_master_usage_response(message: str = "Authentication required") -> HTMLResponse:
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Master Usage Authentication</title>
            <style>
                body {{
                    background: #0a0b0f;
                    color: #e8eaf0;
                    font-family: Arial, sans-serif;
                    padding: 40px;
                }}
                .box {{
                    max-width: 520px;
                    border: 1px solid #2a2f3d;
                    border-radius: 12px;
                    padding: 24px;
                    background: #111318;
                }}
                h1 {{
                    font-size: 22px;
                    margin-bottom: 10px;
                }}
                p {{
                    color: #9aa0b8;
                }}
                code {{
                    color: #00e5a0;
                }}
            </style>
        </head>
        <body>
            <div class="box">
                <h1>Master Usage Authentication Required</h1>
                <p>{message}</p>
                <p>Please refresh the page and enter the master usage username and password.</p>
            </div>
        </body>
        </html>
        """,
        status_code=401,
        headers={
            "WWW-Authenticate": 'Basic realm="LogiKlu Master Usage"'
        },
    )


def is_master_usage_authenticated(request: Request) -> bool:
    configured_username = get_master_usage_username()
    configured_password = get_master_usage_password()

    if not configured_username or not configured_password:
        return False

    authorization = request.headers.get("Authorization", "")

    if not authorization:
        return False

    if not authorization.lower().startswith("basic "):
        return False

    encoded_credentials = authorization.split(" ", 1)[1].strip()

    try:
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
    except Exception:
        return False

    if ":" not in decoded_credentials:
        return False

    username, password = decoded_credentials.split(":", 1)

    username_ok = secrets.compare_digest(username, configured_username)
    password_ok = secrets.compare_digest(password, configured_password)

    return username_ok and password_ok


@router.get("/instructions", response_class=HTMLResponse)
def api_usage_page(request: Request):
    usage_data = prepare_usage_data_for_current_request(
        data=API_INSTRUCTION_DATA,
        request=request,
    )

    return HTMLResponse(content=render_instruction_page(usage_data))


@router.get("/masterinstructions", response_class=HTMLResponse)
def api_master_usage_page(request: Request):
    if not is_master_usage_authenticated(request):
        return unauthorized_master_usage_response()

    master_usage_data = prepare_usage_data_for_current_request(
        data=API_MASTER_INSTRUCTION_DATA,
        request=request,
    )

    return HTMLResponse(content=render_instruction_page(master_usage_data))