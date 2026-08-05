"""EC_POLICY_V1 evaluation and financial resolution."""

from __future__ import annotations

from typing import Any

from src.shared.contracts import AgentResult

from .delivery_agent import _result_data
from .rules import (
    DECISION_CONFIDENCE,
    ISSUE_RULES,
    POLICY_VERSION,
    money,
    payment_matches_order,
)


def _select_issue(
    order_data: dict[str, Any], payment_data: dict[str, Any], delivery_data: dict[str, Any]
) -> str:
    status = str(order_data.get("order_status", "")).lower()
    paid = money(payment_data.get("payment_total_brl", 0)) > 0
    if status == "canceled" and paid:
        return "canceled_order_paid"
    if status == "unavailable" and paid:
        return "unavailable_order_paid"
    if delivery_data.get("is_late_delivery") and delivery_data.get("late_handoff_seller_ids"):
        return "late_delivery_seller"
    if delivery_data.get("is_late_delivery"):
        return "late_delivery_logistics"
    if payment_data.get("is_split_payment") and payment_data.get("is_valid_split_payment"):
        return "valid_split_payment"

    item_total = money(order_data.get("item_total_brl", 0))
    freight_total = money(order_data.get("freight_total_brl", 0))
    if delivery_data.get("is_within_estimate") and payment_matches_order(
        payment_data, item_total, freight_total
    ):
        return "unsupported_late_claim"
    raise ValueError("no EC_POLICY_V1 rule matched the supplied facts")


def apply_policy(
    order_data: dict[str, Any],
    payment_data: dict[str, Any],
    delivery_data: dict[str, Any],
) -> dict[str, Any]:
    """Apply policy precedence and return output sections owned by Policy Agent."""
    if not all(isinstance(value, dict) for value in (order_data, payment_data, delivery_data)):
        raise ValueError("order_data, payment_data and delivery_data must be dictionaries")

    issue = _select_issue(order_data, payment_data, delivery_data)
    rule = ISSUE_RULES[issue]
    item_total = money(order_data.get("item_total_brl", 0))
    freight_total = money(order_data.get("freight_total_brl", 0))
    payment_total = money(payment_data.get("payment_total_brl", 0))
    action = str(rule["action"])
    refund = payment_total if action == "issue_full_refund" else freight_total if action == "refund_freight" else 0.0

    parties: list[dict[str, str]] = []
    if issue == "late_delivery_seller":
        parties = [
            {"party_type": "seller", "party_id": seller_id}
            for seller_id in delivery_data.get("late_handoff_seller_ids", [])[:3]
        ]
    elif rule["party_type"] and rule["party_id"]:
        parties = [{"party_type": str(rule["party_type"]), "party_id": str(rule["party_id"])}]

    cause_code = str(rule["cause_code"])
    evidence_ids = [f"policy:{cause_code}"]
    if issue == "late_delivery_seller":
        evidence_ids = [
            *(f"seller:{party['party_id']}" for party in parties),
            *evidence_ids,
        ]

    return {
        "assessment": {
            "primary_issue": issue,
            "case_status": "action_required" if refund > 0 else "no_action",
            "confidence": DECISION_CONFIDENCE,
        },
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": cause_code, "rank": 1}],
            "responsible_parties": parties,
        },
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "payment_total_brl": payment_total,
            "recommended_refund_brl": money(refund),
        },
        "resolution_actions": [action],
        "evidence_ids": evidence_ids,
    }


class PolicyAgent:
    """Coordinator adapter for :func:`apply_policy`."""

    name = "policy"

    def __init__(self, policy_version: str = POLICY_VERSION):
        if policy_version != POLICY_VERSION:
            raise ValueError(f"unsupported policy version: {policy_version}")
        self.policy_version = policy_version

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        try:
            case_version = context.get("case", {}).get("policy_version", POLICY_VERSION)
            if case_version != self.policy_version:
                raise ValueError(f"unsupported policy version: {case_version}")
            order_data = _result_data(context, ("order_seller", "order", "order_agent"))
            payment_data = _result_data(context, ("payment", "payment_agent"))
            delivery_data = _result_data(context, ("delivery", "delivery_agent"))
            data = apply_policy(order_data, payment_data, delivery_data)
            evidence = data.pop("evidence_ids")
            return AgentResult(agent=self.name, data=data, evidence_ids=evidence)
        except (KeyError, ValueError) as exc:
            return AgentResult(agent=self.name, ok=False, errors=[str(exc)])
