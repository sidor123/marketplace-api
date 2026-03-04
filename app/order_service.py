from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import os

from app.models import (
    Order, OrderItem, Product, ProductStatus, OrderStatus,
    PromoCode, DiscountType, UserOperation, OperationType
)
from app.exceptions import (
    ProductNotFoundException, ProductInactiveException,
    OrderNotFoundException, OrderLimitExceededException,
    OrderHasActiveException, InsufficientStockException,
    PromoCodeInvalidException, PromoCodeMinAmountException,
    InvalidStateTransitionException, OrderOwnershipViolationException
)


RATE_LIMIT_MINUTES = int(os.getenv('ORDER_RATE_LIMIT_MINUTES', '5'))


def check_rate_limit(db: Session, user_id: uuid.UUID, operation_type: OperationType):
    last_operation = db.query(UserOperation).filter(
        UserOperation.user_id == user_id,
        UserOperation.operation_type == operation_type
    ).order_by(UserOperation.created_at.desc()).first()

    if last_operation:
        time_diff = datetime.now() - last_operation.created_at
        if bool(time_diff < timedelta(minutes=RATE_LIMIT_MINUTES)):
            raise OrderLimitExceededException(
                details={
                    "retry_after_seconds": int((timedelta(minutes=RATE_LIMIT_MINUTES) - time_diff).total_seconds())
                }
            )


def check_active_orders(db: Session, user_id: uuid.UUID):
    active_order = db.query(Order).filter(
        Order.user_id == user_id,
        Order.status.in_([OrderStatus.CREATED, OrderStatus.PAYMENT_PENDING])
    ).first()

    if active_order:
        raise OrderHasActiveException(
            details={"active_order_id": str(active_order.id)}
        )


def validate_products(db: Session, items: List[dict]) -> List[Product]:
    products = []
    for item in items:
        product = db.query(Product).filter(Product.id == item['product_id']).first()
        if not product:
            raise ProductNotFoundException(str(item['product_id']))
        if bool(product.status != ProductStatus.ACTIVE):
            raise ProductInactiveException(str(item['product_id']))
        products.append(product)
    return products


def check_stock(products: List[Product], items: List[dict]):
    insufficient_items = []
    for product, item in zip(products, items):
        if product.stock < item['quantity']:
            insufficient_items.append({
                "product_id": str(product.id),
                "requested": item['quantity'],
                "available": product.stock
            })

    if insufficient_items:
        raise InsufficientStockException(
            details={"products": insufficient_items}
        )


def reserve_stock(db: Session, products: List[Product], items: List[dict]):
    for product, item in zip(products, items):
        product.stock -= item['quantity']
    db.flush()


def calculate_discount(promo_code: PromoCode, total_amount: Decimal) -> Decimal:
    if promo_code.discount_type == DiscountType.PERCENTAGE:  # type: ignore
        discount = total_amount * promo_code.discount_value / Decimal(100)  # type: ignore
        discount = min(discount, total_amount * Decimal('0.7'))
    else:
        discount = min(promo_code.discount_value, total_amount)  # type: ignore
    return discount  # type: ignore


def validate_and_apply_promo_code(
    db: Session,
    promo_code_str: Optional[str],
    total_amount: Decimal
) -> tuple[Optional[PromoCode], Decimal]:
    if not promo_code_str:
        return None, Decimal(0)

    promo_code = db.query(PromoCode).filter(PromoCode.code == promo_code_str).first()

    if not promo_code:
        raise PromoCodeInvalidException(promo_code_str, "not found")

    if not promo_code.active:  # type: ignore
        raise PromoCodeInvalidException(promo_code_str, "inactive")

    if promo_code.current_uses >= promo_code.max_uses:  # type: ignore
        raise PromoCodeInvalidException(promo_code_str, "usage limit exceeded")

    now = datetime.now(timezone.utc)
    valid_from = promo_code.valid_from.replace(tzinfo=timezone.utc)  # type: ignore
    valid_until = promo_code.valid_until.replace(tzinfo=timezone.utc)  # type: ignore
    
    if now < valid_from:  # type: ignore
        raise PromoCodeInvalidException(promo_code_str, "not yet valid")

    if now > valid_until:  # type: ignore
        raise PromoCodeInvalidException(promo_code_str, "expired")

    if total_amount < promo_code.min_order_amount:  # type: ignore
        raise PromoCodeMinAmountException(
            float(promo_code.min_order_amount),  # type: ignore
            float(total_amount),
            details={
                "promo_code": promo_code_str,
                "min_amount": float(promo_code.min_order_amount),  # type: ignore
                "current_amount": float(total_amount)
            }
        )

    discount = calculate_discount(promo_code, total_amount)

    promo_code.current_uses += 1  # type: ignore
    db.flush()

    return promo_code, discount  # type: ignore


