"""Delivery-domain analysis based only on facts handed off by Order Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.shared.contracts import AgentResult


def _timestamp(value: Any, field: str) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a timestamp string or null")
    try:
        # Olist uses ``YYYY-MM-DD HH:MM:SS``; fromisoformat also accepts its
        # ISO-8601 equivalent and preserves an offset when one is supplied.
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _precomputed_violations(order_data: dict[str, Any]) -> list[str]:
    raw = order_data.get("seller_handoff_violations", []) or []
    explicit_ids = order_data.get("violating_seller_ids", []) or []
    seller_ids: list[str] = []
    if isinstance(explicit_ids, (list, tuple, set)):
        for seller_id in explicit_ids:
            if seller_id and str(seller_id) not in seller_ids:
                seller_ids.append(str(seller_id))
    if isinstance(raw, bool):
        return seller_ids
    if isinstance(raw, str):
        raw = [raw]
    for entry in raw:
        seller_id = entry.get("seller_id") if isinstance(entry, dict) else entry
        if seller_id and str(seller_id) not in seller_ids:
            seller_ids.append(str(seller_id))
    return seller_ids


def analyze_delivery(order_data: dict[str, Any]) -> dict[str, Any]:
    """Classify delivery timing and identify late seller handoffs.

    This function deliberately does not choose a primary policy issue.  It
    returns delivery facts so the Policy Agent can enforce global precedence.
    """
    if not isinstance(order_data, dict):
        raise ValueError("order_data must be a dictionary")

    delivered = _timestamp(
        order_data.get("order_delivered_customer_date", order_data.get("delivered_customer_date")),
        "order_delivered_customer_date",
    )
    estimated = _timestamp(
        order_data.get("order_estimated_delivery_date", order_data.get("estimated_delivery_date")),
        "order_estimated_delivery_date",
    )
    carrier = _timestamp(
        order_data.get("order_delivered_carrier_date", order_data.get("delivered_carrier_date")),
        "order_delivered_carrier_date",
    )

    items = order_data.get("items", []) or []
    violating_sellers = _precomputed_violations(order_data)
    shipping_limit_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        limit = _timestamp(item.get("shipping_limit_date"), "shipping_limit_date")
        if limit is not None:
            shipping_limit_count += 1
        seller_id = item.get("seller_id")
        if carrier is not None and limit is not None and carrier > limit and seller_id:
            seller_id = str(seller_id)
            if seller_id not in violating_sellers:
                violating_sellers.append(seller_id)

    has_delivery_dates = delivered is not None and estimated is not None
    is_late = bool(has_delivery_dates and delivered > estimated)
    within_estimate = bool(has_delivery_dates and delivered <= estimated)
    if is_late and violating_sellers:
        classification = "late_delivery_seller"
        cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
    elif is_late:
        classification = "late_delivery_logistics"
        cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
    elif within_estimate:
        classification = "unsupported_late_claim"
        cause_code = "DELIVERY_WITHIN_ESTIMATE"
    else:
        classification = None
        cause_code = None

    return {
        "is_late_delivery": is_late,
        "is_within_estimate": within_estimate,
        "has_delivery_dates": has_delivery_dates,
        "has_carrier_date": carrier is not None,
        "has_shipping_limits": bool(items) and shipping_limit_count == len(items),
        "delivery_classification": classification,
        "late_handoff_seller_ids": violating_sellers[:5],
        "root_cause_code": cause_code,
        # Delivery classification is provisional. Only PolicyAgent may emit
        # policy:<root_cause_code> after applying global rule precedence.
        "evidence_ids": [],
    }


class DeliveryAgent:
    """Coordinator adapter for :func:`analyze_delivery`."""

    name = "delivery"

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        try:
            order_data = _result_data(context, ("order_seller", "order", "order_agent"))
            data = analyze_delivery(order_data)
            # Delivery classification is an intermediate fact. Only PolicyAgent
            # owns the final policy:* evidence after applying global precedence
            # (for example, valid split payment can outrank an on-time delivery).
            data.pop("evidence_ids")
            return AgentResult(agent=self.name, data=data, evidence_ids=[])
        except (KeyError, ValueError) as exc:
            return AgentResult(agent=self.name, ok=False, errors=[str(exc)])


def _result_data(context: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    results = context.get("results", {})
    for name in names:
        result = results.get(name)
        if result is not None:
            return result.get("data", result) if isinstance(result, dict) else result.data
    raise KeyError(f"missing agent result; expected one of {names}")
