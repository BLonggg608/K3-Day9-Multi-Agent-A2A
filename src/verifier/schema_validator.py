"""Pure schema/consistency validation for a single case output.

No file or dataframe I/O happens here: callers (src/verifier/agent.py,
scripts/validate_outputs.py) load CSVs/JSON and pass plain dicts/sets in,
which keeps this module trivial to unit test.
"""

from __future__ import annotations

import math
import re
from typing import Any

CASE_STATUSES = {"action_required", "no_action"}

PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}

ROOT_CAUSE_CODES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}

RESOLUTION_ACTIONS = {
    "issue_full_refund",
    "refund_freight",
    "explain_valid_split_payment",
    "reject_late_refund",
}

PARTY_TYPES = {"platform", "seller", "logistics_provider"}

# action -> expected refund basis; None means refund must be 0.
_ZERO_REFUND_ACTIONS = {"explain_valid_split_payment", "reject_late_refund"}

_ISSUE_CONTRACTS = {
    "canceled_order_paid": (
        "ORDER_CANCELED_AFTER_PAYMENT", "issue_full_refund", "platform", "action_required"
    ),
    "unavailable_order_paid": (
        "ORDER_UNAVAILABLE_AFTER_PAYMENT", "issue_full_refund", "platform", "action_required"
    ),
    "late_delivery_seller": (
        "SELLER_HANDOFF_AFTER_LIMIT", "refund_freight", "seller", "action_required"
    ),
    "late_delivery_logistics": (
        "CARRIER_DELIVERED_AFTER_ESTIMATE",
        "refund_freight",
        "logistics_provider",
        "action_required",
    ),
    "valid_split_payment": (
        "MULTIPLE_PAYMENTS_RECONCILED", "explain_valid_split_payment", None, "no_action"
    ),
    "unsupported_late_claim": (
        "DELIVERY_WITHIN_ESTIMATE", "reject_late_refund", None, "no_action"
    ),
}

_ENTITY_LIMIT = 5
_EVIDENCE_LIMIT = 10
_CAUSE_LIMIT = 3
_PARTY_LIMIT = 3
_ACTION_LIMIT = 5

_EVIDENCE_PATTERNS = {
    "order": re.compile(r"^order:(?P<order_id>[^:]+)$"),
    "item": re.compile(r"^item:(?P<order_id>[^:]+):(?P<item_id>[^:]+)$"),
    "payment": re.compile(r"^payment:(?P<order_id>[^:]+):(?P<payment_id>[^:]+)$"),
    "seller": re.compile(r"^seller:(?P<seller_id>[^:]+)$"),
    "policy": re.compile(r"^policy:(?P<cause_code>[^:]+)$"),
}

# Schema spec: nested dict mirrors the JSON shape; leaf values are
# type-or-tuple-of-types accepted at that key.
_SCHEMA: dict[str, Any] = {
    "case_id": str,
    "assessment": {
        "primary_issue": str,
        "case_status": str,
        "confidence": (int, float),
    },
    "affected_entities": {
        "order_ids": list,
        "item_ids": list,
        "seller_ids": list,
        "payment_ids": list,
    },
    "root_cause_analysis": {
        "ranked_causes": list,
        "responsible_parties": list,
    },
    "evidence_ids": list,
    "financial_resolution": {
        "currency": str,
        "item_total_brl": (int, float),
        "freight_total_brl": (int, float),
        "payment_total_brl": (int, float),
        "recommended_refund_brl": (int, float),
    },
    "resolution_actions": list,
}


def validate_output(output: dict[str, Any], source_data: dict[str, Any]) -> list[str]:
    """Validate one case output. Returns [] when valid.

    source_data shape (all sets of valid IDs, built from the CSVs):
        {
            "order_ids": set[str],
            "item_ids": set[str],       # "<order_id>:<order_item_id>"
            "seller_ids": set[str],
            "payment_ids": set[str],    # "<order_id>:<payment_sequential>"
        }
    """
    errors = _check_required_keys(output, _SCHEMA)
    if errors:
        return errors

    errors += _check_enums_and_ranges(output)
    errors += _check_limits(output)
    errors += _check_evidence_ids(output, source_data)
    errors += _check_policy_evidence_consistency(output)
    errors += _check_affected_entities_exist(output, source_data)
    errors += _check_financial_consistency(output)
    errors += _check_policy_consistency(output)
    errors += _check_uniqueness_and_relationships(output)
    return errors


