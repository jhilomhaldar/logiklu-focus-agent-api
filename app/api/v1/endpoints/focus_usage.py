# app/api/v1/endpoints/focus_usage.py

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/focus/usage", response_class=HTMLResponse)
@router.get("/api/focus/usage", response_class=HTMLResponse)
def focus_usage_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LogiKlu Focus API Usage</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f8fafc;
                color: #1f2937;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1100px;
                margin: 0 auto;
                padding: 40px 24px;
            }
            .header {
                background: #111827;
                color: #ffffff;
                padding: 28px 32px;
                border-radius: 12px;
                margin-bottom: 28px;
            }
            .header h1 {
                margin: 0 0 8px 0;
                font-size: 30px;
            }
            .header p {
                margin: 0;
                color: #d1d5db;
                font-size: 15px;
            }
            .card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }
            h2 {
                margin-top: 0;
                color: #111827;
                font-size: 22px;
            }
            h3 {
                color: #111827;
                margin-bottom: 8px;
            }
            code {
                background: #f3f4f6;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 14px;
            }
            pre {
                background: #0f172a;
                color: #e5e7eb;
                padding: 16px;
                border-radius: 8px;
                overflow-x: auto;
                font-size: 14px;
                line-height: 1.5;
            }
            .method {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 8px;
            }
            .get {
                background: #dcfce7;
                color: #166534;
            }
            .post {
                background: #dbeafe;
                color: #1d4ed8;
            }
            .note {
                background: #fffbeb;
                border-left: 4px solid #f59e0b;
                padding: 14px 16px;
                border-radius: 6px;
                margin-top: 12px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
            }
            th, td {
                border: 1px solid #e5e7eb;
                padding: 10px;
                text-align: left;
                vertical-align: top;
            }
            th {
                background: #f9fafb;
            }
            .footer {
                color: #6b7280;
                font-size: 13px;
                text-align: center;
                margin-top: 32px;
            }
        </style>
    </head>
    <body>
        <div class="container">

            <div class="header">
                <h1>LogiKlu Focus API Usage</h1>
                <p>Focus-only API documentation for Cognitive AI integration.</p>
            </div>

            <div class="card">
                <h2>1. Overview</h2>
                <p>
                    This document contains only the LogiKlu Focus APIs required for the
                    Cognitive AI integration. The parent LogiKlu API usage page is separate.
                </p>
                <p>
                    LogiKlu Focus provides deterministic company intelligence, reporting window,
                    scores, score explanations, signal summary, journey detail, and attribution data.
                </p>
            </div>

            <div class="card">
                <h2>2. Authentication</h2>
                <p>
                    Focus API will use Bearer JWT authentication for protected API calls.
                    Cognitive AI will first request an access token, then call Focus APIs using
                    the token.
                </p>

                <h3><span class="method post">POST</span>/oauth/token</h3>

                <p>Request body:</p>
                <pre>{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "grant_type": "client_credentials"
}</pre>

                <p>Response:</p>
                <pre>{
  "access_token": "jwt_token_here",
  "token_type": "Bearer",
  "expires_in": 900,
  "scope": "focus:company-intelligence:read"
}</pre>

                <p>Protected API header:</p>
                <pre>Authorization: Bearer &lt;access_token&gt;</pre>

                <div class="note">
                    Current development environments may still support existing API-key based authentication
                    for older endpoints. New Cognitive AI Focus endpoints will use Bearer JWT.
                </div>
            </div>

            <div class="card">
                <h2>3. Company Intelligence — List</h2>

                <h3><span class="method get">GET</span>/api/focus/company-intelligence</h3>

                <p>
                    Returns a paginated list of Focus companies with intelligence data.
                    Journey detail is included by default unless explicitly disabled.
                </p>

                <h3>Query Parameters</h3>
                <table>
                    <tr>
                        <th>Parameter</th>
                        <th>Required</th>
                        <th>Description</th>
                    </tr>
                    <tr>
                        <td><code>page</code></td>
                        <td>No</td>
                        <td>Page number. Default: 1.</td>
                    </tr>
                    <tr>
                        <td><code>per_page</code></td>
                        <td>No</td>
                        <td>Records per page. Minimum: 10. Default: 10.</td>
                    </tr>
                    <tr>
                        <td><code>search</code></td>
                        <td>No</td>
                        <td>Search by company name, website, industry, city, state, or country.</td>
                    </tr>
                    <tr>
                        <td><code>interest_level</code></td>
                        <td>No</td>
                        <td>Filter by interest level: low, medium, high, high_flame.</td>
                    </tr>
                    <tr>
                        <td><code>priority_label</code></td>
                        <td>No</td>
                        <td>Filter by priority label.</td>
                    </tr>
                    <tr>
                        <td><code>is_shortlisted</code></td>
                        <td>No</td>
                        <td>Filter by Y or N.</td>
                    </tr>
                    <tr>
                        <td><code>include_journey</code></td>
                        <td>No</td>
                        <td>Default: true. Pass false only for a lighter response.</td>
                    </tr>
                </table>

                <h3>Example</h3>
                <pre>GET /api/focus/company-intelligence?page=1&amp;per_page=10
