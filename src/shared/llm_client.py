"""Optional OpenAI client for case rationale generation.

The client is deliberately separate from deterministic domain rules. It is
used for a concise explanation only; it must never decide money, evidence, or
policy precedence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


OPENAI_MODEL = "gpt-4o-mini"


def _load_openai_key() -> str | None:
    key = os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    if key:
        return key

    env_path = Path(".env")
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() in {"OPENAI_KEY", "OPENAI_API_KEY"}:
            return value.strip().strip('"').strip("'") or None
    return None


class OpenAIClient:
    """Small dependency-injected wrapper around the OpenAI Responses API."""

    model = OPENAI_MODEL

    def __init__(self, api_key: str | None = None, model: str = OPENAI_MODEL):
        self.api_key = api_key or _load_openai_key()
        self.model = model
        if not self.api_key:
            raise RuntimeError("OPENAI_KEY is not configured")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the openai package before using OpenAIClient") from exc
        self._client = OpenAI(api_key=self.api_key)

    def explain_case(self, case: dict[str, Any], deterministic_output: dict[str, Any]) -> str:
        """Generate a short rationale from already verified facts."""
        facts = {
            "case_id": case.get("case_id"),
            "assessment": deterministic_output.get("assessment"),
            "root_cause_analysis": deterministic_output.get("root_cause_analysis"),
            "financial_resolution": deterministic_output.get("financial_resolution"),
            "resolution_actions": deterministic_output.get("resolution_actions"),
            "evidence_ids": deterministic_output.get("evidence_ids"),
        }
        response = self._client.responses.create(
            model=self.model,
            instructions=(
                "You are a concise audit assistant. Summarize the supplied verified "
                "facts in Vietnamese in at most three sentences. Do not invent facts, "
                "change the decision, calculate money, or add evidence IDs."
            ),
            input=json.dumps(facts, ensure_ascii=False),
            max_output_tokens=180,
        )
        return response.output_text.strip()

