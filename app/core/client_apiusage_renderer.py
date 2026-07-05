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


def render_client_apiusage_login_page(oauth_client_id: str, message: str = "", client_name: str = "", login_id: str = "") -> str:
    safe_oauth = html.escape(str(oauth_client_id or ""), quote=True)
    safe_message = html.escape(message or "")
    safe_client_name = html.escape(client_name or "LogiKlu API Usage")
    safe_login_id = html.escape(login_id or "", quote=True)
    error_html = f'<div class="error-box">{safe_message}</div>' if safe_message else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>LogiKlu API Usage Login</title>
<style>
:root{{--bg:#0B0E14;--surface:#121620;--surface2:#1A1F2B;--border:#242B3A;--text:#E7E9EE;--dim:#8890A0;--faint:#565D6D;--accent:#5EEAD4;--error:#F4415F;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at top right,rgba(94,234,212,.10),transparent 30%),var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;padding:24px;}}
.card{{width:min(460px,94vw);background:linear-gradient(180deg,rgba(18,22,32,.98),rgba(18,22,32,.90));border:1px solid var(--border);border-radius:18px;padding:30px;box-shadow:0 24px 70px rgba(0,0,0,.32);}}
.logo{{width:178px;height:auto;display:block;margin:0 0 26px;}}
h1{{font-size:24px;margin-bottom:7px;}}
p{{color:var(--dim);font-size:13px;line-height:1.55;margin-bottom:20px;}}
.client{{border:1px solid var(--border);background:var(--surface2);border-radius:12px;padding:12px 14px;margin-bottom:18px;}}
.client small{{display:block;color:var(--faint);font-size:10px;text-transform:uppercase;letter-spacing:.8px;font-weight:800;margin-bottom:4px;}}
.client code{{color:var(--accent);font-family:Consolas,Monaco,'Courier New',monospace;font-size:12px;word-break:break-all;}}
label{{display:block;color:var(--dim);font-size:12px;font-weight:800;margin:14px 0 7px;}}
input{{width:100%;border:1px solid var(--border);background:var(--surface2);color:var(--text);border-radius:10px;padding:12px 13px;font-size:14px;outline:none;}}
input:focus{{border-color:rgba(94,234,212,.45);box-shadow:0 0 0 3px rgba(94,234,212,.08);}}
.password-wrap{{position:relative;}}
.password-wrap input{{padding-right:78px;}}
.password-toggle{{position:absolute;right:8px;top:50%;transform:translateY(-50%);width:auto;margin:0;border:1px solid var(--border);background:#222836;color:var(--accent);border-radius:8px;padding:7px 10px;font-size:11px;font-weight:900;}}
.password-toggle:hover{{background:#2A3142;}}
button{{width:100%;border:none;background:var(--accent);color:#06201C;border-radius:10px;padding:12px 14px;font-size:14px;font-weight:900;margin-top:18px;cursor:pointer;}}
.error-box{{border:1px solid rgba(244,65,95,.32);background:rgba(244,65,95,.12);color:#ff8fa1;border-radius:10px;padding:11px 12px;font-size:13px;line-height:1.45;margin-bottom:14px;}}
.note{{color:var(--faint);font-size:11.5px;margin-top:15px;line-height:1.45;}}
</style>
</head>
<body>
  <div class="card">
    <img class="logo" src="/static/images/logiklu-logo.png" alt="LogiKlu" />
    <h1>API Usage Login</h1>
    <p>Sign in with your LogiKlu user account to view this client API usage report.</p>
    <div class="client"><small>Client Access Key</small><code>{safe_oauth}</code></div>
    {error_html}
    <form method="post" action="/client/apiusage/{safe_oauth}/login" autocomplete="off">
      <label>Email or username</label>
      <input type="text" name="login_id" value="{safe_login_id}" required autofocus />
      <label>Password</label>
      <div class="password-wrap">
        <input type="password" name="password" id="usagePasswordInput" required />
        <button class="password-toggle" type="button" id="usagePasswordToggle" aria-label="Show password">Show</button>
      </div>
      <button type="submit">Login and View Report</button>
    </form>
    <div class="note">Only users assigned as Administrator or Moderator for this client can view the report. The session remains active only for the current browser session.</div>
  </div>
<script>
(function(){{
  var input = document.getElementById('usagePasswordInput');
  var btn = document.getElementById('usagePasswordToggle');
  if(input && btn){{
    btn.addEventListener('click', function(){{
      var isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');
      btn.textContent = isPassword ? 'Hide' : 'Show';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      input.focus();
    }});
  }}
}})();
</script>
</body>
</html>"""


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
<script>
(function(){{
  var input = document.getElementById('usagePasswordInput');
  var btn = document.getElementById('usagePasswordToggle');
  if(input && btn){{
    btn.addEventListener('click', function(){{
      var isPassword = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPassword ? 'text' : 'password');
      btn.textContent = isPassword ? 'Hide' : 'Show';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      input.focus();
    }});
  }}
}})();
</script>
</body>
</html>"""