def _check_policy_evidence_consistency(output: dict[str, Any]) -> list[str]:
    ranked_codes = {
        cause["cause_code"]
        for cause in output["root_cause_analysis"]["ranked_causes"]
        if isinstance(cause, dict) and cause.get("cause_code")
    }
    evidence_codes = {
        evidence_id.split(":", 1)[1]
        for evidence_id in output["evidence_ids"]
        if isinstance(evidence_id, str) and evidence_id.startswith("policy:")
    }
    errors: list[str] = []
    for code in sorted(evidence_codes - ranked_codes):
        errors.append(f"policy evidence '{code}' is not a ranked cause")
    for code in sorted(ranked_codes - evidence_codes):
        errors.append(f"ranked cause '{code}' has no policy evidence")
    return errors


def _check_required_keys(
    node: dict[str, Any], spec: dict[str, Any], path: str = ""
) -> list[str]:
    errors: list[str] = []
    for key, expected in spec.items():
        full_path = f"{path}.{key}" if path else key
        if key not in node:
            errors.append(f"missing key '{full_path}'")
            continue
        value = node[key]
        if isinstance(expected, dict):
            if not isinstance(value, dict):
                errors.append(f"'{full_path}' must be an object")
                continue
            errors += _check_required_keys(value, expected, full_path)
        else:
            if not isinstance(value, expected) or isinstance(value, bool):
                errors.append(f"'{full_path}' has wrong type, expected {expected}")
    return errors


