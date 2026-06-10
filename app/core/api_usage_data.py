API_USAGE_DATA = {
    "title": "LogiKlu Agent API Guide",
    "subtitle": "Developer guide for reading LogiKlu accounts and contacts through sandbox and production APIs.",
    "base_url": "https://api.logiklu.com",
    "sandbox_base_url": "https://sandboxapi.logiklu.com",
    "local_base_url": "http://127.0.0.1:8000",
    "api_version": "v1",
    "environments": [
        {
            "name": "Sandbox",
            "base_url": "https://sandboxapi.logiklu.com",
            "description": "Use this environment for testing API integration before production release."
        },
        {
            "name": "Production",
            "base_url": "https://api.logiklu.com",
            "description": "Use this environment for live production API calls."
        },
        {
            "name": "Local",
            "base_url": "http://127.0.0.1:8000",
            "description": "Use this environment only during local development."
        }
    ],
    "auth": {
        "title": "Authentication",
        "description": "Every protected API request must include your API key in the request header.",
        "headers": [
            {
                "name": "X-API-KEY",
                "required": "Yes",
                "description": "Your assigned API key."
            }
        ]
    },
    "response_format": {
        "success": {
            "status": "success",
            "message": "Accounts fetched successfully",
            "meta": {
                "generated_at": "2026-05-27T10:00:00+00:00",
                "limit": 20,
                "offset": 0,
                "search": None,
                "search_by": None,
                "applied_filters": [
                    {
                        "field": "country",
                        "operator": "like",
                        "value": "India"
                    }
                ],
                "record_count": 20,
                "total_records": 357
            },
            "data": {}
        },
        "error": {
            "status": "error",
            "message": "Missing API key",
            "error_code": "AUTH_API_KEY_MISSING",
            "meta": {
                "timestamp": "2026-05-27T10:00:00+00:00"
            },
            "data": None
        }
    },
    "notes": [
        {
            "title": "Multi-field filters",
            "description": "List APIs support direct query-parameter filters. Example: /api/v1/accounts?country=India&industry=Software. Multiple filters are combined using AND logic."
        },
        {
            "title": "Comma-separated values",
            "description": "Some filters support comma-separated values. Example: /api/v1/accounts?country=India,Japan."
        },
        {
            "title": "Advanced JSON filters",
            "description": "The filters parameter is still supported for advanced field/operator/value filtering."
        },
        {
            "title": "API logging",
            "description": "API requests are logged internally. Sandbox and production logs are stored separately."
        },
        {
            "title": "Standard errors",
            "description": "Authentication errors, validation errors, not-found errors, method errors, and server errors follow the same standard response format."
        }
    ],
    "sections": [
        {
            "id": "accounts",
            "title": "Accounts",
            "description": "Use Account APIs to read company/account information from LogiKlu CRM.",
            "endpoints": [
                {
                    "id": "account-list",
                    "title": "Account List",
                    "method": "GET",
                    "path": "/api/v1/accounts",
                    "purpose": "Fetch account records with general search, multi-field filters, pagination, contacts, and dynamic account fields.",
                    "request_type": "Query Parameters",
                    "parameters": [
                        {
                            "name": "limit",
                            "required": "No",
                            "example": "20",
                            "description": "Number of records to return. Maximum value is 100."
                        },
                        {
                            "name": "offset",
                            "required": "No",
                            "example": "0",
                            "description": "Pagination offset."
                        },
                        {
                            "name": "search",
                            "required": "No",
                            "example": "Hamamatsu",
                            "description": "General search value. If search_by is empty, this searches common account fields."
                        },
                        {
                            "name": "search_by",
                            "required": "No",
                            "example": "lead_name",
                            "description": "Optional old-style specific field search. Example: lead_name, country, owner, assigned_to."
                        },
                        {
                            "name": "lead_publish_status",
                            "required": "No",
                            "example": "active",
                            "description": "Allowed values: active, archive, all."
                        },
                        {
                            "name": "computed_lead_category",
                            "required": "No",
                            "example": "lead",
                            "description": "Allowed values: all, lead, potential_lead, customer."
                        },
                        {
                            "name": "filters",
                            "required": "No",
                            "example": '[{"field":"country","operator":"eq","value":"Japan"}]',
                            "description": "Advanced JSON filters. Use this when operator-level filtering is needed."
                        }
                    ],
                    "multi_field_filters": [
                        {
                            "name": "account_id",
                            "example": "9626",
                            "description": "Exact account ID."
                        },
                        {
                            "name": "lead_name",
                            "example": "LogiKlu",
                            "description": "Filter by account name."
                        },
                        {
                            "name": "lead_segment",
                            "example": "company",
                            "description": "Filter by lead segment."
                        },
                        {
                            "name": "lead_category",
                            "example": "lead",
                            "description": "Filter by raw lead category."
                        },
                        {
                            "name": "lead_type",
                            "example": "hot",
                            "description": "Filter by lead temperature/type."
                        },
                        {
                            "name": "lead_status_id",
                            "example": "1",
                            "description": "Filter by lead status ID."
                        },
                        {
                            "name": "lead_status_name",
                            "example": "New",
                            "description": "Filter by lead status name."
                        },
                        {
                            "name": "website",
                            "example": "logiklu.com",
                            "description": "Filter by website/domain."
                        },
                        {
                            "name": "email",
                            "example": "sales@",
                            "description": "Filter by account email."
                        },
                        {
                            "name": "phone",
                            "example": "9876",
                            "description": "Filter by account phone."
                        },
                        {
                            "name": "industry",
                            "example": "Software",
                            "description": "Filter by industry."
                        },
                        {
                            "name": "city",
                            "example": "Kolkata",
                            "description": "Filter by city."
                        },
                        {
                            "name": "state",
                            "example": "West Bengal",
                            "description": "Filter by state."
                        },
                        {
                            "name": "country",
                            "example": "India,Japan",
                            "description": "Filter by one or multiple countries."
                        },
                        {
                            "name": "zipcode",
                            "example": "700001",
                            "description": "Filter by zipcode."
                        },
                        {
                            "name": "source",
                            "example": "website,manual,csv",
                            "description": "Filter by one or multiple source values."
                        },
                        {
                            "name": "lead_source",
                            "example": "LinkedIn",
                            "description": "Filter by lead source."
                        },
                        {
                            "name": "owner",
                            "example": "4",
                            "description": "Filter by owner user ID."
                        },
                        {
                            "name": "created_by",
                            "example": "4",
                            "description": "Filter by creator user ID."
                        },
                        {
                            "name": "modified_by",
                            "example": "4",
                            "description": "Filter by modifier user ID."
                        }
                    ],
                    "search_by_options": [
                        {
                            "name": "lead_name",
                            "example": "Hamamatsu",
                            "description": "Search account name."
                        },
                        {
                            "name": "lead_segment",
                            "example": "Company",
                            "description": "Company maps to company. Contact maps to contact."
                        },
                        {
                            "name": "lead_category",
                            "example": "Lead",
                            "description": "Potential Lead maps to suspect. Lead maps to lead."
                        },
                        {
                            "name": "lead_type",
                            "example": "hot,warm,cold",
                            "description": "Search one or multiple lead types."
                        },
                        {
                            "name": "lead_persuing_status",
                            "example": "1,2,3",
                            "description": "Search one or multiple lead status IDs."
                        },
                        {
                            "name": "website",
                            "example": "logiklu.com",
                            "description": "Search website/domain."
                        },
                        {
                            "name": "email",
                            "example": "sales@",
                            "description": "Search account email."
                        },
                        {
                            "name": "phone",
                            "example": "9876",
                            "description": "Search account phone."
                        },
                        {
                            "name": "industry",
                            "example": "Software",
                            "description": "Search industry."
                        },
                        {
                            "name": "city",
                            "example": "Kolkata",
                            "description": "Search city."
                        },
                        {
                            "name": "state",
                            "example": "West Bengal",
                            "description": "Search state."
                        },
                        {
                            "name": "country",
                            "example": "India,Japan",
                            "description": "Search one or multiple countries."
                        },
                        {
                            "name": "zipcode",
                            "example": "700001",
                            "description": "Search zipcode."
                        },
                        {
                            "name": "employee_count",
                            "example": "100",
                            "description": "Search employee lower/upper range."
                        },
                        {
                            "name": "owner",
                            "example": "4,8,12",
                            "description": "Search one or multiple owner user IDs."
                        },
                        {
                            "name": "created_by",
                            "example": "4,8",
                            "description": "Search one or multiple creator user IDs."
                        },
                        {
                            "name": "source",
                            "example": "website,manual,csv",
                            "description": "Search one or multiple source values."
                        },
                        {
                            "name": "lead_source",
                            "example": "LinkedIn,Event",
                            "description": "Search one or multiple lead source values."
                        },
                        {
                            "name": "assigned_to",
                            "example": "4,8,12",
                            "description": "Search assigned user IDs from lk_lead_assign."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get first 20 active accounts",
                            "description": "Use this to get the first page of active accounts.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "limit": 20,
                                "offset": 0
                            }
                        },
                        {
                            "title": "General account search",
                            "description": "Search common account fields using one search value.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "search": "Japan",
                                "limit": 20,
                                "offset": 0
                            }
                        },
                        {
                            "title": "Multi-field account filter",
                            "description": "Filter accounts using multiple direct query parameters.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "country": "India",
                                "industry": "Software",
                                "limit": 20
                            }
                        },
                        {
                            "title": "Multi-value country filter",
                            "description": "Filter accounts from one or more countries.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "country": "India,Japan",
                                "limit": 20
                            }
                        },
                        {
                            "title": "Search by account name",
                            "description": "Search only the account name field using old search_by style.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "search": "Hamamatsu",
                                "search_by": "lead_name",
                                "limit": 20,
                                "offset": 0
                            }
                        },
                        {
                            "title": "Get only Lead accounts",
                            "description": "Lead means raw category is lead and the account has active contacts.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "computed_lead_category": "lead",
                                "limit": 20,
                                "offset": 0
                            }
                        },
                        {
                            "title": "Get only Potential Lead accounts",
                            "description": "Potential Lead means suspect, or lead with no active contacts.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "computed_lead_category": "potential_lead",
                                "limit": 20,
                                "offset": 0
                            }
                        },
                        {
                            "title": "Advanced JSON filter",
                            "description": "Use filters for field/operator/value search.",
                            "path": "/api/v1/accounts",
                            "query": {
                                "filters": '[{"field":"country","operator":"eq","value":"Japan"}]'
                            }
                        }
                    ]
                },
                {
                    "id": "account-detail",
                    "title": "Account Details",
                    "method": "GET",
                    "path": "/api/v1/accounts/{account_id}",
                    "purpose": "Fetch one account by account ID with dynamic fields and contacts.",
                    "request_type": "Path Parameter",
                    "parameters": [
                        {
                            "name": "account_id",
                            "required": "Yes",
                            "example": "9626",
                            "description": "Unique account ID from lk_lead_master.lead_id."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get one account detail",
                            "description": "Use this when you already know the account ID.",
                            "path": "/api/v1/accounts/9626",
                            "query": {}
                        }
                    ]
                }
            ]
        },
        {
            "id": "contacts",
            "title": "Contacts",
            "description": "Use Contact APIs to read people/contact information from LogiKlu CRM.",
            "endpoints": [
                {
                    "id": "contact-list",
                    "title": "Contact List",
                    "method": "GET",
                    "path": "/api/v1/contacts",
                    "purpose": "Fetch contacts with general search, multi-field filters, account search, dynamic fields, and linked account summary.",
                    "request_type": "Query Parameters",
                    "parameters": [
                        {
                            "name": "limit",
                            "required": "No",
                            "example": "50",
                            "description": "Number of records to return. Maximum value is 100."
                        },
                        {
                            "name": "offset",
                            "required": "No",
                            "example": "0",
                            "description": "Pagination offset."
                        },
                        {
                            "name": "search",
                            "required": "No",
                            "example": "Manager",
                            "description": "General search value. If search_by is empty, this searches common contact fields."
                        },
                        {
                            "name": "search_by",
                            "required": "No",
                            "example": "designation",
                            "description": "Optional old-style specific contact field search."
                        },
                        {
                            "name": "account_id",
                            "required": "No",
                            "example": "1094",
                            "description": "Fetch contacts under a specific account."
                        },
                        {
                            "name": "account_search",
                            "required": "No",
                            "example": "LogiKlu",
                            "description": "Search contacts by account ID, account name, or account website."
                        },
                        {
                            "name": "associated_accounts_only",
                            "required": "No",
                            "example": "true",
                            "description": "If true, only contacts linked with accounts are returned."
                        },
                        {
                            "name": "filters",
                            "required": "No",
                            "example": '[{"field":"country","operator":"eq","value":"India"}]',
                            "description": "Advanced JSON filters. Use this when operator-level filtering is needed."
                        }
                    ],
                    "multi_field_filters": [
                        {
                            "name": "name",
                            "example": "John",
                            "description": "Filter by first name, last name, or full name."
                        },
                        {
                            "name": "first_name",
                            "example": "John",
                            "description": "Filter by first name."
                        },
                        {
                            "name": "last_name",
                            "example": "Smith",
                            "description": "Filter by last name."
                        },
                        {
                            "name": "email",
                            "example": "gmail.com",
                            "description": "Filter by email."
                        },
                        {
                            "name": "phone",
                            "example": "9876",
                            "description": "Filter by primary phone."
                        },
                        {
                            "name": "whatsapp",
                            "example": "9876",
                            "description": "Filter by WhatsApp number."
                        },
                        {
                            "name": "alternative_phone",
                            "example": "9876",
                            "description": "Filter by alternative phone."
                        },
                        {
                            "name": "alternative_emails",
                            "example": "sales@",
                            "description": "Filter by alternative emails."
                        },
                        {
                            "name": "address",
                            "example": "Park Street",
                            "description": "Filter by address."
                        },
                        {
                            "name": "city",
                            "example": "Kolkata",
                            "description": "Filter by city."
                        },
                        {
                            "name": "state",
                            "example": "West Bengal",
                            "description": "Filter by state."
                        },
                        {
                            "name": "country",
                            "example": "India,Japan",
                            "description": "Filter by one or multiple countries."
                        },
                        {
                            "name": "zipcode",
                            "example": "700001",
                            "description": "Filter by zipcode."
                        },
                        {
                            "name": "department",
                            "example": "Marketing",
                            "description": "Filter by department."
                        },
                        {
                            "name": "designation",
                            "example": "Manager",
                            "description": "Filter by job title/designation."
                        },
                        {
                            "name": "contact_type",
                            "example": "contact",
                            "description": "Filter by contact type."
                        },
                        {
                            "name": "source",
                            "example": "website,manual,csv",
                            "description": "Filter by one or multiple source values."
                        },
                        {
                            "name": "owner",
                            "example": "4",
                            "description": "Filter by owner user ID."
                        },
                        {
                            "name": "created_by",
                            "example": "4",
                            "description": "Filter by creator user ID."
                        },
                        {
                            "name": "modified_by",
                            "example": "4",
                            "description": "Filter by modifier user ID."
                        }
                    ],
                    "search_by_options": [
                        {
                            "name": "name",
                            "example": "John",
                            "description": "Search first name, last name, and full name."
                        },
                        {
                            "name": "first_name",
                            "example": "John",
                            "description": "Search first name."
                        },
                        {
                            "name": "last_name",
                            "example": "Smith",
                            "description": "Search last name."
                        },
                        {
                            "name": "email",
                            "example": "gmail.com",
                            "description": "Search email."
                        },
                        {
                            "name": "phone",
                            "example": "9876",
                            "description": "Search primary phone."
                        },
                        {
                            "name": "whatsapp",
                            "example": "9876",
                            "description": "Search WhatsApp number."
                        },
                        {
                            "name": "alternative_phone",
                            "example": "9876",
                            "description": "Search alternative phone."
                        },
                        {
                            "name": "alternative_emails",
                            "example": "sales@",
                            "description": "Search alternative emails."
                        },
                        {
                            "name": "address",
                            "example": "Park Street",
                            "description": "Search address."
                        },
                        {
                            "name": "city",
                            "example": "Kolkata",
                            "description": "Search city."
                        },
                        {
                            "name": "state",
                            "example": "West Bengal",
                            "description": "Search state."
                        },
                        {
                            "name": "country",
                            "example": "India,Japan",
                            "description": "Search one or multiple countries."
                        },
                        {
                            "name": "zipcode",
                            "example": "700001",
                            "description": "Search zipcode."
                        },
                        {
                            "name": "department",
                            "example": "Marketing",
                            "description": "Search department."
                        },
                        {
                            "name": "designation",
                            "example": "Manager",
                            "description": "Search job title/designation."
                        },
                        {
                            "name": "contact_type",
                            "example": "contact,guest",
                            "description": "Search one or multiple contact types."
                        },
                        {
                            "name": "source",
                            "example": "website,manual,csv",
                            "description": "Search one or multiple source values."
                        },
                        {
                            "name": "owner",
                            "example": "4,8,12",
                            "description": "Search one or multiple owner user IDs."
                        },
                        {
                            "name": "created_by",
                            "example": "4,8",
                            "description": "Search one or multiple creator user IDs."
                        },
                        {
                            "name": "modified_by",
                            "example": "4,8",
                            "description": "Search one or multiple modifier user IDs."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get first 50 contacts",
                            "description": "Use this to get the first page of contacts.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "limit": 50,
                                "offset": 0
                            }
                        },
                        {
                            "title": "General contact search",
                            "description": "Search common contact fields.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "search": "manager"
                            }
                        },
                        {
                            "title": "Multi-field contact filter",
                            "description": "Filter contacts using multiple direct query parameters.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "country": "India",
                                "department": "Sales",
                                "limit": 20
                            }
                        },
                        {
                            "title": "Multi-value country filter",
                            "description": "Filter contacts from one or more countries.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "country": "India,Japan",
                                "limit": 20
                            }
                        },
                        {
                            "title": "Search by contact name",
                            "description": "Search first name, last name, and full name using old search_by style.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "search": "John",
                                "search_by": "name"
                            }
                        },
                        {
                            "title": "Search by email",
                            "description": "Search contacts by email.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "search": "gmail.com",
                                "search_by": "email"
                            }
                        },
                        {
                            "title": "Contacts under one account",
                            "description": "Fetch contacts linked with one account ID.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "account_id": 1094
                            }
                        },
                        {
                            "title": "Search by account",
                            "description": "Search contacts by account ID, account name, or account website.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "account_search": "LogiKlu"
                            }
                        },
                        {
                            "title": "Only contacts linked to accounts",
                            "description": "Use this when you do not want standalone/unlinked contacts.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "associated_accounts_only": "true"
                            }
                        },
                        {
                            "title": "Advanced JSON filter",
                            "description": "Use filters for field/operator/value search.",
                            "path": "/api/v1/contacts",
                            "query": {
                                "filters": '[{"field":"country","operator":"eq","value":"India"}]'
                            }
                        }
                    ]
                },
                {
                    "id": "contact-detail",
                    "title": "Contact Details",
                    "method": "GET",
                    "path": "/api/v1/contacts/{contact_id}",
                    "purpose": "Fetch one contact by contact ID with dynamic fields and linked account summary.",
                    "request_type": "Path Parameter",
                    "parameters": [
                        {
                            "name": "contact_id",
                            "required": "Yes",
                            "example": "101",
                            "description": "Unique contact ID from lk_central_contacts.contact_id."
                        }
                    ],
                    "examples": [
                        {
                            "title": "Get one contact detail",
                            "description": "Use this when you already know the contact ID.",
                            "path": "/api/v1/contacts/101",
                            "query": {}
                        }
                    ]
                }
            ]
        }
    ],
    "errors": [
        {
            "code": "AUTH_API_KEY_MISSING",
            "http_status": 401,
            "meaning": "API key was not sent in the header.",
            "fix": "Send X-API-KEY in request headers."
        },
        {
            "code": "AUTH_INVALID_API_KEY",
            "http_status": 401,
            "meaning": "The API key is wrong or not found.",
            "fix": "Check the API key value."
        },
        {
            "code": "AUTH_API_CLIENT_INACTIVE",
            "http_status": 403,
            "meaning": "The API client is inactive.",
            "fix": "Activate the API client or use an active API key."
        },
        {
            "code": "AUTH_SUBSCRIPTION_INACTIVE",
            "http_status": 403,
            "meaning": "The client subscription is inactive.",
            "fix": "Check the client subscription status."
        },
        {
            "code": "AUTH_IP_NOT_ALLOWED",
            "http_status": 403,
            "meaning": "The request IP address is not allowed for this API key.",
            "fix": "Allow the requesting IP or use an approved network."
        },
        {
            "code": "VALIDATION_ERROR",
            "http_status": 422,
            "meaning": "One or more request parameters are invalid.",
            "fix": "Check parameter names, types, and allowed values."
        },
        {
            "code": "RESOURCE_NOT_FOUND",
            "http_status": 404,
            "meaning": "The requested endpoint or resource was not found.",
            "fix": "Check the endpoint path or resource ID."
        },
        {
            "code": "METHOD_NOT_ALLOWED",
            "http_status": 405,
            "meaning": "The endpoint exists, but the HTTP method is not allowed.",
            "fix": "Use the documented HTTP method for the endpoint."
        },
        {
            "code": "ACCOUNT_NOT_FOUND",
            "http_status": 404,
            "meaning": "No account found for the given account ID.",
            "fix": "Use a valid account ID."
        },
        {
            "code": "CONTACT_NOT_FOUND",
            "http_status": 404,
            "meaning": "No contact found for the given contact ID.",
            "fix": "Use a valid contact ID."
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
            "api_client_id",
            "domain_id",
            "client_database",
            "environment",
            "api_key_prefix",
            "endpoint",
            "request_method",
            "ip_address",
            "user_agent",
            "request_params",
            "request_body for POST, PUT, PATCH, DELETE",
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