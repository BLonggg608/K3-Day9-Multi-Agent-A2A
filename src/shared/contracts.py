"""Contracts shared by all agents.

This module intentionally contains schemas and interfaces only. Domain logic
belongs to the individual agent modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AgentResult:
    """A stable handoff envelope between agents."""

    agent: str
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


class Agent(Protocol):
    """Minimal interface required by the Coordinator."""

    name: str

    def analyze(self, context: dict[str, Any]) -> AgentResult:
        ...


@dataclass
class CaseContext:
    """Mutable case context passed through the handoff chain."""

    case: dict[str, Any]
    results: dict[str, AgentResult] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case,
            "results": {
                name: {
                    "agent": result.agent,
                    "ok": result.ok,
                    "data": result.data,
                    "errors": result.errors,
                    "evidence_ids": result.evidence_ids,
                }
                for name, result in self.results.items()
            },
        }


REQUIRED_OUTPUT_KEYS = {
    "case_id",
    "assessment",
    "affected_entities",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
}

