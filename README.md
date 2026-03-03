# Marketplace API - Домашнее задание №2

Учебный проект API маркетплейса для курса "Архитектура микросервисов".

## Реализованные пункты

- ✅ **Пункт 1 (1 балл)**: OpenAPI-спецификация CRUD для сущности Product
- ✅ **Пункт 2 (1 балл)**: Описание схем данных в OpenAPI
- ✅ **Пункт 3 (1 балл)**: Кодогенерация из OpenAPI (используются Pydantic модели)
- ✅ **Пункт 4 (1 балл)**: PostgreSQL + базовый CRUD с миграциями Flyway
- ✅ **Пункт 5 (1 балл)**: Контрактная обработка ошибок
- ✅ **Пункт 6 (1 балл)**: Контрактная валидация входных данных
- ✅ **Пункт 7 (1 балл)**: Сложная бизнес-логика для заказов
- ✅ **Пункт 8 (1 балл)**: Логирование API в JSON формате
- ✅ **Пункт 9 (1 балл)**: JWT-авторизация с access и refresh токенами
- ✅ **Пункт 10 (1 балл)**: Ролевая модель доступа (USER, SELLER, ADMIN)

**Итого: 10 баллов**

## Технологии

- **Python 3.11+** (работает и с 3.14)
- **Flask** - веб-фреймворк
- **SQLAlchemy** - ORM
- **Flyway** - миграции БД
- **PostgreSQL** - база данных
- **Pydantic** - валидация данных
- **Docker Compose** - для запуска PostgreSQL
- **PyJWT** - JWT токены для авторизации
- **bcrypt** - хеширование паролей

## Структура проекта

```
marketplace-api/
├── openapi/
│   └── products.yaml          # OpenAPI спецификация
├── db/
│   └── migration/             # Flyway миграции
│       ├── V1__create_products_table.sql
│       ├── V2__create_orders_tables.sql
│       └── V3__create_users_table.sql
├── app/
│   ├── __init__.py
│   ├── main.py                # Flask приложение и роуты
│   ├── database.py            # Настройка БД
│   ├── models.py              # SQLAlchemy модели
│   ├── schemas.py             # Pydantic схемы
│   ├── crud.py                # CRUD операции для Products
│   ├── order_service.py       # Бизнес-логика заказов
│   ├── auth_service.py        # JWT и аутентификация
│   ├── auth_middleware.py     # Декораторы авторизации
│   ├── logging_middleware.py  # Логирование запросов
│   └── exceptions.py          # Кастомные исключения
├── docker-compose.yml         # PostgreSQL контейнер
├── flyway.conf                # Конфигурация Flyway
├── requirements.txt           # Зависимости Python
├── Makefile                   # Команды для сборки и запуска
└── README.md
```

## Быстрый старт

### Предварительные требования

- Python 3.11+
- Docker и Docker Compose (или Colima на macOS)
- Flyway (для миграций БД)

**Важно**: Если у вас на хосте уже запущен PostgreSQL на порту 5432, проект использует порт **5433** для Docker контейнера, чтобы избежать конфликтов.

### 1. Настройка переменных окружения

Создайте файл `.env` в корне проекта (если его нет):

```bash
echo "DATABASE_URL=postgresql://marketplace:marketplace123@localhost:5433/marketplace" > .env
```

**Важно**: Убедитесь, что в `.env` указан порт **5433**, а не 5432!

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Запуск Docker (если используете Colima на macOS)

```bash
colima start
```

### 4. Запуск PostgreSQL

```bash
docker-compose up -d
```

Контейнер будет доступен на порту **5433** (не 5432!).

### 5. Установка Flyway

**macOS (Homebrew):**
```bash
brew install flyway
```

**Linux/Windows:**
Скачайте с https://flywaydb.org/download

### 6. Применение миграций

```bash
make migrate
```

Или напрямую:
```bash
flyway -configFiles=flyway.conf migrate
```

