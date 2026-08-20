"""
schemas.py
----------
Pydantic request/response shapes.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
import re


def _check_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Password must include at least one letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must include at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=]", password):
        raise ValueError("Password must include at least one symbol")
    return password


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return _check_password_strength(v)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendCodeRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        return _check_password_strength(v)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None
    theme_preference: Optional[str] = None
    is_verified: bool

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None
    theme_preference: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Products ----------
class ProductCreate(BaseModel):
    url: HttpUrl
    target_price: float


class PriceHistoryOut(BaseModel):
    price: float
    checked_at: datetime

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    name: str
    url: str
    site: str
    target_price: float
    current_price: Optional[float]
    last_checked: Optional[datetime]
    is_active: bool
    image_url: Optional[str] = None
    category: Optional[str] = None
    group_id: Optional[str] = None
    is_primary: bool

    class Config:
        from_attributes = True


class ProductDetail(ProductOut):
    price_history: List[PriceHistoryOut] = []