def _check_enums_and_ranges(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    assessment = output["assessment"]

    if assessment["primary_issue"] not in PRIMARY_ISSUES:
        errors.append(f"invalid primary_issue '{assessment['primary_issue']}'")
    if assessment["case_status"] not in CASE_STATUSES:
        errors.append(f"invalid case_status '{assessment['case_status']}'")
    confidence = assessment["confidence"]
    if not 0 <= confidence <= 1:
        errors.append(f"confidence {confidence} out of range [0, 1]")

    for cause in output["root_cause_analysis"]["ranked_causes"]:
        code = cause.get("cause_code") if isinstance(cause, dict) else None
        if code not in ROOT_CAUSE_CODES:
            errors.append(f"invalid cause_code '{code}'")

    for party in output["root_cause_analysis"]["responsible_parties"]:
        party_type = party.get("party_type") if isinstance(party, dict) else None
        if party_type not in PARTY_TYPES:
            errors.append(f"invalid party_type '{party_type}'")

    for action in output["resolution_actions"]:
        if action not in RESOLUTION_ACTIONS:
            errors.append(f"invalid resolution_action '{action}'")

    if output["financial_resolution"]["currency"] != "BRL":
        errors.append("financial_resolution.currency must be 'BRL'")

    for money_key in (
        "item_total_brl",
        "freight_total_brl",
        "payment_total_brl",
        "recommended_refund_brl",
    ):
        value = output["financial_resolution"][money_key]
        if not math.isfinite(value):
            errors.append(f"financial_resolution.{money_key} must be finite")
        elif value < 0:
            errors.append(f"financial_resolution.{money_key} cannot be negative")
        elif round(value, 2) != value:
            errors.append(f"financial_resolution.{money_key} not rounded to 2 decimals")

    return errors


def _check_limits(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entities = output["affected_entities"]
    for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
        if len(entities[key]) > _ENTITY_LIMIT:
            errors.append(f"affected_entities.{key} exceeds limit of {_ENTITY_LIMIT}")

    if len(output["evidence_ids"]) > _EVIDENCE_LIMIT:
        errors.append(f"evidence_ids exceeds limit of {_EVIDENCE_LIMIT}")

    causes = output["root_cause_analysis"]["ranked_causes"]
    if len(causes) > _CAUSE_LIMIT:
        errors.append(f"ranked_causes exceeds limit of {_CAUSE_LIMIT}")

    parties = output["root_cause_analysis"]["responsible_parties"]
    if len(parties) > _PARTY_LIMIT:
        errors.append(f"responsible_parties exceeds limit of {_PARTY_LIMIT}")

    if len(output["resolution_actions"]) > _ACTION_LIMIT:
        errors.append(f"resolution_actions exceeds limit of {_ACTION_LIMIT}")

    return errors


def _check_evidence_ids(output: dict[str, Any], source_data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    order_ids = source_data.get("order_ids", set())
    item_ids = source_data.get("item_ids", set())
    payment_ids = source_data.get("payment_ids", set())
    seller_ids = source_data.get("seller_ids", set())

    for evidence_id in output["evidence_ids"]:
        prefix = evidence_id.split(":", 1)[0] if ":" in evidence_id else ""
        pattern = _EVIDENCE_PATTERNS.get(prefix)
        if pattern is None:
            errors.append(f"evidence id '{evidence_id}' has unknown format")
            continue

        match = pattern.match(evidence_id)
        if match is None:
            errors.append(f"evidence id '{evidence_id}' has malformed '{prefix}' format")
            continue

        if prefix == "order" and match["order_id"] not in order_ids:
            errors.append(f"evidence '{evidence_id}' references unknown order")
        elif prefix == "item":
            key = f"{match['order_id']}:{match['item_id']}"
            if key not in item_ids:
                errors.append(f"evidence '{evidence_id}' references unknown item")
        elif prefix == "payment":
            key = f"{match['order_id']}:{match['payment_id']}"
            if key not in payment_ids:
                errors.append(f"evidence '{evidence_id}' references unknown payment")
        elif prefix == "seller" and match["seller_id"] not in seller_ids:
            errors.append(f"evidence '{evidence_id}' references unknown seller")
        elif prefix == "policy" and match["cause_code"] not in ROOT_CAUSE_CODES:
            errors.append(f"evidence '{evidence_id}' references unknown cause code")

    return errors


def _check_affected_entities_exist(
    output: dict[str, Any], source_data: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    entities = output["affected_entities"]
    checks = (
        ("order_ids", source_data.get("order_ids", set())),
        ("item_ids", source_data.get("item_ids", set())),
        ("seller_ids", source_data.get("seller_ids", set())),
        ("payment_ids", source_data.get("payment_ids", set())),
    )
    for key, valid_ids in checks:
        for entity_id in entities[key]:
            if entity_id not in valid_ids:
                errors.append(f"affected_entities.{key} contains unknown id '{entity_id}'")
    return errors


def _check_financial_consistency(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    financial = output["financial_resolution"]
    actions = set(output["resolution_actions"])
    refund = financial["recommended_refund_brl"]

    if actions & _ZERO_REFUND_ACTIONS and refund != 0:
        errors.append("recommended_refund_brl must be 0 for a no-refund action")

    if "issue_full_refund" in actions and refund != round(financial["payment_total_brl"], 2):
        errors.append("recommended_refund_brl must equal payment_total_brl for issue_full_refund")

    if "refund_freight" in actions and refund != round(financial["freight_total_brl"], 2):
        errors.append("recommended_refund_brl must equal freight_total_brl for refund_freight")

    if output["assessment"]["case_status"] == "no_action" and refund != 0:
        errors.append("recommended_refund_brl must be 0 when case_status is no_action")

    return errors


def _check_policy_consistency(output: dict[str, Any]) -> list[str]:
    """Ensure all output sections describe the same EC_POLICY_V1 decision."""
    issue = output["assessment"]["primary_issue"]
    contract = _ISSUE_CONTRACTS.get(issue)
    if contract is None:
        return []  # The enum check already reports the unknown issue.

    expected_cause, expected_action, expected_party, expected_status = contract
    errors: list[str] = []
    causes = output["root_cause_analysis"]["ranked_causes"]
    actions = output["resolution_actions"]
    parties = output["root_cause_analysis"]["responsible_parties"]

    if not causes or causes[0].get("cause_code") != expected_cause:
        errors.append(f"primary_issue '{issue}' requires cause_code '{expected_cause}' at rank 1")
    if actions != [expected_action]:
        errors.append(f"primary_issue '{issue}' requires resolution_actions ['{expected_action}']")
    if output["assessment"]["case_status"] != expected_status:
        errors.append(f"primary_issue '{issue}' requires case_status '{expected_status}'")

    party_types = [party.get("party_type") for party in parties if isinstance(party, dict)]
    if expected_party is None and parties:
        errors.append(f"primary_issue '{issue}' must not assign a responsible party")
    elif expected_party is not None and expected_party not in party_types:
        errors.append(f"primary_issue '{issue}' requires party_type '{expected_party}'")
    return errors


def _check_uniqueness_and_relationships(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entities = output["affected_entities"]
    for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
        if len(entities[key]) != len(set(entities[key])):
            errors.append(f"affected_entities.{key} contains duplicates")
    if len(output["evidence_ids"]) != len(set(output["evidence_ids"])):
        errors.append("evidence_ids contains duplicates")

    causes = output["root_cause_analysis"]["ranked_causes"]
    ranks = [cause.get("rank") for cause in causes if isinstance(cause, dict)]
    if ranks != list(range(1, len(causes) + 1)):
        errors.append("ranked_causes ranks must be unique and consecutive from 1")

    order_ids = set(entities["order_ids"])
    for key in ("item_ids", "payment_ids"):
        for entity_id in entities[key]:
            order_id = entity_id.split(":", 1)[0]
            if order_id not in order_ids:
                errors.append(f"affected_entities.{key} id '{entity_id}' belongs to another order")

    seller_ids = set(entities["seller_ids"])
    for party in output["root_cause_analysis"]["responsible_parties"]:
        if isinstance(party, dict) and party.get("party_type") == "seller":
            party_id = party.get("party_id")
            if party_id not in seller_ids:
                errors.append(f"responsible seller '{party_id}' is not an affected seller")
    return errors
