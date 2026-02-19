from typing import Optional
from pydantic import BaseModel, EmailStr

from .user import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: EmailStr


class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    user: UserResponse


class PasswordChange(BaseModel):
    old_password: str
    new_password: str
