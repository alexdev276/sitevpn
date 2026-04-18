from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class SubscriptionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class PaymentProviderType(str, Enum):
    STRIPE = "stripe"


class TariffPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

