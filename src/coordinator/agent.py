"""Coordinator orchestration for the dispute-resolution agents."""

from __future__ import annotations

from typing import Any, Iterable

from src.shared.contracts import Agent, AgentResult, CaseContext


class Coordinator:
    """Run domain agents in a fixed, auditable handoff order.

    The Coordinator owns orchestration only. Each domain agent owns its data
    access and business logic. Agents are injected so teammates can implement
    and test them independently.
    """

    name = "coordinator"

    def __init__(self, agents: Iterable[Agent], verifier: Agent | None = None):
        self.agents = list(agents)
        self.verifier = verifier

    def process_case(self, case: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(case, dict) or not case.get("case_id"):
            raise ValueError("case must be an object containing case_id")

        context = CaseContext(case=case)
        for agent in self.agents:
            result = agent.analyze(context.as_dict())
            context.results[agent.name] = result
            if not result.ok:
                return self._error_output(case, context, result)

        output = self._assemble_output(case, context)
        if self.verifier is not None:
            verification = self.verifier.analyze(
                {"case": case, "results": context.as_dict()["results"], "output": output}
            )
            if not verification.ok:
                output["_verification_errors"] = verification.errors
        return output

    @staticmethod
    def _assemble_output(case: dict[str, Any], context: CaseContext) -> dict[str, Any]:
        """Combine agent-owned sections without applying domain rules here."""
        merged: dict[str, Any] = {"case_id": case["case_id"]}
        for result in context.results.values():
            merged.update(result.data)
        evidence: list[str] = []
        for result in context.results.values():
            evidence.extend(result.evidence_ids)
        merged["evidence_ids"] = list(dict.fromkeys(evidence))
        return merged

    @staticmethod
    def _error_output(
        case: dict[str, Any], context: CaseContext, failed: AgentResult
    ) -> dict[str, Any]:
        return {
            "case_id": case.get("case_id"),
            "error": {
                "agent": failed.agent,
                "messages": failed.errors,
                "completed_agents": list(context.results),
            },
        }

