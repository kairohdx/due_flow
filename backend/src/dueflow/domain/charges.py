from enum import Enum


class ChargeStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

