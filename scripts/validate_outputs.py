"""Validate every file in output/ before packaging.

Checks the directory as a whole (exactly EC_001..EC_050, no stray files) on
top of the per-case checks in src/verifier/schema_validator.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.verifier.agent import load_source_data  # noqa: E402
from src.verifier.schema_validator import validate_output  # noqa: E402

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

EXPECTED_CASE_IDS = [f"EC_{i:03d}" for i in range(1, 51)]


def validate_all_outputs(output_dir: Path = OUTPUT_DIR, data_dir: Path = DATA_DIR) -> bool:
    source_data = load_source_data(data_dir)
    report: dict[str, list[str]] = {}

    expected_names = {f"{case_id}.json" for case_id in EXPECTED_CASE_IDS}
    present_names = {p.name for p in output_dir.glob("*.json")}

    extra_files = sorted(present_names - expected_names)
    missing_files = sorted(expected_names - present_names)
    if extra_files:
        report["_directory"] = report.get("_directory", []) + [f"unexpected file(s): {extra_files}"]
    if missing_files:
        report["_directory"] = report.get("_directory", []) + [f"missing file(s): {missing_files}"]

    for case_id in EXPECTED_CASE_IDS:
        path = output_dir / f"{case_id}.json"
        if not path.exists():
            continue
        try:
            output = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report[case_id] = [f"invalid JSON: {exc}"]
            continue

        errors: list[str] = []
        if output.get("case_id") != case_id:
            errors.append(f"case_id '{output.get('case_id')}' does not match filename '{case_id}'")
        errors += validate_output(output, source_data)
        if errors:
            report[case_id] = errors

    if report:
        for key, errors in report.items():
            print(f"[{key}]")
            for err in errors:
                print(f"  - {err}")
    else:
        print(f"All {len(EXPECTED_CASE_IDS)} outputs passed validation.")

    return not report


if __name__ == "__main__":
    sys.exit(0 if validate_all_outputs() else 1)
