# VPN Service with Remnawave Integration

## Quick Start

1. Clone repository and copy `.env.example` to `.env`, fill in your values.
2. Run `docker-compose up -d`
3. Access API docs at http://localhost:8000/docs

## Environment Variables

See `.env.example` for all required variables. Important:
- `REMNAWAVE_API_URL` and `REMNAWAVE_API_KEY` from your Remnawave panel.
- `STRIPE_API_KEY` and `STRIPE_WEBHOOK_SECRET` from Stripe dashboard.
- `SMTP_*` for email sending.

## Running Migrations

Alembic is configured. Run inside app container:
docker-compose exec app alembic upgrade head

## Testing

Run tests:

docker-compose exec app pytest

## Architecture

- Clean Architecture with separation of domain, application, infrastructure, and API layers.
- Async SQLAlchemy, Redis for caching/rate limiting.
- Celery for background tasks (email, subscription renewal).
- JWT authentication with refresh tokens in httpOnly cookies.
- Stripe payment integration (easily replaceable).

## API Endpoints

See Swagger at `/docs` for full list.

## Admin

Default admin credentials can be set via `.env`. After first run, change password.
