"""Verifier Agent: the final gate the Coordinator calls before returning output.

Loads valid-ID sets from the source CSVs once, then delegates the actual
checks to src/verifier/schema_validator.py (kept dependency-free for testing).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.shared.contracts import AgentResult
from src.verifier.schema_validator import validate_output

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_source_data(data_dir: Path | str = DEFAULT_DATA_DIR) -> dict[str, set[str]]:
    """Build the ID sets schema_validator checks evidence/entities against."""
    data_dir = Path(data_dir)
    order_ids: set[str] = set()
    item_ids: set[str] = set()
    seller_ids: set[str] = set()
    payment_ids: set[str] = set()

    with open(data_dir / "olist_orders_dataset.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            order_ids.add(row["order_id"])

    with open(data_dir / "olist_order_items_dataset.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            item_ids.add(f"{row['order_id']}:{row['order_item_id']}")
            seller_ids.add(row["seller_id"])

    with open(data_dir / "olist_sellers_dataset.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seller_ids.add(row["seller_id"])

    with open(data_dir / "olist_order_payments_dataset.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            payment_ids.add(f"{row['order_id']}:{row['payment_sequential']}")

    return {
        "order_ids": order_ids,
        "item_ids": item_ids,
        "seller_ids": seller_ids,
        "payment_ids": payment_ids,
    }


class VerifierAgent:
    """Implements the shared Agent protocol; only reports errors, never edits output."""

    name = "verifier"

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR):
        self.source_data = load_source_data(data_dir)

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        output = context.get("output", {})
        errors = validate_output(output, self.source_data)
        return AgentResult(agent=self.name, ok=not errors, data={}, errors=errors)
