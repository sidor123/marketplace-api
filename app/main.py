from flask import Flask, request, jsonify, g, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.exceptions import HTTPException
import os
from pydantic import ValidationError
import uuid

from app.database import get_db
from app.models import ProductStatus
from app import crud
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    OrderCreate, OrderUpdate, OrderResponse,
    UserRegister, UserLogin, RefreshTokenRequest,
    PromoCodeCreate, PromoCodeResponse
)
from app.exceptions import (
    APIException,
    ProductNotFoundException,
    ValidationException
)
from app import order_service
from app import auth_service
from app.auth_middleware import require_role
from app.logging_middleware import init_logging_middleware

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

init_logging_middleware(app)


@app.errorhandler(APIException)
def handle_api_exception(error: APIException):
    return jsonify(error.to_dict()), error.status_code


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error_code": "NOT_FOUND",
        "message": "Resource not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    import traceback
    import sys

    print(f"Internal error: {error}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    return jsonify({
        "error_code": "INTERNAL_ERROR",
        "message": "Internal server error"
    }), 500


def format_validation_errors(validation_error: ValidationError):
    errors = {}
    for error in validation_error.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        msg = error['msg']
        error_type = error['type']

        if error_type == 'string_too_short':
            msg = f"String should have at least {error.get('ctx', {}).get('min_length', 1)} characters"
        elif error_type == 'string_too_long':
            msg = f"String should have at most {error.get('ctx', {}).get('max_length', 0)} characters"
        elif error_type == 'greater_than':
            msg = f"Value should be greater than {error.get('ctx', {}).get('gt', 0)}"
        elif error_type == 'greater_than_equal':
            msg = f"Value should be greater than or equal to {error.get('ctx', {}).get('ge', 0)}"
        elif error_type == 'missing':
            msg = "Field required"

        errors[field] = msg

    return errors


@app.route('/')
def root():
    return render_template('index.html')


@app.route('/health/live')
def live():
    return jsonify(status='ok', release=os.environ.get('RELEASE_ID', 'local'))


@app.route('/health/ready')
def ready():
    try:
        from app.database import engine
        with engine.connect() as connection:
            connection.execute(text('SELECT id FROM products LIMIT 1'))
        return jsonify(status='ready')
    except SQLAlchemyError:
        return jsonify(status='unavailable'), 503


@app.before_request
def validate_json_object():
    if request.method in ('POST', 'PUT') and request.is_json:
        if not isinstance(request.get_json(), dict):
            raise ValidationException(message='JSON body must be an object')


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error_code=error.name.upper().replace(' ', '_'), message=error.description), error.code


@app.errorhandler(IntegrityError)
def integrity_error(error):
    return jsonify(error_code='CONFLICT', message='Data conflicts with database constraints'), 409

# ============= AUTH ENDPOINTS =============

# Register new user
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    try:
        validated_data = UserRegister(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )
    
    if validated_data.role and validated_data.role.value == 'ADMIN':
        raise auth_service.AccessDeniedException()

    db_gen = get_db()
    db = next(db_gen)
    try:
        user = auth_service.register_user(
            db,
            validated_data.email,
            validated_data.password,
            validated_data.role.value if validated_data.role else 'USER'
        )
        
        # Generate tokens
        access_token = auth_service.create_access_token(user.id, user.role.value)  # type: ignore
        refresh_token = auth_service.create_refresh_token(user.id)  # type: ignore
        
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value
            }
        }), 201
    finally:
        db.close()


