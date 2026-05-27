API_USAGE_DATA = {
    "title": "LogiKlu Agent API Guide",
    "subtitle": "Simple instructions for using LogiKlu account and contact APIs.",
    "base_url": "https://api.logiklu.com",
    "auth": {
        "title": "Authentication",
        "description": "Every protected API request must include your API key in the request header.",
        "headers": [
            {
                "name": "X-API-KEY",
                "required": "Yes",
                "description": "Your assigned API key."
            }
        ],
        "example": 'curl -X GET "https://api.logiklu.com/accounts" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
    },
    "response_format": {
        "success": {
            "status": "success",
            "message": "Accounts fetched successfully",
            "meta": {
                "generated_at": "2026-05-27T10:00:00+00:00",
                "limit": 20,
                "offset": 0,
                "record_count": 20,
                "total_records": 357
            },
            "data": {}
        },
        "error": {
            "status": "error",
            "message": "Missing API key",
            "error_code": "AUTH_API_KEY_MISSING",
            "data": None
        }
    },
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
                    "path": "/accounts",
                    "purpose": "Fetch account records with search, filters, pagination, contacts, and dynamic account fields.",
                    "request_type": "query_params",
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
                            "description": "Search value. If search_by is empty, this searches common account fields."
                        },
                        {
                            "name": "search_by",
                            "required": "No",
                            "example": "lead_name",
                            "description": "Specific field to search. Example: lead_name, country, owner, assigned_to."
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
                            "description": "Advanced JSON filters."
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
                            "description": "Use this when you want the first page of active accounts.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?limit=20&offset=0" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search account generally",
                            "description": "This searches common account fields.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?search=Japan&limit=20&offset=0" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search by account name",
                            "description": "Use search_by when you want to search one specific field.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?search=Hamamatsu&search_by=lead_name" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Get only Lead accounts",
                            "description": "Lead means raw category is lead and the account has active contacts.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?computed_lead_category=lead" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Get only Potential Lead accounts",
                            "description": "Potential Lead means suspect, or lead with no active contacts.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?computed_lead_category=potential_lead" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search assigned accounts",
                            "description": "This searches accounts assigned to selected user IDs.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts?search=4,8&search_by=assigned_to" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Advanced filter by country",
                            "description": "Use filters when you need field/operator/value style search.",
                            "curl": 'curl -X GET \'https://api.logiklu.com/accounts?filters=[{"field":"country","operator":"eq","value":"Japan"}]\' \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        }
                    ]
                },
                {
                    "id": "account-detail",
                    "title": "Account Details",
                    "method": "GET",
                    "path": "/accounts/{account_id}",
                    "purpose": "Fetch one account by account ID with dynamic fields and contacts.",
                    "request_type": "path_param",
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
                            "title": "Get account detail",
                            "description": "Use this when you already know the account ID.",
                            "curl": 'curl -X GET "https://api.logiklu.com/accounts/9626" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
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
                    "path": "/contacts",
                    "purpose": "Fetch contacts with search, account search, owner filters, dynamic fields, and linked account summary.",
                    "request_type": "query_params",
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
                            "description": "Search value. If search_by is empty, this searches common contact fields."
                        },
                        {
                            "name": "search_by",
                            "required": "No",
                            "example": "designation",
                            "description": "Specific field to search."
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
                            "description": "Use this when you want the first page of active contacts.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?limit=50&offset=0" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search contacts generally",
                            "description": "This searches common contact fields.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?search=manager" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search by contact name",
                            "description": "Search first name, last name, and full name.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?search=John&search_by=name" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search by email",
                            "description": "Search contacts by email.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?search=gmail.com&search_by=email" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Contacts under one account",
                            "description": "Fetch contacts linked with one account ID.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?account_id=1094" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search by account",
                            "description": "Search contacts by account ID, account name, or account website.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?account_search=LogiKlu" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Only contacts linked to accounts",
                            "description": "Use this when you do not want standalone/unlinked contacts.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?associated_accounts_only=true" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        },
                        {
                            "title": "Search by owner IDs",
                            "description": "Search contacts owned by selected user IDs.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts?search=4,8&search_by=owner" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        }
                    ]
                },
                {
                    "id": "contact-detail",
                    "title": "Contact Details",
                    "method": "GET",
                    "path": "/contacts/{contact_id}",
                    "purpose": "Fetch one contact by contact ID with dynamic fields and linked account summary.",
                    "request_type": "path_param",
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
                            "title": "Get contact detail",
                            "description": "Use this when you already know the contact ID.",
                            "curl": 'curl -X GET "https://api.logiklu.com/contacts/101" \\\n  -H "X-API-KEY: YOUR_API_KEY"'
                        }
                    ]
                }
            ]
        }
    ],
    "errors": [
        {
            "code": "AUTH_API_KEY_MISSING",
            "meaning": "API key was not sent in the header.",
            "fix": "Send X-API-KEY in request headers."
        },
        {
            "code": "AUTH_INVALID_API_KEY",
            "meaning": "The API key is wrong or not found.",
            "fix": "Check the API key value."
        },
        {
            "code": "ACCOUNT_NOT_FOUND",
            "meaning": "No account found for the given account ID.",
            "fix": "Use a valid account ID."
        },
        {
            "code": "CONTACT_NOT_FOUND",
            "meaning": "No contact found for the given contact ID.",
            "fix": "Use a valid contact ID."
        }
    ]
}