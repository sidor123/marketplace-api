from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr, model_validator
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    price: Decimal = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    category: str = Field(..., min_length=1, max_length=100)
    status: ProductStatus
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('price must be greater than 0')
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[ProductStatus] = None
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('price must be greater than 0')
        return v


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    description: Optional[str]
    price: Decimal
    stock: int
    category: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total_elements: int
    page: int
    size: int


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., ge=1, le=999)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1, max_length=50)
    promo_code: Optional[str] = Field(None, pattern=r'^[A-Z0-9_]{4,20}$')


class OrderUpdate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1, max_length=50)
    promo_code: Optional[str] = Field(None, pattern=r'^[A-Z0-9_]{4,20}$')


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    price_at_order: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    user_id: uuid.UUID
    status: OrderStatus
    promo_code: Optional[str] = None
    total_amount: Decimal
    discount_amount: Decimal
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime
    details: Optional[dict] = None
    
    @model_validator(mode='before')
    @classmethod
    def extract_promo_code(cls, data: Any) -> Any:
        # If data is a dict, return as is
        if isinstance(data, dict):
            return data
        
        # If data is an ORM object, extract promo_code
        if hasattr(data, 'promo_code') and data.promo_code is not None:
            # If it's a PromoCode object, extract the code string
            if hasattr(data.promo_code, 'code'):
                # Create a dict-like object with the code string
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


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime


# Promo Code schemas
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
