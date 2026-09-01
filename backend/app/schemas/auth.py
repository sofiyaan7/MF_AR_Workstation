"""Authentication request/response models."""
from pydantic import BaseModel, Field

from app.schemas.user import UserProfile


class LoginRequest(BaseModel):
    # The sign-in name is the person's full name, not their employee ID.
    username: str = Field(min_length=1, max_length=160, examples=["Sofiyaan Sameer"])
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
    # Matches the sign-in form, which now collects the full name.
    username: str = Field(min_length=1, max_length=160)
