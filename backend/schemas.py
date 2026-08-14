"""Request/response JSON shapes."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, HttpUrl


class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    profile_picture_url: Optional[str] = None

    class Config:
        from_attributes = True

   

class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    profile_picture_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    matched_product_id: Optional[int] = None
    class Config:
        from_attributes = True


class ProductDetail(ProductOut):
    price_history: List[PriceHistoryOut] = []