### 7. Запуск приложения

```bash
make run
```

Или напрямую:
```bash
python3 -m flask --app app.main run --host 0.0.0.0 --port 8000 --reload
```

Приложение будет доступно по адресу: http://localhost:8000

## Использование Makefile

Для удобства можно использовать Makefile:

```bash
# Полная установка и настройка (установка зависимостей + запуск БД + миграции)
make setup

# Запуск приложения
make run

# Применение миграций
make migrate

# Проверка статуса миграций
make migrate-info

# Запуск PostgreSQL
make docker-up

# Остановка PostgreSQL (контейнер остановлен, данные сохранены)
make docker-down

# Остановка PostgreSQL с удалением всех данных
docker-compose down -v
```

## Завершение работы

### Остановка приложения

Нажмите `Ctrl+C` в терминале, где запущено приложение Flask.

### Остановка PostgreSQL

```bash
# Остановить контейнер (данные сохраняются)
make docker-down
# или
docker-compose down

# Остановить контейнер и удалить все данные
docker-compose down -v
```

### Остановка Docker (если используете Colima на macOS)

```bash
colima stop
```

### Полная очистка

Если нужно полностью очистить проект и начать заново:

```bash
# 1. Остановить и удалить контейнеры с данными
docker-compose down -v

# 2. Удалить образы (опционально)
docker rmi postgres:15-alpine

# 3. Остановить Colima (macOS)
colima stop

# 4. Удалить виртуальное окружение Python (если создавали)
rm -rf venv/
```

## Новые возможности (Пункты 8-10)

### 🔐 Аутентификация и Авторизация

Реализована полная система JWT-авторизации с ролевым доступом:

- **3 роли**: USER (покупатель), SELLER (продавец), ADMIN (администратор)
- **JWT токены**: Access token (30 мин) и Refresh token (7 дней)
- **Защищенные эндпоинты**: Все операции требуют авторизации (кроме просмотра товаров)

**Новые эндпоинты:**
- `POST /auth/register` - Регистрация пользователя
- `POST /auth/login` - Вход и получение токенов
- `POST /auth/refresh` - Обновление access token

**Матрица доступа:**
- USER: может создавать и управлять своими заказами
- SELLER: может создавать и управлять своими товарами, создавать промокоды
- ADMIN: полный доступ ко всем ресурсам

Подробнее: [`AUTH_AND_LOGGING.md`](AUTH_AND_LOGGING.md)

### 📊 Логирование API

Все запросы логируются в JSON формате:

```json
{
  "request_id": "uuid",
  "method": "POST",
  "endpoint": "/orders",
  "status_code": 201,
  "duration_ms": 145,
  "user_id": "user-uuid",
  "timestamp": "2024-01-15T10:30:45Z",
  "request_body": {...}
}
```

- Уникальный `request_id` для каждого запроса
- Автоматическое маскирование паролей
- Заголовок `X-Request-Id` в ответах
- Логирование тела запроса для POST/PUT/DELETE

### 🛒 Бизнес-логика заказов

Полная реализация сложной логики:

- Rate limiting (ограничение частоты операций)
- Проверка активных заказов
- Резервирование товаров
- Промокоды с валидацией
- Снапшот цен
- Возврат товаров при отмене

## API Endpoints

### Authentication

| Метод  | Endpoint         | Описание                    | Роли      |
|--------|------------------|-----------------------------|-----------|
| `POST` | `/auth/register` | Регистрация пользователя    | Public    |
| `POST` | `/auth/login`    | Вход и получение токенов    | Public    |
| `POST` | `/auth/refresh`  | Обновление access token     | Public    |

### Products

