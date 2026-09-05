from typing import Optional

from pydantic import BaseModel, Field


class MobileLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)
    current_timezone: Optional[str] = Field(default="UTC", max_length=100)


class MobileWebSessionRequest(BaseModel):
    domain_id: int = Field(..., gt=0)
    account_id: Optional[int] = Field(default=None, gt=0)
    current_timezone: Optional[str] = Field(default="UTC", max_length=100)
    check_os: Optional[str] = Field(default=None, max_length=100)
    check_version: Optional[str] = Field(default=None, max_length=100)


class MobileWebSessionConsumeRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
