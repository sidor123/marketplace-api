from typing import Any, Optional
from decimal import Decimal
from datetime import datetime
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
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('price must be greater than 0')
        return v


class ProductResponse(GeneratedProductResponse):
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(GeneratedOrderCreate):
    pass


class OrderUpdate(GeneratedOrderUpdate):
    promo_code: Optional[str] = Field(
        default=None, description='Promo code (optional)', pattern=r'^[A-Z0-9_]{4,20}$'
    )


class OrderItemResponse(GeneratedOrderItemResponse):
    model_config = ConfigDict(from_attributes=True)


class OrderResponse(GeneratedOrderResponse):
    model_config = ConfigDict(from_attributes=True)
    
    details: Optional[dict] = None
    
    @model_validator(mode='before')
    @classmethod
    def extract_promo_code(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        
        if hasattr(data, 'promo_code') and data.promo_code is not None:
            if hasattr(data.promo_code, 'code'):
                data_dict = {
                    'id': data.id,
                    'user_id': data.user_id,
                    'status': data.status,
                    'promo_code': data.promo_code.code,
                    'total_amount': data.total_amount,
                    'discount_amount': data.discount_amount,
                    'items': data.items,
                    'created_at': data.created_at,
                    'updated_at': data.updated_at,
                }
                return data_dict
        
        return data


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