| Метод    | Endpoint         | Описание                                      | Роли           |
|----------|------------------|-----------------------------------------------|----------------|
| `POST`   | `/products`      | Создание товара                               | SELLER, ADMIN  |
| `GET`    | `/products/{id}` | Получение товара по ID                        | Public         |
| `GET`    | `/products`      | Список товаров с пагинацией и фильтрацией     | Public         |
| `PUT`    | `/products/{id}` | Обновление товара                             | SELLER*, ADMIN |
| `DELETE` | `/products/{id}` | Мягкое удаление (перевод в статус `ARCHIVED`) | SELLER*, ADMIN |

*SELLER может управлять только своими товарами

### Orders

| Метод  | Endpoint                | Описание          | Роли        |
|--------|-------------------------|-------------------|-------------|
| `POST` | `/orders`               | Создание заказа   | USER, ADMIN |
| `GET`  | `/orders/{id}`          | Получение заказа  | USER*, ADMIN |
| `PUT`  | `/orders/{id}`          | Обновление заказа | USER*, ADMIN |
| `POST` | `/orders/{id}/cancel`   | Отмена заказа     | USER*, ADMIN |

*USER может управлять только своими заказами

### Promo Codes

| Метод  | Endpoint        | Описание              | Роли          |
|--------|-----------------|-----------------------|---------------|
| `POST` | `/promo-codes`  | Создание промокода    | SELLER, ADMIN |

### Примеры запросов

#### Регистрация и вход

**Регистрация:**
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "securepass123",
    "role": "SELLER"
  }'
```

**Вход:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "securepass123"
  }'
```

Сохраните `access_token` из ответа для использования в других запросах.

#### Создание товара (требуется авторизация)

```bash
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
```

#### Получение списка товаров

```bash
# Все товары (первая страница)
curl "http://localhost:8000/products"

# С фильтрацией по статусу
curl "http://localhost:8000/products?status=ACTIVE"

# С фильтрацией по категории
curl "http://localhost:8000/products?category=Электроника"

# С пагинацией
curl "http://localhost:8000/products?page=0&size=10"
```

#### Получение товара по ID

```bash
curl "http://localhost:8000/products/{product_id}"
```

#### Обновление товара

```bash
curl -X PUT "http://localhost:8000/products/{product_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 79990.00,
    "stock": 5
  }'
```

#### Удаление товара (мягкое)

```bash
curl -X DELETE "http://localhost:8000/products/{product_id}"
```

## Схема данных Product

| Поле          | Тип      | Обязательно       | Описание                                    |
|---------------|----------|-------------------|---------------------------------------------|
| `id`          | UUID     | Только в response | Идентификатор товара                        |
| `name`        | string   | Да                | Название товара (1-255 символов)            |
| `description` | string   | Нет               | Описание товара (до 4000 символов)          |
| `price`       | decimal  | Да                | Цена товара (> 0)                           |
| `stock`       | integer  | Да                | Остаток на складе (>= 0)                    |
| `category`    | string   | Да                | Категория товара (1-100 символов)           |
| `status`      | enum     | Да                | Состояние: `ACTIVE`, `INACTIVE`, `ARCHIVED` |
| `created_at`  | datetime | Только в response | Время создания                              |
| `updated_at`  | datetime | Только в response | Время обновления                            |

## База данных

### Подключение к PostgreSQL

**Важно**: Проект использует порт **5433**, а не стандартный 5432!

```bash
# Через Docker exec (рекомендуется)
docker exec -it marketplace-db psql -U marketplace -d marketplace

# Или через psql на хосте (если установлен)
psql -h localhost -p 5433 -U marketplace -d marketplace

# Пароль: marketplace123
```

### Просмотр данных

```sql
-- Все товары
SELECT * FROM products;

-- Активные товары
SELECT * FROM products WHERE status = 'ACTIVE';

-- Товары по категории
SELECT * FROM products WHERE category = 'Электроника';
```

#### Создание заказа (требуется авторизация)

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "items": [
      {
        "product_id": "product-uuid",
        "quantity": 2
      }
    ],
    "promo_code": "SAVE20"
  }'
```

#### Создание промокода (SELLER или ADMIN)

```bash
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
    "valid_until": "2024-12-31T23:59:59Z"
  }'
