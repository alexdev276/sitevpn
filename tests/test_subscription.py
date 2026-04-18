import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from src.application.subscription_service import SubscriptionService
from src.domain.subscription import SubscriptionCreate

@pytest.mark.asyncio
async def test_create_subscription_flow(client: AsyncClient, test_user, test_tariff):
    # Login first to get token
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create payment intent
    payment_resp = await client.post("/api/v1/payments/create-intent", json={
        "tariff_id": test_tariff.id,
        "success_url": "http://example.com/success",
        "cancel_url": "http://example.com/cancel"
    }, headers=headers)
    assert payment_resp.status_code == 200
    intent_data = payment_resp.json()
    assert "client_secret" in intent_data

    # Simulate webhook
    # We would need to mock Stripe webhook event, but for unit test we mock services
