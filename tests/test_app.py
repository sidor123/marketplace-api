import os
import unittest
import uuid
from decimal import Decimal

if not os.environ.get('TEST_DATABASE_URL'):
    raise RuntimeError('Set TEST_DATABASE_URL to a disposable PostgreSQL database')
os.environ['DATABASE_URL'] = os.environ['TEST_DATABASE_URL']
os.environ.setdefault('JWT_SECRET_KEY', 'integration-test-secret-not-for-deployment-1234')

from sqlalchemy import text
from app.main import app
from app.database import engine
from app.migrate import migrate


class MarketplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migrate()
        app.config['TESTING'] = True

    @classmethod
    def tearDownClass(cls):
        engine.dispose()

    def setUp(self):
        self.client = app.test_client()
        self.email = f'test-{uuid.uuid4().hex}@example.com'
        self.password = 'test-password-123'
        response = self.client.post('/auth/register', json={
            'email': self.email, 'password': self.password, 'role': 'SELLER'})
        self.assertEqual(response.status_code, 201, response.json)
        self.auth = response.json
        self.headers = {'Authorization': f"Bearer {self.auth['access_token']}"}

    def product(self, **overrides):
        data = dict(name='Настольная лампа', description='Для рабочего стола', price='1499.95',
                    stock=10, category='Дом', status='ACTIVE')
        data.update(overrides)
        response = self.client.post('/products', json=data, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.json)
        return response.json

    def test_product_crud_and_persistence(self):
        product = self.product()
        path = '/products/' + product['id']
        self.assertEqual(product['seller_id'], self.auth['user']['id'])
        self.assertEqual(self.client.get(path).json['name'], 'Настольная лампа')
        response = self.client.put(path, json={'price': '1999.99', 'stock': 7}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.json)
        engine.dispose()
        self.assertEqual(Decimal(self.client.get(path).json['price']), Decimal('1999.99'))
        self.assertEqual(self.client.delete(path, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get(path).json['status'], 'ARCHIVED')
        self.assertEqual(self.client.delete(path, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.put(path, json={'status': 'ACTIVE'}, headers=self.headers).status_code, 200)

    def test_authentication_and_ownership(self):
        product = self.product()
        path = '/products/' + product['id']
        self.assertEqual(self.client.delete(path).status_code, 401)
        other = self.client.post('/auth/register', json={'email': f'{uuid.uuid4().hex}@example.com',
                                'password': self.password, 'role': 'SELLER'}).json
        headers = {'Authorization': f"Bearer {other['access_token']}"}
        self.assertEqual(self.client.put(path, json={'stock': 0}, headers=headers).status_code, 403)
        self.assertEqual(self.client.delete(path, headers=headers).status_code, 403)
        denied = self.client.post('/auth/register', json={'email': f'{uuid.uuid4().hex}@example.com',
                                  'password': self.password, 'role': 'ADMIN'})
        self.assertEqual(denied.status_code, 403)
        login = self.client.post('/auth/login', json={'email': self.email, 'password': self.password})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.post('/auth/login', json={'email': self.email, 'password': 'wrong'}).status_code, 401)
        refresh = self.client.post('/auth/refresh', json={'refresh_token': login.json['refresh_token']})
        self.assertEqual(refresh.status_code, 200)
        self.assertEqual(self.client.post('/auth/refresh', json={'refresh_token': login.json['access_token']}).status_code, 401)

    def test_validation_and_pagination(self):
        product = self.product()
        for payload in [[], None, 'string']:
            response = self.client.post('/products', data=__import__('json').dumps(payload), content_type='application/json', headers=self.headers)
            self.assertEqual(response.status_code, 400, response.json)
        self.assertEqual(self.client.post('/products', data='{', content_type='application/json', headers=self.headers).status_code, 400)
        for payload in [{'price': 0}, {'stock': -1}, {'name': None}, {'status': None}]:
            response = self.client.put('/products/' + product['id'], json=payload, headers=self.headers)
            self.assertEqual(response.status_code, 400, response.json)
        for query in ['page=bad', 'page=-1', 'size=101', 'status=bad']:
            self.assertEqual(self.client.get('/products?' + query).status_code, 400)
        self.assertEqual(self.client.get('/products/not-a-uuid').status_code, 400)
        self.assertEqual(self.client.get('/products/' + str(uuid.uuid4())).status_code, 404)
        first = self.client.get('/products?size=1').json
        second = self.client.get('/products?size=1&page=1').json
        self.assertLessEqual(len(first['items']), 1)
        if second['items']:
            self.assertNotEqual(first['items'][0]['id'], second['items'][0]['id'])

    def test_login_rejects_passwords_longer_than_bcrypt_limit(self):
        for password in ('a' * 72, 'я' * 36):
            with self.subTest(password_bytes=len(password.encode('utf-8'))):
                email = f'{uuid.uuid4().hex}@example.com'
                registered = self.client.post('/auth/register', json={
                    'email': email, 'password': password})
                self.assertEqual(registered.status_code, 201, registered.json)
                login = self.client.post('/auth/login', json={
                    'email': email, 'password': password})
                self.assertEqual(login.status_code, 200, login.json)
                wrong = self.client.post('/auth/login', json={
                    'email': email, 'password': password + 'wrong'})
                self.assertEqual(wrong.status_code, 401, wrong.json)

    def test_authentication_releases_connection_before_handler(self):
        from flask import g
        from app.auth_middleware import require_role

        @require_role('SELLER')
        def handler():
            self.assertEqual(engine.pool.checkedout(), 0)
            self.assertEqual(str(g.user.id), self.auth['user']['id'])
            return 'ok'

        with app.test_request_context(headers=self.headers):
            self.assertEqual(handler(), 'ok')

    def test_response_serialization_does_not_modify_models(self):
        from app.database import SessionLocal
        from app.models import Product, Order, OrderStatus, PromoCode
        from app.schemas import ProductResponse, OrderResponse
        from datetime import datetime, timezone

        product = self.product()
        with SessionLocal() as db:
            stored = db.get(Product, uuid.UUID(product['id']))
            response = ProductResponse.model_validate(stored)
            self.assertEqual(response.created_at.tzinfo, timezone.utc)
            self.assertIsNone(stored.created_at.tzinfo)
            self.assertNotIn(stored, db.dirty)

        timestamp = datetime(2026, 1, 1)
        order = Order(id=uuid.uuid4(), user_id=uuid.uuid4(), status=OrderStatus.CREATED,
                      total_amount=Decimal('90'), discount_amount=Decimal('10'), items=[],
                      created_at=timestamp, updated_at=timestamp)
        for promo in (None, PromoCode(code='SAVE10')):
            with self.subTest(promo=promo):
                order.promo_code = promo
                response = OrderResponse.model_validate(order)
                self.assertEqual(response.promo_code, promo.code if promo else None)
                self.assertEqual(response.created_at.tzinfo, timezone.utc)
                self.assertIsNone(order.created_at.tzinfo)
                self.assertIsNone(order.updated_at.tzinfo)

    def test_frontend_and_health(self):
        response = self.client.get('/')
        self.assertIn('text/html', response.content_type)
        self.assertIn('Каталог', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)
        self.assertEqual(self.client.get('/static/style.css').status_code, 200)
        self.assertEqual(self.client.get('/health/live').status_code, 200)
        self.assertEqual(self.client.get('/health/ready').status_code, 200)
        self.assertIn('X-Request-Id', response.headers)

    def test_request_logs_do_not_contain_credentials(self):
        with self.assertLogs('api_logger', level='INFO') as captured:
            self.client.post('/auth/refresh', json={'refresh_token': self.auth['refresh_token']})
            self.client.post('/auth/login', json={'email': self.email, 'password': self.password})
        logs = '\n'.join(captured.output)
        self.assertNotIn(self.password, logs)
        self.assertNotIn(self.auth['refresh_token'], logs)
        self.assertIn('duration_ms', logs)

    def test_migrations_are_repeatable(self):
        migrate()
        with engine.connect() as conn:
            self.assertEqual(conn.scalar(text('SELECT count(*) FROM app_schema_migrations')), 3)

    def test_changed_migration_is_rejected(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        import app.migrate as runner
        with TemporaryDirectory() as directory:
            for source in runner.MIGRATIONS.glob('*.sql'):
                (Path(directory) / source.name).write_text(source.read_text() + '\n-- changed\n')
            with patch.object(runner, 'MIGRATIONS', Path(directory)):
                with self.assertRaisesRegex(RuntimeError, 'Applied migration changed'):
                    runner.migrate()
        migrate()

    def test_order_create_update_cancel(self):
        product = self.product()
        buyer = self.client.post('/auth/register', json={'email': f'{uuid.uuid4().hex}@example.com',
                                 'password': self.password, 'role': 'USER'}).json
        headers = {'Authorization': f"Bearer {buyer['access_token']}"}
        payload = {'items': [{'product_id': product['id'], 'quantity': 2}]}
        response = self.client.post('/orders', json=payload, headers=headers)
        self.assertEqual(response.status_code, 201, response.json)
        order_id = response.json['id']
        self.assertEqual(self.client.get('/products/' + product['id']).json['stock'], 8)
        payload['items'][0]['quantity'] = 3
        response = self.client.put('/orders/' + order_id, json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json['items'][0]['quantity'], 3)
        self.assertEqual(self.client.get('/orders/' + order_id, headers=headers).status_code, 200)
        response = self.client.post('/orders/' + order_id + '/cancel', headers=headers)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(self.client.get('/products/' + product['id']).json['stock'], 10)

    def test_order_failure_rolls_back_stock(self):
        product = self.product()
        buyer = self.client.post('/auth/register', json={'email': f'{uuid.uuid4().hex}@example.com',
                                 'password': self.password, 'role': 'USER'}).json
        headers = {'Authorization': f"Bearer {buyer['access_token']}"}
        response = self.client.post('/orders', json={'items': [{'product_id': product['id'], 'quantity': 2}],
                                                     'promo_code': 'INVALID'}, headers=headers)
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(self.client.get('/products/' + product['id']).json['stock'], 10)

    def test_concurrent_buyers_cannot_oversell(self):
        from concurrent.futures import ThreadPoolExecutor
        product = self.product(stock=1)
        tokens = []
        for _ in range(2):
            buyer = self.client.post('/auth/register', json={
                'email': f'{uuid.uuid4().hex}@example.com', 'password': self.password, 'role': 'USER'}).json
            tokens.append(buyer['access_token'])

        def buy(token):
            with app.test_client() as client:
                return client.post('/orders', json={'items': [{'product_id': product['id'], 'quantity': 1}]},
                                   headers={'Authorization': f'Bearer {token}'}).status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(buy, tokens))
        self.assertEqual(sorted(statuses), [201, 409])
        self.assertEqual(self.client.get('/products/' + product['id']).json['stock'], 0)


if __name__ == '__main__':
    unittest.main()
