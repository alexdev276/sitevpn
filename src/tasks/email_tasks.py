from celery import shared_task
import asyncio
from src.infrastructure.email_sender import EmailSender
import structlog

logger = structlog.get_logger()

@shared_task
def send_email_task(to_email: str, subject: str, html_content: str):
    async def _send():
        sender = EmailSender()
        await sender.send_email(to_email, subject, html_content)

    asyncio.run(_send())