Authorization: Bearer &lt;access_token&gt;</pre>

                <h3>Demo URL</h3>
                <pre>GET /demo/{client_database}/api/focus/company-intelligence?page=1&amp;per_page=10</pre>
            </div>

            <div class="card">
                <h2>4. Company Intelligence — Get One</h2>

                <h3><span class="method get">GET</span>/api/focus/company-intelligence/{account_id}</h3>

                <p>
                    Returns the canonical Focus company intelligence object for one account.
                </p>

                <h3>Example</h3>
                <pre>GET /api/focus/company-intelligence/1094
Authorization: Bearer &lt;access_token&gt;</pre>

                <h3>Demo URL</h3>
                <pre>GET /demo/{client_database}/api/focus/company-intelligence/1094</pre>

                <h3>Response Shape</h3>
                <pre>{
  "schema_version": "focus_company_intelligence.v1",
  "account": {
    "account_id": "1094",
    "company_id": "1094",
    "company_name": "LogiKlu",
    "company_domain": "logiklu.com",
    "account_status": "suspect",
    "lead_type": "cold",
    "is_identified_company": true,
    "location": {
      "country": "United States",
      "state": "West Virginia",
      "city": "Jacksonburg"
    },
    "industry": ""
  },
  "reporting_window": {
    "report_id": 1,
    "from_date": "2026-05-31",
    "to_date": "2026-06-29",
    "window_days": 30,
    "timezone": "Asia/Kolkata"
  },
  "deterministic_scores": {
    "score_components": {
      "activity": 18,
      "sustenance": 18,
      "depth": 38,
      "contextual": 16,
      "conversion": 45,
      "priority": 61
    },
    "interest_score": 74,
    "interest_level": "high",
    "priority_label": "Hot Account",
    "engagement_level": "Very High",
    "final_score": 135,
    "computed_at": "2026-06-29 07:17:15"
  },
  "score_explanation": [],
  "signal_summary": {
    "session_count": 5,
    "page_view_count": 29,
    "unique_page_count": 11,
    "total_action_count": 20,
    "asset_download_count": 7,
    "external_link_click_count": 7,
    "lead_form_submission_count": 4,
    "inner_form_submission_count": 2,
    "form_submission_count": 6,
    "video_view_count": 0,
    "first_activity_at": "2026-06-08 14:01:30",
    "last_activity_at": "2026-06-29 08:06:28"
  },
  "top_evidence_facts": [],
  "journey_detail": {},
  "campaign_contact_attribution": {}
}</pre>
            </div>

            <div class="card">
                <h2>5. Deferred / Not Yet Included</h2>
                <p>
                    The following Focus APIs are part of future discussion and are not included
                    in the current client-ready Focus API scope:
                </p>
                <ul>
                    <li><code>GET /api/focus/contacts</code></li>
                    <li><code>GET /api/focus/users</code></li>
                    <li><code>GET /api/focus/roles</code></li>
                    <li><code>POST /api/focus/campaign-execution-requests</code></li>
                    <li><code>GET /api/focus/campaign-execution-requests/{request_id}/status</code></li>
                    <li>Webhook endpoints</li>
                </ul>
            </div>

            <div class="footer">
                LogiKlu Focus API Usage — Focus-only documentation
            </div>

        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)