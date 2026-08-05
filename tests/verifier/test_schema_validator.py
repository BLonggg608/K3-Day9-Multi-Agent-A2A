from __future__ import annotations

import copy

import pytest

from src.verifier.schema_validator import validate_output

SOURCE_DATA = {
    "order_ids": {"o1"},
    "item_ids": {"o1:1"},
    "seller_ids": {"s1"},
    "payment_ids": {"o1:1"},
}

VALID_OUTPUT = {
    "case_id": "EC_001",
    "assessment": {
        "primary_issue": "late_delivery_seller",
        "case_status": "action_required",
        "confidence": 0.92,
    },
    "affected_entities": {
        "order_ids": ["o1"],
        "item_ids": ["o1:1"],
        "seller_ids": ["s1"],
        "payment_ids": ["o1:1"],
    },
    "root_cause_analysis": {
        "ranked_causes": [{"cause_code": "SELLER_HANDOFF_AFTER_LIMIT", "rank": 1}],
        "responsible_parties": [{"party_type": "seller", "party_id": "s1"}],
    },
    "evidence_ids": [
        "order:o1",
        "item:o1:1",
        "payment:o1:1",
        "seller:s1",
        "policy:SELLER_HANDOFF_AFTER_LIMIT",
    ],
    "financial_resolution": {
        "currency": "BRL",
        "item_total_brl": 100.0,
        "freight_total_brl": 15.0,
        "payment_total_brl": 115.0,
        "recommended_refund_brl": 15.0,
    },
    "resolution_actions": ["refund_freight"],
}


def test_valid_output_has_no_errors():
    assert validate_output(VALID_OUTPUT, SOURCE_DATA) == []


def test_missing_top_level_key():
    output = copy.deepcopy(VALID_OUTPUT)
    del output["financial_resolution"]
    errors = validate_output(output, SOURCE_DATA)
    assert any("financial_resolution" in e for e in errors)


def test_missing_nested_key():
    output = copy.deepcopy(VALID_OUTPUT)
    del output["assessment"]["confidence"]
    errors = validate_output(output, SOURCE_DATA)
    assert any("assessment.confidence" in e for e in errors)


def test_confidence_out_of_range():
    output = copy.deepcopy(VALID_OUTPUT)
    output["assessment"]["confidence"] = 1.5
    errors = validate_output(output, SOURCE_DATA)
    assert any("confidence" in e for e in errors)


def test_invalid_case_status():
    output = copy.deepcopy(VALID_OUTPUT)
    output["assessment"]["case_status"] = "maybe"
    errors = validate_output(output, SOURCE_DATA)
    assert any("case_status" in e for e in errors)


def test_evidence_id_bad_format():
    output = copy.deepcopy(VALID_OUTPUT)
    output["evidence_ids"] = ["order-o1"]
    errors = validate_output(output, SOURCE_DATA)
    assert any("unknown format" in e for e in errors)


def test_evidence_id_not_in_source_data():
    output = copy.deepcopy(VALID_OUTPUT)
    output["evidence_ids"] = ["order:does-not-exist"]
    errors = validate_output(output, SOURCE_DATA)
    assert any("unknown order" in e for e in errors)


def test_affected_entity_not_in_source_data():
    output = copy.deepcopy(VALID_OUTPUT)
    output["affected_entities"]["seller_ids"] = ["fake-seller"]
    errors = validate_output(output, SOURCE_DATA)
    assert any("unknown id 'fake-seller'" in e for e in errors)


def test_entity_limit_exceeded():
    output = copy.deepcopy(VALID_OUTPUT)
    output["affected_entities"]["order_ids"] = [f"o{i}" for i in range(6)]
    errors = validate_output(output, SOURCE_DATA)
    assert any("order_ids exceeds limit" in e for e in errors)


def test_refund_freight_must_equal_freight_total():
    output = copy.deepcopy(VALID_OUTPUT)
    output["financial_resolution"]["recommended_refund_brl"] = 999.0
    errors = validate_output(output, SOURCE_DATA)
    assert any("refund_freight" in e for e in errors)


def test_no_action_requires_zero_refund():
    output = copy.deepcopy(VALID_OUTPUT)
    output["assessment"]["case_status"] = "no_action"
    output["resolution_actions"] = ["reject_late_refund"]
    output["financial_resolution"]["recommended_refund_brl"] = 5.0
    errors = validate_output(output, SOURCE_DATA)
    assert any("no_action" in e or "no-refund" in e for e in errors)


def test_money_not_rounded():
    output = copy.deepcopy(VALID_OUTPUT)
    output["financial_resolution"]["freight_total_brl"] = 15.006
    errors = validate_output(output, SOURCE_DATA)
    assert any("not rounded" in e for e in errors)
