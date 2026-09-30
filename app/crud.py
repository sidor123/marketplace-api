from sqlalchemy.orm import Session
from typing import Optional
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from app.models import Product, ProductStatus, PromoCode, DiscountType


def create_product(db: Session, data: dict) -> Product:
    status_value = data['status']
    if isinstance(status_value, str):
        status_enum = ProductStatus[status_value]
    elif hasattr(status_value, 'value'):
        status_enum = ProductStatus[status_value.value]
    else:
        status_enum = status_value
    
    db_product = Product(
        name=data['name'],
        description=data.get('description'),
        price=Decimal(str(data['price'])),
        stock=int(data['stock']),
        category=data['category'],
        status=status_enum,
        seller_id=data.get('seller_id')
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_product(db: Session, product_id: uuid.UUID) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_products(
    db: Session,
    page: int = 0,
    size: int = 20,
    status: Optional[ProductStatus] = None,
    category: Optional[str] = None
) -> tuple[list[Product], int]:
    query = db.query(Product)
    
    if status:
        query = query.filter(Product.status == status)
    if category:
        query = query.filter(Product.category == category)
    
    total = query.count()
    products = query.order_by(Product.created_at.desc(), Product.id).offset(page * size).limit(size).all()
    return products, total


def update_product(
    db: Session,
    product_id: uuid.UUID,
    data: dict
) -> Optional[Product]:
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    if 'name' in data:
        db_product.name = data['name']
    if 'description' in data:
        db_product.description = data['description']
    if 'price' in data:
        db_product.price = Decimal(str(data['price'])) # type: ignore
    if 'stock' in data:
        db_product.stock = int(data['stock']) # type: ignore
    if 'category' in data:
        db_product.category = data['category']
    if 'status' in data:
        status_value = data['status']
        if isinstance(status_value, str):
            db_product.status = ProductStatus[status_value] # type: ignore
        elif hasattr(status_value, 'value'):
            db_product.status = ProductStatus[status_value.value] # type: ignore
        else:
            db_product.status = status_value # type: ignore

    db_product.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: uuid.UUID) -> bool:
    db_product = get_product(db, product_id)
    if not db_product:
        return False
    
    db_product.status = ProductStatus.ARCHIVED  # type: ignore
    db_product.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.commit()
    return True


def create_promo_code(db: Session, data: dict) -> PromoCode:
    discount_type_value = data['discount_type']
    if isinstance(discount_type_value, str):
        discount_type_enum = DiscountType[discount_type_value]
    else:
        discount_type_enum = discount_type_value
    
    valid_from = data['valid_from']
    if isinstance(valid_from, str):
        valid_from = datetime.fromisoformat(valid_from.replace('Z', '+00:00'))
    
    valid_until = data['valid_until']
    if isinstance(valid_until, str):
        valid_until = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
    
    db_promo_code = PromoCode(
        code=data['code'],
        discount_type=discount_type_enum,
        discount_value=Decimal(str(data['discount_value'])),
        min_order_amount=Decimal(str(data.get('min_order_amount', 0))),
        max_uses=int(data['max_uses']),
        valid_from=valid_from,
        valid_until=valid_until,
        active=data.get('active', True)
    )
    db.add(db_promo_code)
    db.commit()
    db.refresh(db_promo_code)
    return db_promo_code
