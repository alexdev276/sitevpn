from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "vpn_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.subscription_tasks", "src.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "renew-subscriptions-daily": {
            "task": "src.tasks.subscription_tasks.renew_expiring_subscriptions",
            "schedule": 86400.0,  # daily
        },
    },
)
