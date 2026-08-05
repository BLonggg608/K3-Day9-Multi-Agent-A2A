"""Constants and small helpers for EC_POLICY_V1.

Keeping the policy vocabulary here avoids spelling drift between the delivery
and policy agents.  The order of ``POLICY_PRIORITY`` is business-significant.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


POLICY_VERSION = "EC_POLICY_V1"
PAYMENT_TOLERANCE_BRL = Decimal("0.10")

POLICY_PRIORITY = (
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
)

ISSUE_RULES: dict[str, dict[str, str | None]] = {
    "canceled_order_paid": {
        "cause_code": "ORDER_CANCELED_AFTER_PAYMENT",
        "party_type": "platform",
        "party_id": "OLIST_PLATFORM",
        "action": "issue_full_refund",
    },
    "unavailable_order_paid": {
        "cause_code": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
        "party_type": "platform",
        "party_id": "OLIST_PLATFORM",
        "action": "issue_full_refund",
    },
    "late_delivery_seller": {
        "cause_code": "SELLER_HANDOFF_AFTER_LIMIT",
        "party_type": "seller",
        "party_id": None,
        "action": "refund_freight",
    },
    "late_delivery_logistics": {
        "cause_code": "CARRIER_DELIVERED_AFTER_ESTIMATE",
        "party_type": "logistics_provider",
        "party_id": "LOGISTICS_PROVIDER",
        "action": "refund_freight",
    },
    "valid_split_payment": {
        "cause_code": "MULTIPLE_PAYMENTS_RECONCILED",
        "party_type": None,
        "party_id": None,
        "action": "explain_valid_split_payment",
    },
    "unsupported_late_claim": {
        "cause_code": "DELIVERY_WITHIN_ESTIMATE",
        "party_type": None,
        "party_id": None,
        "action": "reject_late_refund",
    },
}


def money(value: Any) -> float:
    """Return a BRL amount rounded half-up to two decimal places."""
    if value in (None, ""):
        value = 0
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def payment_matches_order(
    payment_data: dict[str, Any], item_total: float, freight_total: float
) -> bool:
    """Resolve reconciliation from explicit facts or calculate it safely."""
    for key in ("payment_matches_order", "is_reconciled", "is_payment_matched"):
        if key in payment_data:
            return bool(payment_data[key])
    expected = Decimal(str(item_total)) + Decimal(str(freight_total))
    actual = Decimal(str(payment_data.get("payment_total_brl", 0) or 0))
    return abs(actual - expected) <= PAYMENT_TOLERANCE_BRL