@app.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return tokens"""
    data = request.get_json()
    
    try:
        validated_data = UserLogin(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        user = auth_service.authenticate_user(db, validated_data.email, validated_data.password)
        
        if not user:
            raise APIException(
                error_code="INVALID_CREDENTIALS",
                message="Invalid email or password",
                status_code=401
            )
        
        # Generate tokens
        access_token = auth_service.create_access_token(user.id, user.role.value)  # type: ignore
        refresh_token = auth_service.create_refresh_token(user.id)  # type: ignore
        
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value
            }
        })
    finally:
        db.close()


@app.route('/auth/refresh', methods=['POST'])
def refresh():
    """Refresh access token using refresh token"""
    data = request.get_json()
    
    try:
        validated_data = RefreshTokenRequest(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        access_token, refresh_token = auth_service.refresh_access_token(
            db,
            validated_data.refresh_token
        )
        
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        })
    finally:
        db.close()

# ============= PRODUCT ENDPOINTS =============

# Create product
@app.route('/products', methods=['POST'])
@require_role('SELLER', 'ADMIN')
def create_product():
    data = request.get_json()

    try:
        validated_data = ProductCreate(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        product_data = validated_data.model_dump()
        if g.user_role == 'SELLER':
            product_data['seller_id'] = g.user_id
        elif g.user_role == 'ADMIN':
            # ADMIN can create products without seller_id or with specified seller_id
            product_data['seller_id'] = product_data.get('seller_id', None)
        
        product = crud.create_product(db, product_data)
        return jsonify(ProductResponse.model_validate(product).model_dump(mode='json')), 201
    finally:
        db.close()


# Get product by ID
@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise ValidationException(
            message="Invalid product ID format",
            details={"product_id": product_id}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        product = crud.get_product(db, product_uuid)
        if not product:
            raise ProductNotFoundException(product_id)
        return jsonify(ProductResponse.model_validate(product).model_dump(mode='json'))
    finally:
        db.close()


# Get all products (with filtration and pagination)
@app.route('/products', methods=['GET'])
def get_products():
    status = request.args.get('status', None)
    category = request.args.get('category', None)
    try:
        page = int(request.args.get('page', 0))
        size = int(request.args.get('size', 20))
        if page < 0 or not 1 <= size <= 100:
            raise ValueError
    except ValueError:
        raise ValidationException(message='page must be >= 0; size must be between 1 and 100')

    if status and status not in ['ACTIVE', 'INACTIVE', 'ARCHIVED']:
        raise ValidationException(
            message="Invalid status value",
            details={"status": status, "allowed_values": ["ACTIVE", "INACTIVE", "ARCHIVED"]}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        status_enum = ProductStatus[status] if status else None
        products, total = crud.get_products(db, page, size, status_enum, category)

        return jsonify({
            "items": [ProductResponse.model_validate(p).model_dump(mode='json') for p in products],
            "total_elements": total,
            "page": page,
            "size": size
        })
    finally:
        db.close()


# Update product
@app.route('/products/<product_id>', methods=['PUT'])
@require_role('SELLER', 'ADMIN')
def update_product(product_id):
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise ValidationException(
            message="Invalid product ID format",
            details={"fields": {"id": "Invalid UUID format"}}
        )

    data = request.get_json()

    try:
        validated_data = ProductUpdate(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        existing_product = crud.get_product(db, product_uuid)
        if not existing_product:
            raise ProductNotFoundException(product_id)
        
        if g.user_role == 'SELLER':
            if existing_product.seller_id != g.user_id:
                raise auth_service.AccessDeniedException(
                    details={"message": "You can only update your own products"}
                )
        
        product = crud.update_product(db, product_uuid, validated_data.model_dump(exclude_unset=True))
        return jsonify(ProductResponse.model_validate(product).model_dump(mode='json'))
    finally:
        db.close()


# Delete product (set to archived)
@app.route('/products/<product_id>', methods=['DELETE'])
@require_role('SELLER', 'ADMIN')
def delete_product(product_id):
    try:
        product_uuid = uuid.UUID(product_id)
    except ValueError:
        raise ValidationException(
            message="Invalid product ID format",
            details={"fields": {"id": "Invalid UUID format"}}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        existing_product = crud.get_product(db, product_uuid)
        if not existing_product:
            raise ProductNotFoundException(product_id)
        
        if g.user_role == 'SELLER':
            if existing_product.seller_id != g.user_id:
                raise auth_service.AccessDeniedException(
                    details={"message": "You can only delete your own products"}
                )
        
        success = crud.delete_product(db, product_uuid)
        return '', 204
    finally:
        db.close()

# ============= ORDER ENDPOINTS =============

# Create (make) an order
@app.route('/orders', methods=['POST'])
@require_role('USER', 'ADMIN')
def create_order_endpoint():
    data = request.get_json()

    try:
        validated_data = OrderCreate(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        items_data = [item.model_dump() for item in validated_data.items]
        order = order_service.create_order(
            db,
            g.user_id,
            items_data,
            validated_data.promo_code
        )
        return jsonify(OrderResponse.model_validate(order).model_dump(mode='json')), 201
    finally:
        db.close()


# Get order info
@app.route('/orders/<order_id>', methods=['GET'])
@require_role('USER', 'ADMIN')
def get_order_endpoint(order_id):
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise ValidationException(
            message="Invalid order ID format",
            details={"order_id": order_id}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        order = order_service.get_order(db, order_uuid)
        if not order:
            from app.exceptions import OrderNotFoundException
            raise OrderNotFoundException(order_id)
        
        if g.user_role == 'USER' and order.user_id != g.user_id:
            from app.exceptions import OrderOwnershipViolationException
            raise OrderOwnershipViolationException(order_id)
        
        return jsonify(OrderResponse.model_validate(order).model_dump(mode='json'))
    finally:
        db.close()


# Update order
@app.route('/orders/<order_id>', methods=['PUT'])
@require_role('USER', 'ADMIN')
def update_order_endpoint(order_id):
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise ValidationException(
            message="Invalid order ID format",
            details={"fields": {"id": "Invalid UUID format"}}
        )

    data = request.get_json()

    try:
        validated_data = OrderUpdate(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )

    db_gen = get_db()
    db = next(db_gen)
    try:
        items_data = [item.model_dump() for item in validated_data.items]
        order = order_service.update_order(db, order_uuid, g.user_id, items_data, validated_data.promo_code)
        return jsonify(OrderResponse.model_validate(order).model_dump(mode='json'))
    finally:
        db.close()


# Cancel order
@app.route('/orders/<order_id>/cancel', methods=['POST'])
@require_role('USER', 'ADMIN')
def cancel_order_endpoint(order_id):
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise ValidationException(
            message="Invalid order ID format",
            details={"fields": {"id": "Invalid UUID format"}}
        )
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        order = order_service.cancel_order(db, order_uuid, g.user_id)
        return jsonify(OrderResponse.model_validate(order).model_dump(mode='json'))
    finally:
        db.close()

# ============= PROMO CODE ENDPOINTS =============

# Create promo code
@app.route('/promo-codes', methods=['POST'])
@require_role('SELLER', 'ADMIN')
def create_promo_code():
    data = request.get_json()
    
    try:
        validated_data = PromoCodeCreate(**data)
    except ValidationError as e:
        raise ValidationException(
            message="Validation failed",
            details={"fields": format_validation_errors(e)}
        )
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        promo_code_data = validated_data.model_dump()
        promo_code = crud.create_promo_code(db, promo_code_data)
        return jsonify(PromoCodeResponse.model_validate(promo_code).model_dump(mode='json')), 201
    finally:
        db.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8000')))