def create_order(db: Session, user_id: uuid.UUID, items_data: List[dict], promo_code_str: Optional[str]) -> Order:
    check_rate_limit(db, user_id, OperationType.CREATE_ORDER)
    check_active_orders(db, user_id)

    products = validate_products(db, items_data)
    check_stock(products, items_data)
    reserve_stock(db, products, items_data)

    total_amount = sum(
        product.price * Decimal(item['quantity'])
        for product, item in zip(products, items_data)
    )

    promo_code, discount = validate_and_apply_promo_code(db, promo_code_str, total_amount)  # type: ignore

    order = Order(
        user_id=user_id,
        status=OrderStatus.CREATED,
        promo_code_id=promo_code.id if promo_code else None,
        total_amount=total_amount - discount,
        discount_amount=discount
    )
    db.add(order)
    db.flush()

    for product, item in zip(products, items_data):
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item['quantity'],
            price_at_order=product.price
        )
        db.add(order_item)

    user_operation = UserOperation(
        user_id=user_id,
        operation_type=OperationType.CREATE_ORDER
    )
    db.add(user_operation)

    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: uuid.UUID) -> Optional[Order]:
    return db.query(Order).filter(Order.id == order_id).first()


def update_order(db: Session, order_id: uuid.UUID, user_id: uuid.UUID, items_data: List[dict], promo_code_str: Optional[str] = None) -> Order:
    order = get_order(db, order_id)
    if not order:
        raise OrderNotFoundException(str(order_id))

    if order.user_id != user_id:  # type: ignore
        raise OrderOwnershipViolationException(str(order_id))

    if order.status != OrderStatus.CREATED:  # type: ignore
        raise InvalidStateTransitionException(
            order.status.value,
            "update",
            details={"message": "Order can only be updated in CREATED state"}
        )

    check_rate_limit(db, user_id, OperationType.UPDATE_ORDER)

    # Return stock from old items
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity

    # Decrement old promo code usage if it exists
    if order.promo_code_id:  # type: ignore
        old_promo = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if old_promo:
            old_promo.current_uses -= 1  # type: ignore

    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
    db.flush()

    products = validate_products(db, items_data)
    check_stock(products, items_data)
    reserve_stock(db, products, items_data)

    total_amount = sum(
        product.price * Decimal(item['quantity'])
        for product, item in zip(products, items_data)
    )

    # Apply new promo code if provided, otherwise keep the old one
    promo_code = None
    discount = Decimal(0)
    
    # Use new promo code if provided, otherwise try to reuse the old one
    if promo_code_str is not None:
        # New promo code provided (could be empty string to remove promo code)
        if promo_code_str:
            promo_code, discount = validate_and_apply_promo_code(db, promo_code_str, total_amount)  # type: ignore
            order.promo_code_id = promo_code.id if promo_code else None  # type: ignore
        else:
            # Empty string means remove promo code
            order.promo_code_id = None  # type: ignore
    elif order.promo_code_id:  # type: ignore
        # No new promo code provided, try to reuse the old one
        promo_code = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if promo_code:
            # Re-validate and apply the old promo code
            try:
                promo_code, discount = validate_and_apply_promo_code(db, promo_code.code, total_amount)  # type: ignore
                order.promo_code_id = promo_code.id if promo_code else None  # type: ignore
            except Exception:
                # If old promo code is no longer valid, remove it
                order.promo_code_id = None  # type: ignore

    order.total_amount = total_amount - discount  # type: ignore
    order.discount_amount = discount  # type: ignore

    for product, item in zip(products, items_data):
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item['quantity'],
            price_at_order=product.price
        )
        db.add(order_item)

    user_operation = UserOperation(
        user_id=user_id,
        operation_type=OperationType.UPDATE_ORDER
    )
    db.add(user_operation)

    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order_id: uuid.UUID, user_id: uuid.UUID) -> Order:
    order = get_order(db, order_id)
    if not order:
        raise OrderNotFoundException(str(order_id))

    if order.user_id != user_id:  # type: ignore
        raise OrderOwnershipViolationException(str(order_id))

    if order.status not in [OrderStatus.CREATED, OrderStatus.PAYMENT_PENDING]:
        raise InvalidStateTransitionException(
            order.status.value,
            OrderStatus.CANCELED.value,
            details={"message": "Order can only be canceled from CREATED or PAYMENT_PENDING state"}
        )

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity

    if order.promo_code_id:  # type: ignore
        promo_code = db.query(PromoCode).filter(PromoCode.id == order.promo_code_id).first()
        if promo_code:
            promo_code.current_uses -= 1  # type: ignore

    order.status = OrderStatus.CANCELED  # type: ignore

    db.commit()
    db.refresh(order)
    return order
