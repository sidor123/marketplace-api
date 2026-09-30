import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import uuid
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.exceptions import APIException
from app.config import required, positive_int


SECRET_KEY = required('JWT_SECRET_KEY')
if len(SECRET_KEY) < 32:
    raise RuntimeError('JWT_SECRET_KEY must contain at least 32 characters')
ACCESS_TOKEN_EXPIRE_MINUTES = positive_int('ACCESS_TOKEN_EXPIRE_MINUTES', '30')
REFRESH_TOKEN_EXPIRE_DAYS = positive_int('REFRESH_TOKEN_EXPIRE_DAYS', '7')
ENCRYPTION_ALGORITHM = 'HS256'


class TokenExpiredException(APIException):
    def __init__(self):
        super().__init__(
            error_code="TOKEN_EXPIRED",
            message="Access token has expired",
            status_code=401
        )


class TokenInvalidException(APIException):
    def __init__(self):
        super().__init__(
            error_code="TOKEN_INVALID",
            message="Invalid access token",
            status_code=401
        )


class RefreshTokenInvalidException(APIException):
    def __init__(self):
        super().__init__(
            error_code="REFRESH_TOKEN_INVALID",
            message="Invalid or expired refresh token",
            status_code=401
        )


class AccessDeniedException(APIException):
    def __init__(self, details=None):
        super().__init__(
            error_code="ACCESS_DENIED",
            message="Access denied: insufficient permissions",
            status_code=403,
            details=details
        )


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    encoded_password = password.encode('utf-8')
    if len(encoded_password) > 72:
        return False
    return bcrypt.checkpw(encoded_password, password_hash.encode('utf-8'))


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    payload = {
        'user_id': str(user_id),
        'role': role,
        'type': 'access',
        'exp': datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ENCRYPTION_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> str:
    payload = {
        'user_id': str(user_id),
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ENCRYPTION_ALGORITHM)


def decode_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ENCRYPTION_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.InvalidTokenError:
        raise TokenInvalidException()


def register_user(db: Session, email: str, password: str, role: str = 'USER') -> User:
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise APIException(
            error_code="USER_ALREADY_EXISTS",
            message=f"User with email {email} already exists",
            status_code=409
        )
    
    try:
        user_role = UserRole[role]
    except KeyError:
        raise APIException(
            error_code="VALIDATION_ERROR",
            message=f"Invalid role: {role}",
            status_code=400
        )
    
    password_hash = hash_password(password)
    user = User(
        email=email,
        password_hash=password_hash,
        role=user_role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    if not verify_password(password, user.password_hash): # type: ignore
        return None
    
    return user


def get_user_from_token(db: Session, token: str) -> User:
    payload = decode_token(token)
    
    if payload.get('type') != 'access':
        raise TokenInvalidException()
    
    user_id = uuid.UUID(payload['user_id'])
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise TokenInvalidException()
    
    return user


def refresh_access_token(db: Session, refresh_token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ENCRYPTION_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise RefreshTokenInvalidException()
    except jwt.InvalidTokenError:
        raise RefreshTokenInvalidException()
    
    if payload.get('type') != 'refresh':
        raise RefreshTokenInvalidException()
    
    user_id = uuid.UUID(payload['user_id'])
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise RefreshTokenInvalidException()
    
    new_access_token = create_access_token(user.id, user.role.value) # type: ignore
    new_refresh_token = create_refresh_token(user.id) # type: ignore
    
    return new_access_token, new_refresh_token
