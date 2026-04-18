from src.api.v1.schemas.common import PaymentRead, SubscriptionRead, UserRead, VpnUserRead


class DashboardResponse(UserRead):
    subscription: SubscriptionRead | None = None
    vpn_user: VpnUserRead | None = None
    payments: list[PaymentRead]

