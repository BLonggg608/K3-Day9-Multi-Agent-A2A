"""Payment reconciliation agent for Olist dispute cases."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Protocol

from src.shared.contracts import AgentResult

from .queries import PaymentRepository


CENT = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")
MAX_PAYMENT_IDS = 5


class PaymentRows(Protocol):
    def get_by_order_id(self, order_id: str) -> list[dict[str, object]]:
        ...


def _money(value: object, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid number") from exc
    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return amount


def _rounded(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _as_float(amount: Decimal) -> float:
    return float(_rounded(amount))


def reconcile_payments(
    order_id: str,
    payment_rows: list[dict[str, object]],
    item_total: object,
    freight_total: object,
) -> dict[str, Any]:
    """Return deterministic payment facts for one order.

    All rows participate in totals. Only the first five sequential IDs are
    exposed because the final output schema limits each affected-entity set to
    five IDs.
    """
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order_id must be a non-empty string")

    item_amount = _money(item_total, "item_total")
    freight_amount = _money(freight_total, "freight_total")
    if item_amount < 0 or freight_amount < 0:
        raise ValueError("item_total and freight_total cannot be negative")

    normalized_rows: list[dict[str, Any]] = []
    seen_sequences: set[int] = set()
    for row in payment_rows:
        if row.get("order_id") != order_id:
            raise ValueError("payment row order_id does not match requested order")
        try:
            sequence = int(row["payment_sequential"])
            installments = int(row["payment_installments"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("payment sequence and installments must be integers") from exc
        if sequence <= 0 or sequence in seen_sequences:
            raise ValueError("payment_sequential must be unique and positive")
        if installments < 0:
            raise ValueError("payment_installments cannot be negative")
        seen_sequences.add(sequence)

        value = _money(row.get("payment_value"), "payment_value")
        if value < 0:
            raise ValueError("payment_value cannot be negative")
        normalized_rows.append(
            {
                "payment_sequential": sequence,
                "payment_type": str(row.get("payment_type", "")),
                "payment_installments": installments,
                "payment_value": _as_float(value),
                "_decimal_value": value,
            }
        )

    normalized_rows.sort(key=lambda row: row["payment_sequential"])
    payment_total = sum(
        (row["_decimal_value"] for row in normalized_rows), Decimal("0")
    )
    expected_total = item_amount + freight_amount
    difference = abs(payment_total - expected_total)
    is_split = len(normalized_rows) >= 2
    is_reconciled = difference <= RECONCILIATION_TOLERANCE

    public_rows = []
    for row in normalized_rows:
        public_rows.append({key: value for key, value in row.items() if key != "_decimal_value"})

    sequences = [row["payment_sequential"] for row in normalized_rows]
    payment_ids = [f"{order_id}:{sequence}" for sequence in sequences[:MAX_PAYMENT_IDS]]
    evidence_ids = [
        f"payment:{order_id}:{sequence}" for sequence in sequences[:MAX_PAYMENT_IDS]
    ]
    return {
        "order_id": order_id,
        "payment_total_brl": _as_float(payment_total),
        "payment_rows": public_rows,
        "is_paid": payment_total > 0,
        "is_split_payment": is_split,
        "expected_total_brl": _as_float(expected_total),
        "payment_difference_brl": _as_float(difference),
        "is_payment_reconciled": is_reconciled,
        "is_valid_split_payment": is_split and is_reconciled,
        "payment_ids": payment_ids,
        "evidence_ids": evidence_ids,
    }


def analyze_payment(
    order_id: str,
    item_total: object,
    freight_total: object,
    repository: PaymentRows | None = None,
) -> dict[str, Any]:
    """Public functional API requested by the team assignment."""
    source = repository or PaymentRepository()
    return reconcile_payments(
        order_id,
        source.get_by_order_id(order_id),
        item_total,
        freight_total,
    )


class PaymentAgent:
    """Coordinator-compatible adapter around payment reconciliation."""

    name = "payment"

    def __init__(self, repository: PaymentRows | None = None):
        self.repository = repository or PaymentRepository()

    @staticmethod
    def _find_order_facts(context: dict[str, Any]) -> dict[str, Any]:
        results = context.get("results", {})
        if not isinstance(results, dict):
            raise ValueError("context.results must be an object")
        for result in results.values():
            if not isinstance(result, dict) or not result.get("ok", False):
                continue
            data = result.get("data", {})
            required = {"order_id", "item_total_brl", "freight_total_brl"}
            if isinstance(data, dict) and required.issubset(data):
                return data
        raise ValueError(
            "payment agent requires prior order facts containing order_id, "
            "item_total_brl, and freight_total_brl"
        )

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        try:
            order = self._find_order_facts(context)
            data = analyze_payment(
                str(order["order_id"]),
                order["item_total_brl"],
                order["freight_total_brl"],
                self.repository,
            )
            evidence_ids = data.pop("evidence_ids")
            return AgentResult(
                agent=self.name,
                data=data,
                evidence_ids=evidence_ids,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            return AgentResult(
                agent=self.name,
                ok=False,
                errors=[str(exc)],
            )
