# VPN Service

Коммерческий VPN-сервис на FastAPI с clean architecture, PostgreSQL, Redis, Celery и интеграцией Remnawave API.

## Stack

- Python 3.11+
- FastAPI
- PostgreSQL + SQLAlchemy 2.0 Async ORM
- Redis
- Celery + Redis
- Stripe как платёжный провайдер
- JWT access/refresh токены
- structlog
- Pydantic Settings

## Структура

```text
src/
  api/
  application/
  core/
  db/
  domain/
  infrastructure/
  tasks/
tests/
```

## Основные возможности

- Регистрация, подтверждение email кодом, login/logout, refresh-токены в httpOnly cookie
- Восстановление и смена пароля
- Роли `admin` и `user`
- Платежи и подписки с webhooks Stripe
- Создание и продление VPN-пользователя в Remnawave
- Личный кабинет: подписка, VPN-конфиги, история платежей
- Админ-эндпоинты: пользователи, тарифы, платежи, системные логи
- Rate limiting и защита от brute force через Redis
- JSON-логирование через structlog

## Запуск локально

1. Скопируйте `.env.example` в `.env` и заполните секреты.
2. Поднимите сервисы:

```bash
docker compose up --build
```

3. Примените миграции:

```bash
alembic upgrade head
```

4. Swagger будет доступен на `http://localhost:8000/docs`.

## Переменные окружения

Основные переменные описаны в `.env.example`.

- `DATABASE_URL`: async DSN для PostgreSQL
- `REDIS_URL`: Redis для кэша, rate limit и Celery
- `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`: секреты JWT
- `STRIPE_*`: параметры Stripe
- `REMNAWAVE_*`: базовый URL, API key и Internal Squad ID
- `APP_LOG_FILE`: путь до лог-файла для admin endpoint `/api/v1/admin/logs`

## Remnawave

Интеграция изолирована в `src/infrastructure/clients/remnawave_client.py`.
Сервисный слой использует четыре основные операции:

- `create_user`
- `block_user`
- `extend_user`
- `delete_user`

Если SDK меняет имя клиентского класса, адаптер можно скорректировать локально без переписывания use case-логики.

## Тесты

```bash
pytest
```

Подробный сценарий использования API и прогонки тестов вынесен в [USAGE_AND_TESTS.md](/Users/alexej/Documents/VPN-USER/USAGE_AND_TESTS.md).

В проекте есть:

- unit-тест создания подписки
- unit-тест обработки webhook
- integration-тест регистрации пользователя и создания платежа через моки

## Примечания

- Все даты сохраняются как timezone-aware UTC datetimes.
- Refresh token хранится в httpOnly cookie.
- Для production стоит вынести отправку email в реальный SMTP/mail provider и усилить проверку Stripe signature в формате, который ожидает Stripe.
