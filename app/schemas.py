from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, EmailStr

from generated.schemas import (
    TokenResponse,
    ProductStatus,
    ProductCreate as GeneratedProductCreate,
    ProductUpdate as GeneratedProductUpdate,
    ProductResponse as GeneratedProductResponse,
    ProductListResponse,
    OrderStatus,
    OrderItemCreate,
    OrderCreate as GeneratedOrderCreate,
    OrderUpdate as GeneratedOrderUpdate,
    OrderItemResponse as GeneratedOrderItemResponse,
    OrderResponse as GeneratedOrderResponse,
    ErrorResponse,
)


class UserRole(str, Enum):
    USER = "USER"
    SELLER = "SELLER"
    ADMIN = "ADMIN"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: Optional[UserRole] = UserRole.USER

    @field_validator('password')
    @classmethod
    def password_byte_length(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_AMOUNT = "FIXED_AMOUNT"


class PromoCodeCreate(BaseModel):
    code: str = Field(..., pattern=r'^[A-Z0-9_]{4,20}$', min_length=4, max_length=20)
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal = Field(default=Decimal(0), ge=0)
    max_uses: int = Field(..., gt=0)
    valid_from: datetime
    valid_until: datetime
    active: bool = Field(default=True)

    @field_validator('valid_from', 'valid_until')
    @classmethod
    def normalize_dates(cls, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator('valid_until')
    @classmethod
    def validate_dates(cls, v, info):
        if 'valid_from' in info.data and v <= info.data['valid_from']:
            raise ValueError('valid_until must be after valid_from')
        return v


class PromoCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    min_order_amount: Decimal
    max_uses: int
    current_uses: int
    valid_from: datetime
    valid_until: datetime
    active: bool


class ProductCreate(GeneratedProductCreate):
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('price must be greater than 0')
        return v


class ProductUpdate(GeneratedProductUpdate):
    @model_validator(mode='before')
    @classmethod
    def reject_null_fields(cls, data):
        if isinstance(data, dict):
            for field in ('name', 'price', 'stock', 'category', 'status'):
                if field in data and data[field] is None:
                    raise ValueError(f'{field} cannot be null')
        return data

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('price must be greater than 0')
        return v


class TimestampResponse(BaseModel):
    @field_validator('created_at', 'updated_at', mode='before', check_fields=False)
    @classmethod
    def ensure_timezone_aware(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class ProductResponse(GeneratedProductResponse, TimestampResponse):
    seller_id: Optional[uuid.UUID] = None
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(GeneratedOrderCreate):
    @field_validator('items')
    @classmethod
    def unique_products(cls, items):
        if len({item.product_id for item in items}) != len(items):
            raise ValueError('Each product must appear only once')
        return items


class OrderUpdate(GeneratedOrderUpdate):
    _unique_products = field_validator('items')(OrderCreate.unique_products.__func__)

    promo_code: Optional[str] = Field(
        default=None, description='Promo code (optional)', pattern=r'^[A-Z0-9_]{4,20}$'
    )


class OrderItemResponse(GeneratedOrderItemResponse):
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(GeneratedOrderResponse, TimestampResponse):
    items: list[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)

    details: Optional[dict] = None

    @field_validator('promo_code', mode='before')
    @classmethod
    def extract_promo_code(cls, value):
        return getattr(value, 'code', value)


__all__ = [
    'TokenResponse',
    'UserRole',
    'UserRegister',
    'UserLogin',
    'RefreshTokenRequest',
    'UserResponse',

    'ProductStatus',
    'ProductCreate',
    'ProductUpdate',
    'ProductResponse',
    'ProductListResponse',

    'OrderStatus',
    'OrderItemCreate',
    'OrderCreate',
    'OrderUpdate',
    'OrderItemResponse',
    'OrderResponse',

    'DiscountType',
    'PromoCodeCreate',
    'PromoCodeResponse',

    'ErrorResponse',
]
