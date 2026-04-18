# Usage And Tests

Этот файл нужен как быстрый практический сценарий:

- как руками проверить основной функционал сервиса
- как прогонять unit и integration тесты
- какие переменные и зависимости нужны для локального запуска

## Подготовка окружения

1. Создайте `.env` на основе `.env.example`.
2. Поднимите инфраструктуру:

```bash
docker compose up --build
```

3. Примените миграции:

```bash
alembic upgrade head
```

4. Установите зависимости локально, если хотите запускать тесты не из контейнера:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .[dev]
```

## Базовые API-сценарии

Базовый URL:

```bash
export BASE_URL="http://localhost:8000/api/v1"
```

### 1. Регистрация пользователя

```bash
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strong-password-123"
  }'
```

Ожидаемый результат:

```json
{
  "message": "Registration successful. Verification code sent."
}
```

Примечание:
В текущем проекте код подтверждения логируется и кладется в Redis по ключу `verify:<email>`.

### 2. Подтверждение email

Если Redis поднят локально, код можно получить так:

```bash
redis-cli GET "verify:user@example.com"
```

После этого подтвердите email:

```bash
curl -X POST "$BASE_URL/auth/confirm-email" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "code": "ABC123"
  }'
```

### 3. Логин

```bash
curl -i -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strong-password-123"
  }'
```

Что важно:

- в body вернется `access_token`
- в `Set-Cookie` вернется `refresh_token`

Пример сохранения access token:

```bash
export ACCESS_TOKEN="<access_token>"
```

### 4. Просмотр профиля

```bash
curl "$BASE_URL/users/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 5. Создание тарифа через admin

Для этого нужен пользователь с ролью `admin`.

```bash
curl -X POST "$BASE_URL/admin/tariffs" \
  -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monthly Pro",
    "description": "30 days subscription",
    "period": "monthly",
    "price": 10.00,
    "duration_days": 30,
    "traffic_limit_bytes": 107374182400
  }'
```

### 6. Создание платежа

```bash
curl -X POST "$BASE_URL/payments" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tariff_id": "PUT_TARIFF_UUID_HERE"
  }'
```

Ожидаемый результат:

- создается `pending` подписка
- создается запись платежа
- возвращается `checkout_url`

### 7. Проверка текущей подписки

```bash
curl "$BASE_URL/subscriptions/current" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 8. Отмена подписки

```bash
curl -X POST "$BASE_URL/subscriptions/cancel" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Проверка webhook Stripe

В проекте webhook endpoint:

```text
/api/v1/payments/webhook
```

Текущая реализация ожидает заголовок:

```text
Stripe-Signature
```

Для локальной отладки можно отправить тестовый JSON:

```bash
curl -X POST "http://localhost:8000/api/v1/payments/webhook" \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: <signature>" \
  -d '{
    "type": "checkout.session.completed",
    "data": {
      "object": {
        "id": "cs_test",
        "status": "complete",
        "payment_status": "paid",
        "subscription": "sub_test",
        "metadata": {
          "user_id": "USER_ID",
          "tariff_id": "TARIFF_ID",
          "subscription_id": "SUBSCRIPTION_ID"
        }
      }
    }
  }'
```

## Что проверить руками после успешной оплаты

После webhook или успешной оплаты имеет смысл проверить:

- у `payments` статус стал `succeeded`
- у `subscriptions` статус стал `active`
- создан или обновлен `vpn_users`
- в профиле пользователя появились данные по VPN и подписке

## Прогон тестов

### Полный запуск

```bash
python3 -m pytest
```

### Только unit-тесты

```bash
python3 -m pytest tests/unit -q
```

### Только integration-тесты

```bash
python3 -m pytest tests/integration -q
```

### Один конкретный тест

```bash
python3 -m pytest tests/integration/test_register_and_subscribe.py -q
```

## Что именно покрыто тестами

### Unit

[tests/unit/test_subscription_service.py](/Users/alexej/Documents/VPN-USER/tests/unit/test_subscription_service.py)

- создание `pending` подписки
- расчет базового срока подписки

[tests/unit/test_payment_webhook.py](/Users/alexej/Documents/VPN-USER/tests/unit/test_payment_webhook.py)

- обработка webhook
- перевод платежа в `succeeded`
- активация подписки

### Integration

[tests/integration/test_register_and_subscribe.py](/Users/alexej/Documents/VPN-USER/tests/integration/test_register_and_subscribe.py)

- регистрация пользователя
- подтверждение email через код из Redis
- логин
- создание платежа через mock Stripe provider

## Рекомендуемый сценарий smoke test

1. Поднять `docker compose`.
2. Создать тариф через admin endpoint.
3. Зарегистрировать обычного пользователя.
4. Подтвердить email.
5. Выполнить логин и сохранить `access_token`.
6. Создать платеж.
7. Отправить тестовый webhook.
8. Проверить `/users/me` и `/subscriptions/current`.

## Если тесты не стартуют

Частые причины:

- не установлен `pytest`
- не установлены dev-зависимости из `.[dev]`
- не создан `.env`
- недоступны PostgreSQL или Redis при реальном запуске

Минимальная команда для установки тестового окружения:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .[dev]
```

