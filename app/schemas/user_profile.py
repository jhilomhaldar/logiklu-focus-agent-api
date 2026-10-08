from pydantic import BaseModel, Field


class UserChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=1, max_length=255)
    confirm_password: str = Field(..., min_length=1, max_length=255)
