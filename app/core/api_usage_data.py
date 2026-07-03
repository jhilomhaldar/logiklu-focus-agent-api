API_USAGE_DATA = {
    "title": "LogiKlu Focus API Guide",
    "subtitle": "Client-facing developer guide for LogiKlu Focus Account Intelligence APIs using OAuth 2.0 Bearer JWT authentication.",
    "base_url": "https://api.logiklu.com",
    "sandbox_base_url": "https://sandboxapi.logiklu.com",
    "local_base_url": "http://127.0.0.1:8000",
    "api_version": "v1",
    "auth_badge": "Bearer JWT",
    "quick_start_auth_type": "bearer",
    "auth": {
        "title": "Authentication",
        "description": "Protected APIs use OAuth 2.0 Client Credentials with a short-lived Bearer JWT. First generate an access token from /oauth/token, then send it in the Authorization header.",
        "headers": [
            {
                "name": "Authorization",
                "required": "Yes",
                "description": "Use Bearer authentication for protected APIs. Format: Authorization: Bearer <access_token>."
            }
        ],
        "token_endpoint": {
            "method": "POST",
            "path": "/oauth/token",
            "auth": "No Auth",
            "content_type": "application/json",
            "description": "Generate a short-lived access token using the OAuth client credentials flow.",
            "request_body": {
                "client_id": "OAuth client ID provided by LogiKlu.",
                "client_secret": "Client secret provided by LogiKlu. Keep this private.",
                "grant_type": "client_credentials"
            },
            "response_fields": {
                "access_token": "JWT access token to be sent as Bearer token.",
                "token_type": "Bearer",
                "expires_in": "Token lifetime in seconds. Current default is 900 seconds.",
                "scope": "Allowed API permissions/scopes."
            }
        }
    },
    "response_format": {
        "success": {
            "status": "success",
            "message": "Focus Account Intelligence fetched successfully",
            "meta": {
                "generated_at": "2026-07-03T10:00:00+00:00",
                "page": 1,
                "per_page": 10,
                "record_count": 10
            },
            "data": {
                "logiklu_account_inetellegence": []
            }
        },
        "error": {
            "status": "error",
            "message": "Missing API key or bearer token",
            "error_code": "AUTH_CREDENTIALS_MISSING",
            "meta": {
                "timestamp": "2026-07-03T10:00:00+00:00"
            },
            "data": None
        }
    },
    "notes": [
        {
            "title": "OAuth token flow",
            "description": "Call /oauth/token with client_id, client_secret, and grant_type=client_credentials. Then send the returned access_token as Authorization: Bearer <access_token>."
        },
        {
            "title": "Bearer token expiry",
            "description": "Access tokens are short-lived. The current default expiry is 900 seconds. Generate a new token when the previous token expires."
        },
        {
            "title": "No JWT secret sharing",
            "description": "JWT_SECRET_KEY is an internal LogiKlu server secret. It must never be shared with API consumers."
        },
        {
            "title": "Clean endpoint paths",
            "description": "Public API routes use clean paths such as /oauth/token and /focus/account-intelligence. Do not prefix these routes with /api/v1."
        },
        {
            "title": "API logging",
            "description": "API requests are logged internally for audit, troubleshooting, and support. Sandbox and production logs are stored separately."
        }
    ],
    "sections": [
        {
            "id": "authentication",
            "title": "OAuth / JWT Authentication",
            "description": "Generate a Bearer access token using client credentials, then call protected APIs with Authorization: Bearer <access_token>.",
            "endpoints": [
                {
                    "id": "oauth-token",
                    "title": "Generate Access Token",
                    "method": "POST",
                    "path": "/oauth/token",
                    "purpose": "Generate a Bearer access token using the client credentials provided by LogiKlu.",
                    "auth_type": "none",
                    "request_type": "JSON Body",
                    "parameters": [
                        {
                            "name": "client_id",
                            "type": "string",
                            "required": "Yes",
                            "example": "lkc_3f2a6a9eae2c4b2db37f9875f0e9a111",
                            "description": "OAuth client ID provided by LogiKlu."
                        },
                        {
                            "name": "client_secret",
                            "type": "string",
                            "required": "Yes",
                            "example": "provided_client_secret",
                            "description": "Client secret provided by LogiKlu. Keep this private and never expose it in frontend code."
                        },
                        {
                            "name": "grant_type",
                            "type": "string",
                            "required": "Yes",
                            "example": "client_credentials",
                            "description": "Must be client_credentials."
                        }
                    ],
                    "body": {
                        "client_id": "YOUR_CLIENT_ID",
                        "client_secret": "YOUR_CLIENT_SECRET",
                        "grant_type": "client_credentials"
                    },
                    "examples": [
                        {
                            "title": "Generate token",
                            "description": "Call this endpoint with No Auth. Use the returned access_token as Bearer token for protected APIs.",
                            "path": "/oauth/token",
                            "body": {
                                "client_id": "YOUR_CLIENT_ID",
                                "client_secret": "YOUR_CLIENT_SECRET",
                                "grant_type": "client_credentials"
                            }
                        }
                    ],
                    "response_example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 900,
                        "scope": "focus:account-intelligence:read"
                    }
                }
            ]
        },
        {
            "id": "focus-account-intelligence",
            "title": "Focus Account Intelligence",
            "description": "Use Focus Account Intelligence APIs to read LogiKlu Focus buying-intent signals, priority score, interest level, evidence facts, contacts, and journey intelligence for accounts.",
            "endpoints": [
                {
                    "id": "focus-account-intelligence-list",
                    "title": "Focus Account Intelligence List",
                    "method": "GET",
                    "path": "/focus/account-intelligence",
                    "purpose": "Fetch Focus Account Intelligence records with search, filters, pagination, signal summary, and journey intelligence. Journey data is included by default.",
                    "auth_type": "bearer",
                    "request_type": "Query Parameters",
                    "parameters": [
                        {
                            "name": "page",
                            "type": "integer",
                            "required": "No",
                            "example": "1",
                            "description": "Page number. Default is 1."
                        },
                        {
                            "name": "per_page",
                            "type": "integer",
                            "required": "No",
                            "example": "10",
                            "description": "Number of records per page."
                        },
                        {
                            "name": "search",
                            "type": "string",
                            "required": "No",
                            "example": "LogiKlu",
                            "description": "Search by account/company name, website, city, state, country, or related searchable values."
                        },
                        {
                            "name": "interest_level",
                            "type": "string",
                            "required": "No",
                            "example": "High",
                            "description": "Filter by interest level when available."
                        },
                        {
                            "name": "priority_label",
                            "type": "string",
                            "required": "No",
                            "example": "Hot",
                            "description": "Filter by priority label such as Hot, Warm, Monitor, or Low when available."
                        },
                        {
                            "name": "is_shortlisted",
                            "type": "boolean",
                            "required": "No",
                            "example": "true",
                            "description": "Filter shortlisted records. Supported values usually true/false or 1/0."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get first page of Focus Account Intelligence",
                            "description": "Use this to retrieve the first page of account intelligence records.",
                            "path": "/focus/account-intelligence",
                            "query": {
                                "page": 1,
                                "per_page": 10
                            }
                        },
                        {
                            "title": "Search Focus Account Intelligence",
                            "description": "Search Focus intelligence records by account-related text.",
                            "path": "/focus/account-intelligence",
                            "query": {
                                "search": "LogiKlu",
                                "page": 1,
                                "per_page": 10
                            }
                        },
                        {
                            "title": "Filter by priority",
                            "description": "Fetch records matching a priority label.",
                            "path": "/focus/account-intelligence",
                            "query": {
                                "priority_label": "Hot",
                                "page": 1,
                                "per_page": 10
                            }
                        }
                    ],
                    "response_example": {
                        "status": "success",
                        "message": "Focus Account Intelligence fetched successfully",
                        "meta": {
                            "generated_at": "2026-07-03T10:00:00+00:00",
                            "page": 1,
                            "per_page": 10,
                            "record_count": 1
                        },
                        "data": {
                            "logiklu_account_inetellegence": [
                                {
                                    "schema_version": "logiklu_focus_account_intelligence.v1",
                                    "account": {
                                        "account_id": 1094,
                                        "company_name": "LogiKlu"
                                    },
                                    "signal_summary": {},
                                    "top_evidence_facts": []
                                }
                            ]
                        }
                    }
                },
                {
                    "id": "focus-account-intelligence-detail",
                    "title": "Focus Account Intelligence Details",
                    "method": "GET",
                    "path": "/focus/account-intelligence/{account_id}",
                    "purpose": "Fetch one account intelligence record by account ID with score, signal summary, evidence, contacts, and journey intelligence.",
                    "auth_type": "bearer",
                    "request_type": "Path Parameter",
                    "parameters": [
                        {
                            "name": "account_id",
                            "type": "integer",
                            "required": "Yes",
                            "example": "1094",
                            "description": "Account ID / lead ID for which Focus intelligence should be fetched."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get one Focus Account Intelligence record",
                            "description": "Use this when you already know the account ID.",
                            "path": "/focus/account-intelligence/1094",
                            "query": {}
                        }
                    ],
                    "response_example": {
                        "status": "success",
                        "message": "Focus Account Intelligence fetched successfully",
                        "meta": {
                            "generated_at": "2026-07-03T10:00:00+00:00",
                            "account_id": 1094
                        },
                        "data": {
                            "logiklu_account_inetellegence": {
                                "schema_version": "logiklu_focus_account_intelligence.v1",
                                "account": {
                                    "account_id": 1094,
                                    "company_name": "LogiKlu"
                                },
                                "signal_summary": {},
                                "top_evidence_facts": []
                            }
                        }
                    }
                }
            ]
        }
    ],
    "errors": [
        {
            "code": "AUTH_CREDENTIALS_MISSING",
            "http_status": 401,
            "meaning": "No bearer token was sent.",
            "fix": "Generate a token using /oauth/token and send Authorization: Bearer <access_token>."
        },
        {
            "code": "AUTHORIZATION_HEADER_INVALID",
            "http_status": 401,
            "meaning": "Authorization header was sent in an invalid format.",
            "fix": "Use Authorization: Bearer <access_token>."
        },
        {
            "code": "OAUTH_INVALID_CLIENT",
            "http_status": 401,
            "meaning": "The client_id is invalid or not found.",
            "fix": "Check the client_id provided by LogiKlu."
        },
        {
            "code": "OAUTH_INVALID_CLIENT_SECRET",
            "http_status": 401,
            "meaning": "The client_secret is invalid.",
            "fix": "Check the client_secret provided by LogiKlu."
        },
        {
            "code": "OAUTH_UNSUPPORTED_GRANT_TYPE",
            "http_status": 400,
            "meaning": "The grant_type is not supported.",
            "fix": "Use grant_type=client_credentials."
        },
        {
            "code": "AUTH_JWT_INVALID",
            "http_status": 401,
            "meaning": "The bearer token is malformed or invalid.",
            "fix": "Generate a fresh token from /oauth/token and retry."
        },
        {
            "code": "AUTH_JWT_EXPIRED",
            "http_status": 401,
            "meaning": "The bearer token has expired.",
            "fix": "Generate a fresh token from /oauth/token."
        },
        {
            "code": "AUTH_JWT_AUDIENCE_INVALID",
            "http_status": 401,
            "meaning": "The bearer token audience does not match this API environment.",
            "fix": "Use a token generated for the correct environment."
        },
        {
            "code": "AUTH_JWT_ENVIRONMENT_MISMATCH",
            "http_status": 401,
            "meaning": "The bearer token was generated for a different environment.",
            "fix": "Use sandbox tokens only on sandbox and production tokens only on production."
        },
        {
            "code": "LOGIKLU_ACCOUNT_INTELLIGENCE_NOT_FOUND",
            "http_status": 404,
            "meaning": "No LogiKlu account intelligence record was found for the requested account_id.",
            "fix": "Use a valid account_id available in the current LogiKlu Focus intelligence dataset."
        },
        {
            "code": "VALIDATION_ERROR",
            "http_status": 422,
            "meaning": "One or more request parameters are invalid.",
            "fix": "Check parameter names, types, and allowed values."
        },
        {
            "code": "INTERNAL_SERVER_ERROR",
            "http_status": 500,
            "meaning": "Unexpected server-side error.",
            "fix": "Retry later or contact LogiKlu technical support with request details."
        }
    ],
    "logging": {
        "title": "API Request Logging",
        "description": "LogiKlu stores API request logs internally for audit, troubleshooting, and support.",
        "logged_fields": [
            "oauth_client_id",
            "auth_type",
            "api_client_id",
            "domain_id",
            "client_database",
            "environment",
            "endpoint",
            "request_method",
            "ip_address",
            "user_agent",
            "request_params",
            "http_status_code",
            "response_status",
            "error_code",
            "error_message",
            "execution_time_ms",
            "created_at"
        ],
        "sandbox_table": "lk_agent_api_request_logs_sandbox",
        "production_table": "lk_agent_api_request_logs"
    }
}
