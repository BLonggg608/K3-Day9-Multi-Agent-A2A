from __future__ import annotations

from pathlib import Path

from src.verifier.agent import VerifierAgent, load_source_data

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def test_load_source_data_reads_real_csvs():
    source_data = load_source_data(DATA_DIR)
    assert len(source_data["order_ids"]) > 0
    assert len(source_data["item_ids"]) > 0
    assert len(source_data["seller_ids"]) > 0
    assert len(source_data["payment_ids"]) > 0


def test_verifier_agent_reports_ok_true_for_matching_ids():
    source_data = load_source_data(DATA_DIR)
    real_order_id = next(iter(source_data["order_ids"]))
    real_item_id = next(i for i in source_data["item_ids"] if i.startswith(real_order_id))
    real_payment_id = next((p for p in source_data["payment_ids"] if p.startswith(real_order_id)), None)

    agent = VerifierAgent(data_dir=DATA_DIR)
    output = {
        "case_id": "EC_001",
        "assessment": {
            "primary_issue": "unsupported_late_claim",
            "case_status": "no_action",
            "confidence": 0.5,
        },
        "affected_entities": {
            "order_ids": [real_order_id],
            "item_ids": [real_item_id],
            "seller_ids": [],
            "payment_ids": [real_payment_id] if real_payment_id else [],
        },
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": "DELIVERY_WITHIN_ESTIMATE", "rank": 1}],
            "responsible_parties": [],
        },
        "evidence_ids": [
            f"order:{real_order_id}",
            f"item:{real_item_id}",
            "policy:DELIVERY_WITHIN_ESTIMATE",
        ],
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": 0.0,
            "freight_total_brl": 0.0,
            "payment_total_brl": 0.0,
            "recommended_refund_brl": 0.0,
        },
        "resolution_actions": ["reject_late_refund"],
    }

    result = agent.analyze({"case": {}, "results": {}, "output": output})
    assert result.ok, result.errors
    assert result.agent == "verifier"


def test_verifier_agent_reports_errors_for_fake_ids():
    agent = VerifierAgent(data_dir=DATA_DIR)
    result = agent.analyze({"case": {}, "results": {}, "output": {"case_id": "EC_001"}})
    assert not result.ok
    assert result.errors
