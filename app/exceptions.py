from typing import Optional, Dict, Any


class APIException(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error_code": self.error_code,
            "message": self.message
        }
        if self.details is not None:
            result["details"] = self.details # type: ignore
        return result


class ProductNotFoundException(APIException):
    def __init__(self, product_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="PRODUCT_NOT_FOUND",
            message=f"Product with id {product_id} not found",
            status_code=404,
            details=details
        )


class ProductInactiveException(APIException):
    def __init__(self, product_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="PRODUCT_INACTIVE",
            message=f"Product with id {product_id} is not active",
            status_code=409,
            details=details
        )


class OrderNotFoundException(APIException):
    def __init__(self, order_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="ORDER_NOT_FOUND",
            message=f"Order with id {order_id} not found",
            status_code=404,
            details=details
        )


class OrderLimitExceededException(APIException):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="ORDER_LIMIT_EXCEEDED",
            message="Order creation or update rate limit exceeded. Please try again later.",
            status_code=429,
            details=details
        )


class OrderHasActiveException(APIException):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="ORDER_HAS_ACTIVE",
            message="User already has an active order. Complete or cancel it before creating a new one.",
            status_code=409,
            details=details
        )


class InvalidStateTransitionException(APIException):
    def __init__(self, current_state: str, target_state: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="INVALID_STATE_TRANSITION",
            message=f"Invalid state transition from {current_state} to {target_state}",
            status_code=409,
            details=details
        )


class InsufficientStockException(APIException):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="INSUFFICIENT_STOCK",
            message="Insufficient stock for one or more products",
            status_code=409,
            details=details
        )


class PromoCodeInvalidException(APIException):
    def __init__(self, promo_code: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="PROMO_CODE_INVALID",
            message=f"Promo code '{promo_code}' is invalid: {reason}",
            status_code=422,
            details=details
        )


class PromoCodeMinAmountException(APIException):
    def __init__(self, min_amount: float, current_amount: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="PROMO_CODE_MIN_AMOUNT",
            message=f"Order amount {current_amount} is below minimum required amount {min_amount} for promo code",
            status_code=422,
            details=details
        )


class OrderOwnershipViolationException(APIException):
    def __init__(self, order_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="ORDER_OWNERSHIP_VIOLATION",
            message=f"Order {order_id} belongs to another user",
            status_code=403,
            details=details
        )


class ValidationException(APIException):
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details
        )
