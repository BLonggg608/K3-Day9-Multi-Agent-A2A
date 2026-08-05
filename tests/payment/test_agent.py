from __future__ import annotations

import unittest

from src.payment.agent import PaymentAgent, reconcile_payments
from src.payment.queries import InMemoryPaymentRepository


ORDER_ID = "order-001"


def payment(
    sequence: int,
    value: object,
    *,
    installments: int = 1,
    order_id: str = ORDER_ID,
) -> dict[str, object]:
    return {
        "order_id": order_id,
        "payment_sequential": sequence,
        "payment_type": "credit_card",
        "payment_installments": installments,
        "payment_value": value,
    }


class ReconcilePaymentsTests(unittest.TestCase):
    def test_no_payment(self) -> None:
        result = reconcile_payments(ORDER_ID, [], 0, 0)
        self.assertEqual(result["payment_total_brl"], 0.0)
        self.assertFalse(result["is_paid"])
        self.assertFalse(result["is_split_payment"])
        self.assertEqual(result["payment_ids"], [])

    def test_one_payment_reconciles(self) -> None:
        result = reconcile_payments(ORDER_ID, [payment(1, "115.00")], 100, 15)
        self.assertTrue(result["is_paid"])
        self.assertFalse(result["is_split_payment"])
        self.assertTrue(result["is_payment_reconciled"])
        self.assertFalse(result["is_valid_split_payment"])

    def test_multiple_payment_rows_form_valid_split_payment(self) -> None:
        rows = [payment(2, "15.00"), payment(1, "100.00")]
        result = reconcile_payments(ORDER_ID, rows, 100, 15)
        self.assertTrue(result["is_split_payment"])
        self.assertTrue(result["is_valid_split_payment"])
        self.assertEqual(
            result["payment_ids"], [f"{ORDER_ID}:1", f"{ORDER_ID}:2"]
        )
        self.assertEqual(
            result["evidence_ids"],
            [f"payment:{ORDER_ID}:1", f"payment:{ORDER_ID}:2"],
        )

    def test_invalid_split_payment_is_not_reconciled(self) -> None:
        rows = [payment(1, "50.00"), payment(2, "50.00")]
        result = reconcile_payments(ORDER_ID, rows, 100, 15)
        self.assertTrue(result["is_split_payment"])
        self.assertFalse(result["is_payment_reconciled"])
        self.assertFalse(result["is_valid_split_payment"])

    def test_difference_of_exactly_ten_cents_is_allowed(self) -> None:
        result = reconcile_payments(ORDER_ID, [payment(1, "114.90")], 100, 15)
        self.assertTrue(result["is_payment_reconciled"])

    def test_difference_over_ten_cents_is_rejected(self) -> None:
        result = reconcile_payments(ORDER_ID, [payment(1, "114.89")], 100, 15)
        self.assertFalse(result["is_payment_reconciled"])

    def test_installments_do_not_create_split_payment_or_multiply_value(self) -> None:
        result = reconcile_payments(
            ORDER_ID, [payment(1, "115.00", installments=8)], 100, 15
        )
        self.assertEqual(result["payment_total_brl"], 115.0)
        self.assertFalse(result["is_split_payment"])

    def test_all_rows_are_summed_but_entity_ids_are_limited_to_five(self) -> None:
        rows = [payment(sequence, "1.00") for sequence in range(1, 7)]
        result = reconcile_payments(ORDER_ID, rows, 6, 0)
        self.assertEqual(result["payment_total_brl"], 6.0)
        self.assertEqual(len(result["payment_rows"]), 6)
        self.assertEqual(len(result["payment_ids"]), 5)
        self.assertEqual(len(result["evidence_ids"]), 5)

    def test_rejects_duplicate_payment_sequence(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique and positive"):
            reconcile_payments(
                ORDER_ID, [payment(1, "50"), payment(1, "50")], 100, 0
            )


class PaymentAgentTests(unittest.TestCase):
    def test_agent_consumes_prior_order_facts(self) -> None:
        repository = InMemoryPaymentRepository([payment(1, "115.00")])
        agent = PaymentAgent(repository)
        context = {
            "case": {"case_id": "EC_001"},
            "results": {
                "order_seller": {
                    "agent": "order_seller",
                    "ok": True,
                    "data": {
                        "order_id": ORDER_ID,
                        "item_total_brl": 100.0,
                        "freight_total_brl": 15.0,
                    },
                    "errors": [],
                    "evidence_ids": [],
                }
            },
        }
        result = agent.analyze(context)
        self.assertTrue(result.ok)
        self.assertEqual(result.data["payment_total_brl"], 115.0)
        self.assertEqual(result.evidence_ids, [f"payment:{ORDER_ID}:1"])

    def test_agent_returns_structured_error_when_order_facts_are_missing(self) -> None:
        agent = PaymentAgent(InMemoryPaymentRepository([]))
        result = agent.analyze({"case": {"case_id": "EC_001"}, "results": {}})
        self.assertFalse(result.ok)
        self.assertIn("requires prior order facts", result.errors[0])


if __name__ == "__main__":
    unittest.main()
