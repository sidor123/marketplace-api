import json
import time
import uuid
from datetime import datetime
from flask import request, g
from functools import wraps
import logging
import sys

logger = logging.getLogger('api_logger')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


def mask_sensitive_data(data):
    if not isinstance(data, dict):
        return data
    
    masked_data = data.copy()
    sensitive_fields = ['password', 'token', 'secret', 'api_key']
    
    for field in sensitive_fields:
        if field in masked_data:
            masked_data[field] = '***MASK***'
    
    return masked_data


def log_request():
    request_id = str(uuid.uuid4())
    g.request_id = request_id
    g.start_time = time.time()
    
    g.request_id_header = request_id


def log_response(response):
    duration_ms = int((time.time() - g.start_time) * 1000)
    
    user_id = getattr(g, 'user_id', None)
    
    log_entry = {
        "request_id": g.request_id,
        "method": request.method,
        "endpoint": request.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "user_id": str(user_id) if user_id else None,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    if request.method in ['POST', 'PUT', 'DELETE']:
        if request.is_json:
            try:
                request_body = request.get_json()
                log_entry["request_body"] = mask_sensitive_data(request_body)
            except Exception:
                pass
    
    logger.info(json.dumps(log_entry))
    
    response.headers['X-Request-Id'] = g.request_id
    
    return response


def init_logging_middleware(app):
    @app.before_request
    def before_request():
        log_request()
    
    @app.after_request
    def after_request(response):
        return log_response(response)
