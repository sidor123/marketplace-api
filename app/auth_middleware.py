from functools import wraps
from flask import request, g

from app.database import get_db
from app.auth_service import get_user_from_token, TokenInvalidException, AccessDeniedException


def get_token_from_header() -> str:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise TokenInvalidException()
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise TokenInvalidException()
    
    return parts[1]


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_header()
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            user = get_user_from_token(db, token)
            g.user = user
            g.user_id = user.id
            g.user_role = user.role.value
            return f(*args, **kwargs)
        finally:
            db.close()
    
    return decorated_function


def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = get_token_from_header()
            
            db_gen = get_db()
            db = next(db_gen)
            try:
                user = get_user_from_token(db, token)
                g.user = user
                g.user_id = user.id
                g.user_role = user.role.value
                
                # Check if user has required role
                if user.role.value not in allowed_roles:
                    raise AccessDeniedException(
                        details={
                            "required_roles": list(allowed_roles),
                            "user_role": user.role.value
                        }
                    )
                
                return f(*args, **kwargs)
            finally:
                db.close()
        
        return decorated_function
    return decorator


# optional auth (sets g.user if token present, otherwise works without it)
def optional_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_header()
            db_gen = get_db()
            db = next(db_gen)
            try:
                user = get_user_from_token(db, token)
                g.user = user
                g.user_id = user.id
                g.user_role = user.role.value
            finally:
                db.close()
        except:
            g.user = None
            g.user_id = None
            g.user_role = None
        
        return f(*args, **kwargs)
    
    return decorated_function