```

## Особенности реализации

### 1. OpenAPI спецификация

- Полное описание всех эндпоинтов в `openapi/products.yaml`
- Отдельные схемы для создания (`ProductCreate`), обновления (`ProductUpdate`) и ответа (`ProductResponse`)
- Валидация на уровне спецификации (minLength, maxLength, minimum, format)

### 2. Валидация данных

- Используются Pydantic модели для валидации
- Схемы определены в `app/schemas.py` на основе OpenAPI спецификации
- Автоматическая валидация входных данных с детальными сообщениями об ошибках

### 3. База данных

- PostgreSQL с миграциями через **Flyway**
- Индекс на поле `status` для оптимизации фильтрации
- Автоматическое заполнение `created_at` при создании
- Ручное обновление `updated_at` при изменении записей
- Мягкое удаление через изменение статуса на `ARCHIVED`
- **Порт 5433** для избежания конфликтов с локальным PostgreSQL

### 4. CRUD операции

- Полная реализация Create, Read, Update, Delete
- Пагинация с параметрами `page` и `size`
- Фильтрация по `status` и `category`
- Обработка ошибок (404 для несуществующих товаров, 400 для валидации)
- Правильное управление сессиями БД

### 5. Исправленные проблемы

- ✅ Корректная строка подключения к PostgreSQL
- ✅ Отключение GSSAPI для Flyway и SQLAlchemy
- ✅ Правильное управление сессиями базы данных
- ✅ Ручное обновление timestamp `updated_at`
- ✅ Использование порта 5433 для избежания конфликтов

## Проверка работы

### Автоматический тест

```bash
python3 test_app.py
```

### Ручная проверка

#### 1. Запустить систему

```bash
make setup
make run
```

#### 2. Создать товар

```bash
curl -X POST "http://localhost:8000/products" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тестовый товар",
    "description": "Описание",
    "price": 100.00,
    "stock": 5,
    "category": "Тест",
    "status": "ACTIVE"
  }'
```

#### 3. Проверить в БД

```bash
docker exec -it marketplace-db psql -U marketplace -d marketplace -c "SELECT * FROM products;"
```

#### 4. Получить список товаров

```bash
curl "http://localhost:8000/products"
```

## Устранение проблем

### Ошибка "role marketplace does not exist"

Если вы видите эту ошибку, скорее всего на вашем хосте уже запущен PostgreSQL на порту 5432. Проект использует порт 5433. Убедитесь, что:

1. **Проверьте файл `.env`**: Убедитесь, что в нем указан порт **5433**:
   ```bash
   cat .env
   # Должно быть: DATABASE_URL=postgresql://marketplace:marketplace123@localhost:5433/marketplace
   ```
   
2. Если порт неправильный, исправьте:
   ```bash
   echo "DATABASE_URL=postgresql://marketplace:marketplace123@localhost:5433/marketplace" > .env
   ```

3. Docker контейнер запущен: `docker ps | grep marketplace-db`

4. Используется правильный порт в конфигурации (5433)

5. Пересоздайте контейнер: `docker-compose down -v && docker-compose up -d`

### Ошибка GSSAPI

Если возникают проблемы с GSSAPI аутентификацией:

1. Убедитесь, что в `flyway.conf` есть параметр `?gssEncMode=disable`
2. Убедитесь, что в `app/database.py` используется правильный драйвер `postgresql://`

### Docker не запускается (macOS)

Если используете Colima:

```bash
colima start
docker-compose up -d
```

## Дополнительная документация

- [`AUTH_AND_LOGGING.md`](AUTH_AND_LOGGING.md) - Подробная документация по аутентификации, авторизации и логированию
- [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) - Детальное описание структуры проекта
- [`openapi/products.yaml`](openapi/products.yaml) - Полная OpenAPI спецификация

## Автор

Учебный проект для курса "Архитектура микросервисов"