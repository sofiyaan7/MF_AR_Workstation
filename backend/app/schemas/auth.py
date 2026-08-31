"""Authentication request/response models."""
from pydantic import BaseModel, Field

from app.schemas.user import UserProfile


class LoginRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64, examples=["ARWL12345"])
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class LoginResponse(BaseModel):
    user: UserProfile
    csrf_token: str
    must_change_password: bool = False
    message: str = "Signed in successfully"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)


class PasswordPolicyResponse(BaseModel):
    min_length: int
    requirements: list[str]


class ForgotPasswordRequest(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
