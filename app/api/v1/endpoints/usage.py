from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/usage", response_class=HTMLResponse)
def api_usage_page():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>LogiKlu Agent API Usage Guide</title>
        <style>
            body {
                font-family: Arial, Helvetica, sans-serif;
                background: #f5f7fb;
                color: #222;
                margin: 0;
                padding: 0;
                line-height: 1.6;
            }

            .container {
                max-width: 1180px;
                margin: 0 auto;
                padding: 30px 20px 60px;
            }

            .header {
                background: #0b5fa5;
                color: #fff;
                padding: 28px 34px;
                border-radius: 14px;
                margin-bottom: 24px;
                box-shadow: 0 6px 18px rgba(0,0,0,0.12);
            }

            .header h1 {
                margin: 0 0 8px;
                font-size: 28px;
            }

            .header p {
                margin: 0;
                opacity: 0.95;
            }

            .card {
                background: #fff;
                border-radius: 14px;
                padding: 24px 28px;
                margin-bottom: 22px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
                border: 1px solid #e5e9f0;
            }

            h2 {
                margin-top: 0;
                color: #0b5fa5;
                font-size: 22px;
                border-bottom: 1px solid #e5e9f0;
                padding-bottom: 8px;
            }

            h3 {
                color: #333;
                margin-bottom: 8px;
                font-size: 18px;
            }

            code {
                background: #eef3f8;
                padding: 2px 6px;
                border-radius: 5px;
                color: #0b5fa5;
                font-family: Consolas, Monaco, monospace;
            }

            pre {
                background: #1f2937;
                color: #f9fafb;
                padding: 18px;
                border-radius: 10px;
                overflow-x: auto;
                font-size: 14px;
                line-height: 1.5;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
            }

            th {
                background: #0b5fa5;
                color: #fff;
                text-align: left;
                padding: 10px;
                font-size: 14px;
            }

            td {
                border: 1px solid #dce3ec;
                padding: 10px;
                vertical-align: top;
                font-size: 14px;
            }

            tr:nth-child(even) {
                background: #f8fafc;
            }

            .method {
                display: inline-block;
                background: #198754;
                color: #fff;
                padding: 3px 8px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                margin-right: 8px;
            }

            .note {
                background: #fff7e6;
                border-left: 5px solid #ffb020;
                padding: 12px 16px;
                border-radius: 8px;
                margin: 12px 0;
            }

            .endpoint {
                font-size: 16px;
                font-weight: bold;
                color: #111827;
            }

            .footer {
                color: #667085;
                text-align: center;
                margin-top: 35px;
                font-size: 13px;
            }
        </style>
    </head>

    <body>
        <div class="container">
            <div class="header">
                <h1>LogiKlu Agent API Usage Guide</h1>
                <p>Client-facing API documentation for account, contact, and engagement data access.</p>
            </div>

            <div class="card">
                <h2>Base URL</h2>
                <p>Production API base URL:</p>
                <pre>https://api.logiklu.com/api/v1</pre>
            </div>

            <div class="card">
                <h2>Authentication</h2>
                <p>All protected endpoints require an API key in the request header.</p>

                <table>
                    <thead>
                        <tr>
                            <th>Header</th>
                            <th>Required</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>X-API-KEY</code></td>
                            <td>Yes</td>
                            <td>API key issued for the client account.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Example</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <div class="note">
                    HMAC signature authentication can be enabled later using <code>X-TIMESTAMP</code> and <code>X-SIGNATURE</code>.
                </div>
            </div>

            <div class="card">
                <h2>Health APIs</h2>

                <p class="endpoint"><span class="method">GET</span>/health</p>
                <p>Checks whether the API service is running.</p>
                <pre>https://api.logiklu.com/api/v1/health</pre>

                <p class="endpoint"><span class="method">GET</span>/health/db</p>
                <p>Checks whether the API can connect to the master database.</p>
                <pre>https://api.logiklu.com/api/v1/health/db</pre>

                <p class="endpoint"><span class="method">GET</span>/health/client-db</p>
                <p>Checks whether the API can connect to the authenticated client database.</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/health/client-db" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>
            </div>

                            <div class="card">
                <h2>Accounts API</h2>

                <p class="endpoint"><span class="method">GET</span>/accounts</p>
                <p>
                    Fetches account/company records from LogiKlu CRM. This API supports general search,
                    specific field search, computed lead category filtering, publish-status filtering,
                    dynamic filters, pagination, contacts, and dynamic account fields.
                </p>

                <h3>Authentication</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Basic Query Parameters</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Allowed / Example</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>limit</code></td>
                            <td><code>20</code></td>
                            <td>Number of records to return. Maximum allowed value is <code>100</code>.</td>
                        </tr>
                        <tr>
                            <td><code>offset</code></td>
                            <td><code>0</code></td>
                            <td>Pagination offset.</td>
                        </tr>
                        <tr>
                            <td><code>search</code></td>
                            <td><code>Hamamatsu</code></td>
                            <td>Search value. Works as general search if <code>search_by</code> is not provided.</td>
                        </tr>
                        <tr>
                            <td><code>search_by</code></td>
                            <td><code>lead_name</code></td>
                            <td>Specific field search. When provided, <code>search</code> will apply only to that selected field.</td>
                        </tr>
                        <tr>
                            <td><code>lead_publish_status</code></td>
                            <td><code>active</code>, <code>archive</code>, <code>all</code></td>
                            <td>
                                Controls account publish/archive status.
                                <code>active</code> returns active accounts,
                                <code>archive</code> returns archived accounts,
                                <code>all</code> removes active/archive restriction.
                            </td>
                        </tr>
                        <tr>
                            <td><code>computed_lead_category</code></td>
                            <td><code>all</code>, <code>lead</code>, <code>potential_lead</code>, <code>customer</code></td>
                            <td>
                                Computed lead category based on account category and active contact count.
                                <code>lead</code> means raw category is lead and account has active contacts.
                                <code>potential_lead</code> means suspect, or lead without active contacts.
                            </td>
                        </tr>
                        <tr>
                            <td><code>filters</code></td>
                            <td><code>[{"field":"country","operator":"eq","value":"Japan"}]</code></td>
                            <td>Advanced multi-condition filters in JSON format.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>General Search</h3>
                <p>
                    If <code>search_by</code> is not passed, the API searches across multiple common account fields.
                </p>

                <p>General search checks:</p>
                <table>
                    <tbody>
                        <tr><td><code>lead_name</code></td><td>Account name</td></tr>
                        <tr><td><code>website</code></td><td>Website/domain</td></tr>
                        <tr><td><code>email</code></td><td>Account email</td></tr>
                        <tr><td><code>phone</code></td><td>Account phone</td></tr>
                        <tr><td><code>industry</code></td><td>Industry</td></tr>
                        <tr><td><code>city</code></td><td>City</td></tr>
                        <tr><td><code>state</code></td><td>State</td></tr>
                        <tr><td><code>country</code></td><td>Country</td></tr>
                        <tr><td><code>lead_source</code></td><td>Lead source</td></tr>
                    </tbody>
                </table>

                <h4>Example: General Search</h4>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=Japan&limit=20&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Specific Search Using search_by</h3>
                <p>
                    Use <code>search</code> with <code>search_by</code> when the client wants to search one specific account field.
                </p>

                <table>
                    <thead>
                        <tr>
                            <th>search_by</th>
                            <th>Example search value</th>
                            <th>Description / Mapping</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>lead_name</code></td>
                            <td><code>Hamamatsu</code></td>
                            <td>Searches account name using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>lead_segment</code></td>
                            <td><code>Company</code> / <code>Contact</code></td>
                            <td>
                                <code>Company</code> maps to <code>company</code>.
                                <code>Contact</code> maps to <code>contact</code>.
                            </td>
                        </tr>
                        <tr>
                            <td><code>lead_category</code></td>
                            <td><code>Potential Lead</code> / <code>Lead</code> / <code>Customer</code></td>
                            <td>
                                <code>Potential Lead</code> maps to raw <code>suspect</code>.
                                <code>Lead</code> maps to raw <code>lead</code>.
                                For computed category logic, use <code>computed_lead_category</code>.
                            </td>
                        </tr>
                        <tr>
                            <td><code>lead_type</code></td>
                            <td><code>hot,warm,cold</code></td>
                            <td>Searches account type. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>lead_persuing_status</code></td>
                            <td><code>1,2,3</code></td>
                            <td>Searches by lead pursuing/status IDs. Multiple IDs are supported.</td>
                        </tr>
                        <tr>
                            <td><code>website</code></td>
                            <td><code>logiklu.com</code></td>
                            <td>Searches website/domain using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>email</code></td>
                            <td><code>sales@</code></td>
                            <td>Searches account email using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>phone</code></td>
                            <td><code>9876</code></td>
                            <td>Searches phone field using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>industry</code></td>
                            <td><code>Software</code></td>
                            <td>Searches industry using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>city</code></td>
                            <td><code>Tokyo</code></td>
                            <td>Searches city using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>state</code></td>
                            <td><code>Aichi</code></td>
                            <td>Searches state using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>country</code></td>
                            <td><code>India,Japan</code></td>
                            <td>Searches country. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>zipcode</code></td>
                            <td><code>700001</code></td>
                            <td>Searches zipcode using partial match.</td>
                        </tr>
                        <tr>
                            <td><code>employee_count</code></td>
                            <td><code>100</code></td>
                            <td>Searches employee lower/upper range fields.</td>
                        </tr>
                        <tr>
                            <td><code>owner</code></td>
                            <td><code>4,8,12</code></td>
                            <td>Searches owner user IDs. Multiple IDs are supported.</td>
                        </tr>
                        <tr>
                            <td><code>created_by</code></td>
                            <td><code>4,8</code></td>
                            <td>Searches created-by user IDs. Multiple IDs are supported.</td>
                        </tr>
                        <tr>
                            <td><code>source</code></td>
                            <td><code>website,manual,csv</code></td>
                            <td>Searches source enum. Multiple values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>lead_source</code></td>
                            <td><code>LinkedIn,Event</code></td>
                            <td>Searches lead source. Multiple values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>assigned_to</code></td>
                            <td><code>4,8,12</code></td>
                            <td>
                                Searches assigned user IDs using <code>lk_lead_assign</code>.
                                Multiple user IDs are supported.
                            </td>
                        </tr>
                    </tbody>
                </table>

                <h3>Specific Search Examples</h3>

                <p>Search by account name:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=Hamamatsu&search_by=lead_name&limit=20&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by lead segment:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=Company&search_by=lead_segment" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by raw lead category:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=Lead&search_by=lead_category" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search multiple lead types:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=hot,warm,cold&search_by=lead_type" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search multiple lead status IDs:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=1,2,3&search_by=lead_persuing_status" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by country:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=India,Japan&search_by=country" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by owner IDs:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=4,8,12&search_by=owner" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by assigned user IDs:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?search=4,8,12&search_by=assigned_to" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Computed Lead Category</h3>
                <p>
                    Computed lead category is different from raw <code>lead_category</code>.
                    It uses account category and active contact count.
                </p>

                <table>
                    <thead>
                        <tr>
                            <th>computed_lead_category</th>
                            <th>Logic</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>lead</code></td>
                            <td>Raw <code>lead_category = lead</code> and account has more than 0 active contacts.</td>
                        </tr>
                        <tr>
                            <td><code>potential_lead</code></td>
                            <td>Raw <code>lead_category = suspect</code>, or raw <code>lead</code> with 0 active contacts.</td>
                        </tr>
                        <tr>
                            <td><code>customer</code></td>
                            <td>Raw <code>lead_category = customer</code>.</td>
                        </tr>
                        <tr>
                            <td><code>all</code></td>
                            <td>No computed category filter.</td>
                        </tr>
                    </tbody>
                </table>

                <p>Only computed Lead accounts:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?computed_lead_category=lead&limit=20&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Only Potential Lead accounts:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?computed_lead_category=potential_lead&limit=20&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Publish Status Examples</h3>

                <p>Only active accounts:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?lead_publish_status=active" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Only archived accounts:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?lead_publish_status=archive" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>All accounts, active and archived:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?lead_publish_status=all" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Advanced Dynamic Filters</h3>
                <p>
                    The <code>filters</code> parameter accepts a JSON array.
                    Use it when multiple field-specific conditions are needed.
                </p>

                <table>
                    <thead>
                        <tr>
                            <th>Operator</th>
                            <th>Meaning</th>
                            <th>Example</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>eq</code></td>
                            <td>Exact match</td>
                            <td><code>{"field":"country","operator":"eq","value":"Japan"}</code></td>
                        </tr>
                        <tr>
                            <td><code>neq</code></td>
                            <td>Not equal</td>
                            <td><code>{"field":"source","operator":"neq","value":"csv"}</code></td>
                        </tr>
                        <tr>
                            <td><code>like</code></td>
                            <td>Contains</td>
                            <td><code>{"field":"lead_name","operator":"like","value":"Photonics"}</code></td>
                        </tr>
                        <tr>
                            <td><code>starts_with</code></td>
                            <td>Starts with</td>
                            <td><code>{"field":"lead_name","operator":"starts_with","value":"Ham"}</code></td>
                        </tr>
                        <tr>
                            <td><code>ends_with</code></td>
                            <td>Ends with</td>
                            <td><code>{"field":"website","operator":"ends_with","value":".com"}</code></td>
                        </tr>
                        <tr>
                            <td><code>in</code></td>
                            <td>Multiple values</td>
                            <td><code>{"field":"country","operator":"in","value":["India","Japan"]}</code></td>
                        </tr>
                        <tr>
                            <td><code>from</code></td>
                            <td>Greater than or equal</td>
                            <td><code>{"field":"created_date","operator":"from","value":"2026-01-01"}</code></td>
                        </tr>
                        <tr>
                            <td><code>to</code></td>
                            <td>Less than or equal</td>
                            <td><code>{"field":"created_date","operator":"to","value":"2026-05-31"}</code></td>
                        </tr>
                    </tbody>
                </table>

                <p>Filter by country:</p>
                <pre>curl -X GET 'https://api.logiklu.com/api/v1/accounts?filters=[{"field":"country","operator":"eq","value":"Japan"}]' \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Filter by multiple conditions:</p>
                <pre>curl -X GET 'https://api.logiklu.com/api/v1/accounts?filters=[{"field":"country","operator":"eq","value":"Japan"},{"field":"source","operator":"in","value":["website","manual"]}]' \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Combined Examples</h3>

                <p>Computed Lead accounts from Japan:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?computed_lead_category=lead&search=Japan&search_by=country&limit=20&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Active accounts assigned to selected users:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?lead_publish_status=active&search=4,8&search_by=assigned_to" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Potential leads with selected source:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts?computed_lead_category=potential_lead&search=website,manual&search_by=source" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>
            </div>

            <div class="card">
                <h2>Account Detail API</h2>

                <p class="endpoint"><span class="method">GET</span>/accounts/{account_id}</p>
                <p>Fetches one account with dynamic fields and contacts.</p>

                <h3>Example</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/accounts/9626" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>
            </div>

                        <div class="card">
                <h2>Contacts API</h2>

                <p class="endpoint"><span class="method">GET</span>/contacts</p>
                <p>
                    Fetches standalone contacts from LogiKlu CRM. This API supports general contact search,
                    specific field search using <code>search_by</code>, account-based search, owner/created-by
                    filtering, associated-account filtering, pagination, dynamic contact fields, and full
                    linked account summary.
                </p>

                <h3>Authentication</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Basic Query Parameters</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Allowed / Example</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>limit</code></td>
                            <td><code>50</code></td>
                            <td>Number of records to return. Maximum allowed value is <code>100</code>.</td>
                        </tr>
                        <tr>
                            <td><code>offset</code></td>
                            <td><code>0</code></td>
                            <td>Pagination offset.</td>
                        </tr>
                        <tr>
                            <td><code>search</code></td>
                            <td><code>manager</code></td>
                            <td>Search value. Works as general search if <code>search_by</code> is not provided.</td>
                        </tr>
                        <tr>
                            <td><code>search_by</code></td>
                            <td><code>designation</code></td>
                            <td>Specific contact field to search.</td>
                        </tr>
                        <tr>
                            <td><code>account_id</code></td>
                            <td><code>1094</code></td>
                            <td>Fetch contacts linked with a specific account ID.</td>
                        </tr>
                        <tr>
                            <td><code>account_search</code></td>
                            <td><code>LogiKlu</code></td>
                            <td>Search contacts by account ID, account name, or account website.</td>
                        </tr>
                        <tr>
                            <td><code>associated_accounts_only</code></td>
                            <td><code>true</code> / <code>false</code></td>
                            <td>When true, only returns contacts that are linked to an account.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>General Contact Search</h3>
                <p>
                    If <code>search_by</code> is not provided, the API searches across common contact fields.
                </p>

                <table>
                    <tbody>
                        <tr><td><code>name</code></td><td>First name, last name, and full name.</td></tr>
                        <tr><td><code>email</code></td><td>Contact email.</td></tr>
                        <tr><td><code>phone</code></td><td>Primary phone.</td></tr>
                        <tr><td><code>whatsapp</code></td><td>WhatsApp number.</td></tr>
                        <tr><td><code>alternative_phone</code></td><td>Alternative phone.</td></tr>
                        <tr><td><code>alternative_emails</code></td><td>Alternative emails.</td></tr>
                        <tr><td><code>address</code></td><td>Address.</td></tr>
                        <tr><td><code>city</code></td><td>City.</td></tr>
                        <tr><td><code>state</code></td><td>State.</td></tr>
                        <tr><td><code>country</code></td><td>Country.</td></tr>
                        <tr><td><code>zipcode</code></td><td>Zipcode.</td></tr>
                        <tr><td><code>department</code></td><td>Department.</td></tr>
                        <tr><td><code>designation</code></td><td>Designation / job title.</td></tr>
                        <tr><td><code>contact_type</code></td><td>Contact type.</td></tr>
                        <tr><td><code>source</code></td><td>Contact source.</td></tr>
                    </tbody>
                </table>

                <h4>Example: General Search</h4>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=manager&limit=50&offset=0" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Specific Search Using search_by</h3>
                <p>
                    Use <code>search</code> with <code>search_by</code> when the client wants to search a specific
                    contact field.
                </p>

                <table>
                    <thead>
                        <tr>
                            <th>search_by</th>
                            <th>Example search value</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>name</code></td>
                            <td><code>John</code></td>
                            <td>Searches first name, last name, and full name.</td>
                        </tr>
                        <tr>
                            <td><code>first_name</code></td>
                            <td><code>John</code></td>
                            <td>Searches first name.</td>
                        </tr>
                        <tr>
                            <td><code>last_name</code></td>
                            <td><code>Smith</code></td>
                            <td>Searches last name.</td>
                        </tr>
                        <tr>
                            <td><code>email</code></td>
                            <td><code>gmail.com</code></td>
                            <td>Searches contact email.</td>
                        </tr>
                        <tr>
                            <td><code>phone</code></td>
                            <td><code>9876</code></td>
                            <td>Searches primary phone.</td>
                        </tr>
                        <tr>
                            <td><code>whatsapp</code></td>
                            <td><code>9876</code></td>
                            <td>Searches WhatsApp number.</td>
                        </tr>
                        <tr>
                            <td><code>alternative_phone</code></td>
                            <td><code>9876</code></td>
                            <td>Searches alternative phone.</td>
                        </tr>
                        <tr>
                            <td><code>alternative_emails</code></td>
                            <td><code>sales@</code></td>
                            <td>Searches alternative emails.</td>
                        </tr>
                        <tr>
                            <td><code>address</code></td>
                            <td><code>Park Street</code></td>
                            <td>Searches address.</td>
                        </tr>
                        <tr>
                            <td><code>city</code></td>
                            <td><code>Kolkata</code></td>
                            <td>Searches city. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>state</code></td>
                            <td><code>West Bengal</code></td>
                            <td>Searches state. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>country</code></td>
                            <td><code>India,Japan</code></td>
                            <td>Searches country. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>zipcode</code></td>
                            <td><code>700001</code></td>
                            <td>Searches zipcode.</td>
                        </tr>
                        <tr>
                            <td><code>department</code></td>
                            <td><code>Marketing</code></td>
                            <td>Searches department.</td>
                        </tr>
                        <tr>
                            <td><code>designation</code></td>
                            <td><code>Manager</code></td>
                            <td>Searches designation / job title.</td>
                        </tr>
                        <tr>
                            <td><code>contact_type</code></td>
                            <td><code>contact,guest</code></td>
                            <td>Searches contact type. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>source</code></td>
                            <td><code>website,manual,csv</code></td>
                            <td>Searches contact source. Multiple comma-separated values are supported.</td>
                        </tr>
                        <tr>
                            <td><code>owner</code></td>
                            <td><code>4,8,12</code></td>
                            <td>Searches owner user IDs. Multiple IDs are supported.</td>
                        </tr>
                        <tr>
                            <td><code>created_by</code></td>
                            <td><code>4,8,12</code></td>
                            <td>Searches created-by user IDs. Multiple IDs are supported.</td>
                        </tr>
                        <tr>
                            <td><code>modified_by</code></td>
                            <td><code>4,8,12</code></td>
                            <td>Searches modified-by user IDs. Multiple IDs are supported.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Specific Contact Search Examples</h3>

                <p>Search by contact name:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=John&search_by=name" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by email:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=gmail.com&search_by=email" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by phone:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=9876&search_by=phone" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by designation:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=Manager&search_by=designation" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by country:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=India,Japan&search_by=country" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by owner IDs:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=4,8,12&search_by=owner" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search by created-by user IDs:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=4,8,12&search_by=created_by" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Account-Based Contact Search</h3>

                <p>Contacts under one account ID:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?account_id=1094" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Search contacts by account name, account website, or account ID:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?account_search=LogiKlu" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Only contacts associated with accounts:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?associated_accounts_only=true" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Combined Contact Search Examples</h3>

                <p>Associated contacts under an account search with designation:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?associated_accounts_only=true&account_search=LogiKlu&search=Manager&search_by=designation" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <p>Contacts in selected countries owned by selected users:</p>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts?search=4,8&search_by=owner&associated_accounts_only=true" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>
            </div>

                        <div class="card">
                <h2>Contact Detail API</h2>

                <p class="endpoint"><span class="method">GET</span>/contacts/{contact_id}</p>
                <p>
                    Fetches one contact by contact ID. The response includes the contact's main information,
                    dynamic fields from <code>lk_central_contacts_details</code>, and the linked account summary
                    if the contact is associated with an account.
                </p>

                <h3>Authentication</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts/CONTACT_ID" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Path Parameter</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Example</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>contact_id</code></td>
                            <td><code>101</code></td>
                            <td>Unique contact ID from <code>lk_central_contacts.contact_id</code>.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Example</h3>
                <pre>curl -X GET "https://api.logiklu.com/api/v1/contacts/101" \\
  -H "X-API-KEY: YOUR_API_KEY"</pre>

                <h3>Response Includes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Section</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><code>contact</code></td>
                            <td>Main contact details such as name, email, phone, WhatsApp, designation, department, address, source, owner, created by, and modified by.</td>
                        </tr>
                        <tr>
                            <td><code>dynamic_fields</code></td>
                            <td>Additional contact fields from <code>lk_central_contacts_details</code>.</td>
                        </tr>
                        <tr>
                            <td><code>account</code></td>
                            <td>Full linked account summary from <code>lk_lead_master</code>, if the contact is associated with an account.</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Sample Response Structure</h3>
                <pre>{
  "status": "success",
  "message": "Contact detail fetched successfully",
  "meta": {
    "generated_at": "2026-05-27T10:00:00+00:00",
    "contact_id": 101
  },
  "data": {
    "contact": {
      "contact_id": 101,
      "contact_type": "contact",
      "name": "John Smith",
      "email": "john@example.com",
      "phone": "+91 1234567890",
      "whatsapp": "+91 9876543210",
      "alternative_phone": "",
      "alternative_emails": "",
      "social_network": {
        "Linkedin": "https://www.linkedin.com/in/example"
      },
      "address": "",
      "city": "Kolkata",
      "state": "West Bengal",
      "country": "India",
      "zipcode": "700001",
      "avatar": "",
      "department": "Sales",
      "designation": "Sales Manager",
      "source": "Website Visitor",
      "source_details": {},
      "owner": {
        "name": "Owner Name",
        "email": "owner@example.com"
      },
      "created_by": {
        "name": "Creator Name",
        "email": "creator@example.com"
      },
      "created_date": "2026-05-20 10:30:00",
      "modified_by": {
        "name": "Modifier Name",
        "email": "modifier@example.com"
      },
      "modified_date": "2026-05-21 12:15:00",
      "notes": "",
      "dynamic_fields": {},
      "account": {
        "account_id": 1094,
        "account_name": "LogiKlu",
        "lead_category": "Lead",
        "website": "logiklu.com"
      }
    }
  }
}</pre>

                <h3>Error Example</h3>
                <pre>{
  "status": "error",
  "message": "Contact not found",
  "error_code": "CONTACT_NOT_FOUND",
  "data": {
    "contact_id": 101,
    "timestamp": "2026-05-27T10:00:00+00:00"
  }
}</pre>
            </div>

            <div class="footer">
                LogiKlu API &copy; Usage Guide
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html)