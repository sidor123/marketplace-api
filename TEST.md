curl -X 'POST' \
  'http://localhost:8000/auth/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "password": "password",
  "role": "USER"
}'

curl -X 'POST' \
  'http://localhost:8000/auth/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "seller@example.com",
  "password": "password",
  "role": "SELLER"
}'

curl -X POST "http://localhost:8000/products" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Ноутбук",
    "description": "Игровой ноутбук",
    "price": 89990.50,
    "stock": 10,
    "category": "Электроника",
    "status": "ACTIVE"
  }'

curl -X 'GET' \
  'http://localhost:8000/products?page=0&size=20' \
  -H 'accept: application/json'

curl -X 'GET' \
  'http://localhost:8000/products/?id=f38cb6e0-9327-43a3-8d7c-93ffc006ed37' \
  -H 'accept: application/json'

curl -X PUT "http://localhost:8000/products/{product_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "price": 79990.00,
    "stock": 5
  }'

curl -X DELETE "http://localhost:8000/products/{product_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

curl -X POST "http://localhost:8000/promo-codes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "code": "SAVE20",
    "discount_type": "PERCENTAGE",
    "discount_value": 20,
    "min_order_amount": 100,
    "max_uses": 100,
    "valid_from": "2024-01-01T00:00:00Z",
    "valid_until": "2028-12-31T23:59:59Z"
  }'

curl -X 'POST' \
  'http://localhost:8000/orders' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
  "items": [
    {
      "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "quantity": 1
    }
  ],
  "promo_code": "SAVE20"
}'

curl -X 'GET' \
  'http://localhost:8000/orders/{order_id}' \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

curl -X 'PUT' \
  'http://localhost:8000/orders/{order_id}' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
  "items": [
    {
      "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "quantity": 3
    }
  ],
  "promo_code": "SAVE20"
}'

curl -X 'POST' \
  'http://localhost:8000/orders/{order_id}/cancel' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"