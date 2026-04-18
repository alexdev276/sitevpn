import pytest
from unittest.mock import AsyncMock, patch
from src.application.vpn_service import VpnService
from src.infrastructure.remnawave_client import RemnawaveClient

@pytest.mark.asyncio
async def test_provision_vpn_user(db_session, test_user, test_tariff):
    # Create subscription
    from src.db.models import Subscription
    from datetime import datetime, timedelta, timezone

    sub = Subscription(
        user_id=test_user.id,
        tariff_id=test_tariff.id,
        status="inactive",
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.commit()

    # Mock Remnawave client
    mock_remnawave = AsyncMock(spec=RemnawaveClient)
    mock_remnawave.create_user.return_value = {"uuid": "test-uuid-123"}

    service = VpnService(db_session, mock_remnawave)
    vpn_user = await service.provision_vpn_user(test_user, sub)

    assert vpn_user.remnawave_uuid == "test-uuid-123"
    mock_remnawave.create_user.assert_called_once()
