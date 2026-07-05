from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict


def _template_path() -> Path:
    return Path(__file__).resolve().parent / "client_apiusage_template.html"


def render_client_apiusage_page(report: Dict[str, Any]) -> str:
    template = _template_path().read_text(encoding="utf-8")
    envs_json = json.dumps(report.get("envs", {}), ensure_ascii=False)
    selected_env = report.get("selected_environment") or "sandbox"
    timezone_name = report.get("timezone") or "Asia/Calcutta"
    timezone_offset = report.get("timezone_offset_minutes")
    if timezone_offset is None:
        timezone_offset = 330
    return (
        template
        .replace("__USAGE_DATA__", envs_json)
        .replace("__SELECTED_ENV__", html.escape(str(selected_env)))
        .replace("__TIMEZONE__", html.escape(str(timezone_name)))
        .replace("__TIMEZONE_OFFSET__", html.escape(str(timezone_offset)))
    )


def render_client_apiusage_error_page(message: str) -> str:
    safe_message = html.escape(message or "Unable to load API usage report.")
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
<title>LogiKlu API Usage</title>
<style>
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#0B0E14;color:#E7E9EE;font-family:Arial,Helvetica,sans-serif;}}
.card{{width:min(520px,92vw);background:#121620;border:1px solid #242B3A;border-radius:14px;padding:28px;box-shadow:0 20px 60px rgba(0,0,0,.24);}}
.logo{{width:42px;height:42px;border-radius:10px;background:#5EEAD4;color:#06201C;display:grid;place-items:center;font-weight:900;margin-bottom:18px;}}
h1{{font-size:22px;margin:0 0 8px;}}
p{{color:#8890A0;line-height:1.55;margin:0 0 18px;}}
.small{{font-size:12px;color:#565D6D;}}
</style>
</head>
<body>
<div class=\"card\">
  <div class=\"logo\">LK</div>
  <h1>API usage report unavailable</h1>
  <p>{safe_message}</p>
  <div class=\"small\">Please check the OAuth client ID in the browser URL.</div>
</div>
</body>
</html>"""
