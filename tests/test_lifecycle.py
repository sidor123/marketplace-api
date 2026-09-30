import concurrent.futures
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid


class LifecycleTests(unittest.TestCase):
    def test_sigterm_finishes_inflight_request_and_restart_preserves_data(self):
        if not os.environ.get('TEST_DATABASE_URL'):
            self.fail('Set TEST_DATABASE_URL to a disposable PostgreSQL database')
        os.environ['DATABASE_URL'] = os.environ['TEST_DATABASE_URL']
        from app.database import engine
        from app.migrate import migrate
        from sqlalchemy import text
        migrate()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, PORT=str(port), WEB_CONCURRENCY='2',
                   JWT_SECRET_KEY='lifecycle-test-key-only-not-for-deployment')
        root = Path(__file__).resolve().parent.parent
        process = None

        def request(path, payload=None, token=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            data = json.dumps(payload).encode() if payload is not None else None
            with urllib.request.urlopen(urllib.request.Request(base + path, data=data, headers=headers), timeout=20) as response:
                return response.status, json.load(response)

        with tempfile.TemporaryFile() as logs:
            def start():
                server = subprocess.Popen([sys.executable, '-m', 'gunicorn', '--config', 'gunicorn.conf.py',
                                           '--bind', f'127.0.0.1:{port}', 'app.main:app'], cwd=root,
                                          env=env, stdout=logs, stderr=logs)
                started = time.monotonic()
                while time.monotonic() - started < 15:
                    if server.poll() is not None:
                        self.fail('Gunicorn exited before becoming ready')
                    try:
                        if request('/health/ready')[0] == 200:
                            return server
                    except OSError:
                        time.sleep(0.1)
                server.terminate()
                server.wait(timeout=30)
                self.fail('Gunicorn startup exceeded 15 seconds')

            try:
                process = start()
                _, user = request('/auth/register', {'email': f'{uuid.uuid4().hex}@example.com',
                                                    'password': 'lifecycle-test-123', 'role': 'SELLER'})
                _, product = request('/products', {'name': 'Persists across restart', 'price': '10.25',
                                                  'stock': 1, 'category': 'Test', 'status': 'ACTIVE'}, user['access_token'])
                path = '/products/' + product['id']
                with engine.connect() as blocker, concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    transaction = blocker.begin()
                    blocker.execute(text('LOCK TABLE products IN ACCESS EXCLUSIVE MODE'))
                    pending = executor.submit(request, path)
                    deadline = time.monotonic() + 5
                    blocked = False
                    while time.monotonic() < deadline:
                        blocker.execute(text('SELECT pg_stat_clear_snapshot()'))
                        blocked = bool(blocker.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND query LIKE '%products%' AND pid <> pg_backend_pid()")))
                        if blocked:
                            break
                        time.sleep(0.05)
                    try:
                        self.assertTrue(blocked, 'Expected an in-flight SQL request')
                        process.send_signal(signal.SIGTERM)
                        time.sleep(0.2)
                    finally:
                        transaction.rollback()
                    self.assertEqual(pending.result(timeout=15)[0], 200)
                self.assertEqual(process.wait(timeout=30), 0)
                process = start()
                status, restored = request(path)
                self.assertEqual(status, 200)
                self.assertEqual(restored['id'], product['id'])
                self.assertEqual(restored['price'], '10.25')
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=30)
                engine.dispose()
