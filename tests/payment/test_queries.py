from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.payment.queries import PaymentRepository


class PaymentRepositoryTests(unittest.TestCase):
    def test_loads_and_sorts_rows_by_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "payments.csv"
            csv_path.write_text(
                "order_id,payment_sequential,payment_type,payment_installments,payment_value\n"
                "abc,2,voucher,1,15.00\n"
                "abc,1,credit_card,2,100.00\n",
                encoding="utf-8",
            )
            rows = PaymentRepository(csv_path).get_by_order_id("abc")
        self.assertEqual([row["payment_sequential"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["payment_value"], "100.00")

    def test_rejects_missing_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "payments.csv"
            csv_path.write_text("order_id,payment_value\nabc,1.00\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                PaymentRepository(csv_path).get_by_order_id("abc")


if __name__ == "__main__":
    unittest.main()
