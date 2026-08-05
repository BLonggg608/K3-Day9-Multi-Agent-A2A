"""CSV access for the payment domain.

The repository builds an in-memory index once. A batch of 50 cases therefore
does not rescan the full payments CSV for every order.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


DEFAULT_PAYMENT_CSV = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "olist_order_payments_dataset.csv"
)

REQUIRED_COLUMNS = {
    "order_id",
    "payment_sequential",
    "payment_type",
    "payment_installments",
    "payment_value",
}


class PaymentRepository:
    """Read payment rows and index them by Olist order ID."""

    def __init__(self, csv_path: str | Path = DEFAULT_PAYMENT_CSV):
        self.csv_path = Path(csv_path)
        self._payments_by_order: dict[str, list[dict[str, object]]] | None = None

    def _load(self) -> None:
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"payment CSV not found: {self.csv_path}")

        payments_by_order: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    "payment CSV is missing required columns: "
                    + ", ".join(sorted(missing))
                )

            for line_number, row in enumerate(reader, start=2):
                try:
                    normalized = {
                        "order_id": row["order_id"],
                        "payment_sequential": int(row["payment_sequential"]),
                        "payment_type": row["payment_type"],
                        "payment_installments": int(row["payment_installments"]),
                        # Keep the source decimal as text. The agent uses Decimal
                        # for arithmetic and converts only its final output.
                        "payment_value": row["payment_value"],
                    }
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"invalid payment data at CSV line {line_number}"
                    ) from exc
                payments_by_order[normalized["order_id"]].append(normalized)

        for rows in payments_by_order.values():
            rows.sort(key=lambda payment: int(payment["payment_sequential"]))
        self._payments_by_order = dict(payments_by_order)

    def get_by_order_id(self, order_id: str) -> list[dict[str, object]]:
        """Return defensive copies of all payment rows for an order."""
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id must be a non-empty string")
        if self._payments_by_order is None:
            self._load()
        return [dict(row) for row in self._payments_by_order.get(order_id, [])]


class InMemoryPaymentRepository:
    """Small repository useful for isolated tests and local integration."""

    def __init__(self, rows: Iterable[dict[str, object]]):
        self._rows = [dict(row) for row in rows]

    def get_by_order_id(self, order_id: str) -> list[dict[str, object]]:
        rows = [row for row in self._rows if row.get("order_id") == order_id]
        return sorted(rows, key=lambda row: int(row["payment_sequential"]))
