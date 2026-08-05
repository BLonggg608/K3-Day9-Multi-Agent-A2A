"""Run the Coordinator over every case in input/, writing output/ and trace.jsonl.

Requires all domain agents to exist (see architecture.md ownership table). If a
teammate's module isn't in place yet, this fails fast naming the missing piece
instead of silently producing partial output — per chiaviec.md, the Verifier
integrates modules but does not implement domain logic itself.

Expected agent classes (each implementing the shared Agent protocol from
src/shared/contracts.py: a `name` attribute and `analyze(context) -> AgentResult`):
    src/order_seller/agent.py        -> OrderSellerAgent   (Thanh vien 2)
    src/payment/agent.py             -> PaymentAgent        (Thanh vien 3)
    src/delivery_policy/delivery_agent.py -> DeliveryAgent  (Thanh vien 4)
    src/delivery_policy/policy_agent.py   -> PolicyAgent    (Thanh vien 4)
"""

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.coordinator.agent import Coordinator  # noqa: E402
from src.shared.contracts import Agent  # noqa: E402
from src.shared.llm_client import OpenAIAuditClient  # noqa: E402
from src.verifier.agent import VerifierAgent  # noqa: E402

INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TRACE_PATH = ROOT / "logging" / "trace.jsonl"

_AGENT_SPECS = [
    ("src.order_seller.agent", "OrderSellerAgent", "Thanh vien 2"),
    ("src.payment.agent", "PaymentAgent", "Thanh vien 3"),
    ("src.delivery_policy.delivery_agent", "DeliveryAgent", "Thanh vien 4"),
    ("src.delivery_policy.policy_agent", "PolicyAgent", "Thanh vien 4"),
]


def _build_domain_agents() -> list[Agent]:
    agents: list[Agent] = []
    missing: list[str] = []
    for module_path, class_name, owner in _AGENT_SPECS:
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as exc:
            if exc.name == module_path:
                missing.append(f"{module_path}.{class_name} (owned by {owner})")
                continue
            raise SystemExit(
                f"Cannot import {module_path}: dependency {exc.name!r} is missing. "
                "Install dependencies with: python -m pip install -r requirements.txt"
            ) from exc
        except ImportError as exc:
            raise SystemExit(f"Cannot import {module_path}: {exc}") from exc

        try:
            agent_cls = getattr(module, class_name)
        except AttributeError:
            missing.append(f"{module_path}.{class_name} (owned by {owner})")
            continue
        agents.append(agent_cls())

    if missing:
        raise SystemExit(
            "Pipeline cannot run, missing agent implementation(s):\n"
            + "\n".join(f"  - {m}" for m in missing)
        )
    return agents


def run_pipeline(
    input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR, trace_path: Path = TRACE_PATH
) -> None:
    domain_agents = _build_domain_agents()
    llm_client = OpenAIAuditClient()
    coordinator = Coordinator(
        agents=domain_agents,
        verifier=VerifierAgent(),
        llm_client=llm_client,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    case_files = sorted(input_dir.glob("EC_*.json"))
    if not case_files:
        raise SystemExit(f"No input cases found in {input_dir}")

    with open(trace_path, "w", encoding="utf-8") as trace_file:
        for case_path in case_files:
            case: dict[str, Any] = json.loads(case_path.read_text(encoding="utf-8"))
            started = time.time()
            output = coordinator.process_case(case)
            duration_ms = round((time.time() - started) * 1000, 2)

            if coordinator.last_llm_error is not None:
                raise RuntimeError(
                    f"LLM audit failed for {case.get('case_id')}: "
                    f"{coordinator.last_llm_error}"
                )
            if not coordinator.last_llm_rationale:
                raise RuntimeError(
                    f"LLM audit produced no rationale for {case.get('case_id')}"
                )

            (output_dir / case_path.name).write_text(
                json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            trace_file.write(
                json.dumps(
                    {
                        "case_id": case.get("case_id"),
                        "duration_ms": duration_ms,
                        "ok": "error" not in output,
                        "verification_errors": output.get("_verification_errors", []),
                        "llm": {
                            "provider": llm_client.provider,
                            "model": llm_client.model,
                            "parameter_size": llm_client.parameter_size,
                            "called": True,
                            "rationale": coordinator.last_llm_rationale,
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(f"{case_path.name}: done in {duration_ms}ms")


if __name__ == "__main__":
    run_pipeline()
