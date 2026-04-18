from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings


settings = get_settings()
celery_app = Celery("vpn_service", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "renew-expired-subscriptions": {
            "task": "src.tasks.jobs.renew_expired_subscriptions",
            "schedule": crontab(minute="*/30"),
        },
        "sync-remnawave-usage": {
            "task": "src.tasks.jobs.sync_remnawave_usage",
            "schedule": crontab(minute="*/15"),
        },
    },
)

