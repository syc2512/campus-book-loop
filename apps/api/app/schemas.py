from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TextbookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    isbn: str
    title: str
    author: str
    publisher: str
    edition: str
    course_code: str
    course_name: str
    major: str
    category: str
    new_price: float
    description: str


class ListingCreate(BaseModel):
    textbook_id: str
    condition_grade: int = Field(ge=1, le=10)
    asking_price: float = Field(gt=0, le=5000)
    note: str = Field(default="", max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("image_url")
    @classmethod
    def safe_image_url(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.startswith(("/media/", "http://", "https://")):
            raise ValueError("image_url must be a /media path or an absolute http(s) URL")
        return value


class ImageUploadResponse(BaseModel):
    image_url: str
    content_type: str
    byte_size: int


class ListingRead(BaseModel):
    id: str
    seller_id: str
    seller_name: str
    textbook_id: str
    textbook_title: str
    course_name: str
    major: str
    edition: str
    new_price: float
    condition_grade: int
    asking_price: float
    note: str
    image_url: str | None
    status: str
    created_at: datetime


class PriceEstimateRequest(BaseModel):
    new_price: float = Field(gt=0, le=5000)
    condition_grade: int = Field(ge=1, le=10)
    category: str = "专业课"
    demand_factor: float = Field(default=1.0, ge=0.6, le=1.6)
    has_notes: bool = False
    edition_current: bool = True


class PriceEstimateResponse(BaseModel):
    suggested_price: float
    low_price: float
    high_price: float
    source: str
    model_version: str
    factors: dict[str, float]
    disclaimer: str


class RecommendationItem(BaseModel):
    textbook: TextbookRead
    available_count: int
    lowest_price: float
    reason: str
    score: float


class RecommendationResponse(BaseModel):
    strategy: str
    items: list[RecommendationItem]


class OrderCreate(BaseModel):
    listing_id: str
    idempotency_key: str = Field(min_length=8, max_length=100)


class OrderRead(BaseModel):
    id: str
    listing_id: str
    textbook_title: str
    buyer_id: str
    seller_id: str
    amount: float
    commission_amount: float
    status: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime


class AdminOrderRead(OrderRead):
    buyer_name: str
    seller_name: str


class ListingModeration(BaseModel):
    status: Literal["active", "removed"]
    reason: str = Field(default="", max_length=500)


class OrderRefund(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
