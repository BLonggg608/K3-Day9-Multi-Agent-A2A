"""Unit tests for member 4's Delivery and Policy agents (stdlib only)."""

from __future__ import annotations

import unittest

from src.delivery_policy.delivery_agent import DeliveryAgent, analyze_delivery
from src.delivery_policy.policy_agent import apply_policy


BASE_ORDER = {
    "order_status": "delivered",
    "order_delivered_carrier_date": "2018-01-02 10:00:00",
    "order_delivered_customer_date": "2018-01-12 10:00:00",
    "order_estimated_delivery_date": "2018-01-10 10:00:00",
    "item_total_brl": 100,
    "freight_total_brl": 15,
    "items": [{"seller_id": "SELLER_1", "shipping_limit_date": "2018-01-03 10:00:00"}],
}
BASE_PAYMENT = {"payment_total_brl": 115, "is_split_payment": False, "is_valid_split_payment": False}


class DeliveryTests(unittest.TestCase):
    def test_late_delivery_logistics_when_handoff_was_on_time(self):
        result = analyze_delivery(BASE_ORDER)
        self.assertEqual(result["delivery_classification"], "late_delivery_logistics")
        self.assertEqual(result["late_handoff_seller_ids"], [])

    def test_late_delivery_seller_when_handoff_exceeded_limit(self):
        order = dict(BASE_ORDER, order_delivered_carrier_date="2018-01-04 10:00:00")
        result = analyze_delivery(order)
        self.assertEqual(result["delivery_classification"], "late_delivery_seller")
        self.assertEqual(result["late_handoff_seller_ids"], ["SELLER_1"])

    def test_delivery_within_estimate(self):
        order = dict(BASE_ORDER, order_delivered_customer_date="2018-01-09 10:00:00")
        self.assertTrue(analyze_delivery(order)["is_within_estimate"])

    def test_invalid_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid order_delivered_customer_date"):
            analyze_delivery(dict(BASE_ORDER, order_delivered_customer_date="not-a-date"))

    def test_delivery_agent_does_not_emit_preliminary_policy_evidence(self):
        agent = DeliveryAgent()
        context = {
            "results": {
                "order_seller": {
                    "ok": True,
                    "data": BASE_ORDER,
                }
            }
        }
        result = agent.analyze(context)
        self.assertTrue(result.ok)
        self.assertEqual(result.evidence_ids, [])


class PolicyPriorityTests(unittest.TestCase):
    def decide(self, order=None, payment=None, delivery=None):
        return apply_policy(order or BASE_ORDER, payment or BASE_PAYMENT, delivery or analyze_delivery(order or BASE_ORDER))

    def test_canceled_paid_has_priority_over_late_delivery(self):
        result = self.decide(order=dict(BASE_ORDER, order_status="canceled"))
        self.assertEqual(result["assessment"]["primary_issue"], "canceled_order_paid")
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 115.0)

    def test_unavailable_paid(self):
        result = self.decide(order=dict(BASE_ORDER, order_status="unavailable"))
        self.assertEqual(result["assessment"]["primary_issue"], "unavailable_order_paid")

    def test_late_delivery_seller_precedes_split_payment(self):
        order = dict(BASE_ORDER, order_delivered_carrier_date="2018-01-04 10:00:00")
        payment = dict(BASE_PAYMENT, is_split_payment=True, is_valid_split_payment=True)
        result = self.decide(order=order, payment=payment)
        self.assertEqual(result["assessment"]["primary_issue"], "late_delivery_seller")
        self.assertEqual(result["root_cause_analysis"]["responsible_parties"][0]["party_id"], "SELLER_1")
        self.assertIn("seller:SELLER_1", result["evidence_ids"])

    def test_late_delivery_logistics(self):
        result = self.decide()
        self.assertEqual(result["assessment"]["primary_issue"], "late_delivery_logistics")
        self.assertEqual(result["assessment"]["confidence"], 1.0)
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 15.0)

    def test_valid_split_payment(self):
        order = dict(BASE_ORDER, order_delivered_customer_date=None, order_estimated_delivery_date=None)
        payment = dict(BASE_PAYMENT, is_split_payment=True, is_valid_split_payment=True)
        result = self.decide(order=order, payment=payment)
        self.assertEqual(result["assessment"]["primary_issue"], "valid_split_payment")
        self.assertEqual(result["assessment"]["case_status"], "no_action")

    def test_unsupported_late_claim_requires_reconciled_payment(self):
        order = dict(BASE_ORDER, order_delivered_customer_date="2018-01-09 10:00:00")
        result = self.decide(order=order)
        self.assertEqual(result["assessment"]["primary_issue"], "unsupported_late_claim")
        self.assertEqual(result["resolution_actions"], ["reject_late_refund"])

    def test_no_matching_rule_fails_explicitly(self):
        order = dict(BASE_ORDER, order_delivered_customer_date=None, order_estimated_delivery_date=None)
        with self.assertRaisesRegex(ValueError, "no EC_POLICY_V1 rule matched"):
            self.decide(order=order)


if __name__ == "__main__":
    unittest.main()
