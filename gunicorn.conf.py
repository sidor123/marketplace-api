import os

bind = f"0.0.0.0:{int(os.environ.get('PORT', '8000'))}"
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
worker_class = 'gthread'
threads = int(os.environ.get('WEB_THREADS', '4'))
timeout = 30
graceful_timeout = 25
accesslog = None
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
capture_output = True
worker_tmp_dir = '/tmp'
