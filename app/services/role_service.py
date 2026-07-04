from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "logiklu_role.v1"


STATIC_ROLES = [
    {
        "role_code": "clientsuperadmin",
        "role_name": "Client Super Admin",
        "description": (
            "Client Super Admin users have full access across the client account. "
            "They can view all records, manage all CRM data such as leads, deals, contacts, and activities, "
            "create records for any user, manage all settings, and add any type of user without approval. "
            "Reports are not generated for this role because this is an administrative/software management role, "
            "not a field or market-facing role. This role cannot have child users because it is not part of the field hierarchy."
        ),
        "is_active": True,
    },
    {
        "role_code": "clientadmin",
        "role_name": "Client Admin",
        "description": (
            "Client Admin users have access similar to Client Super Admin users, including broad access to CRM records, "
            "users, and operational data. The key difference is that they cannot add admin-level users directly. "
            "Admin user creation requires approval from a Client Super Admin. Other than this approval restriction, "
            "their access is largely similar to the Client Super Admin role."
        ),
        "is_active": True,
    },
    {
        "role_code": "dataadmin",
        "role_name": "Client Data Admin",
        "description": (
            "Client Data Admin users can manage CRM data such as leads, deals, contacts, and activities. "
            "They can add and update operational CRM records, but they cannot view or modify system settings. "
            "This role is intended for users responsible for maintaining CRM data without administrative configuration access."
        ),
        "is_active": True,
    },
    {
        "role_code": "supervisor",
        "role_name": "Manager",
        "description": (
            "Manager users are part of the field hierarchy. They can manage their own leads, deals, contacts, "
            "and activities, and they can also have child users such as other managers and sales representatives. "
            "They can view reports for themselves and their subordinates. They may create users only under their own hierarchy, "
            "and such user creation requires approval from a Client Admin or Client Super Admin."
        ),
        "is_active": True,
    },
    {
        "role_code": "clientuser",
        "role_name": "Sales Representative",
        "description": (
            "Sales Person users are field workers with limited CRM access. They can manage their own leads, deals, "
            "contacts, and activities, but they cannot create or manage subordinate users. This role is intended for "
            "sales representatives who work on assigned or self-owned CRM records."
        ),
        "is_active": True,
    },
    {
        "role_code": "leadresearcher",
        "role_name": "Lead Researcher",
        "description": (
            "Lead Researcher users are responsible for researching and adding leads. They have access only to lead-related "
            "features and can add or upload leads for managers or sales representatives. This role is focused on lead discovery "
            "and data entry, without access to deals, broader CRM operations, settings, or hierarchy management."
        ),
        "is_active": True,
    },
]


def fetch_roles(
    search: Optional[str] = None,
    role_code: Optional[str] = None,
) -> List[Dict[str, Any]]:
    roles = STATIC_ROLES

    if role_code:
        role_code_value = str(role_code).strip().lower()

        roles = [
            role
            for role in roles
            if str(role.get("role_code", "")).lower() == role_code_value
        ]

    if search:
        search_value = str(search).strip().lower()

        if search_value:
            roles = [
                role
                for role in roles
                if search_value in str(role.get("role_code", "")).lower()
                or search_value in str(role.get("role_name", "")).lower()
                or search_value in str(role.get("description", "")).lower()
            ]

    return roles


def fetch_role_by_code(role_code: str) -> Optional[Dict[str, Any]]:
    if not role_code:
        return None

    role_code_value = str(role_code).strip().lower()

    for role in STATIC_ROLES:
        if str(role.get("role_code", "")).lower() == role_code_value:
            return role

    return None