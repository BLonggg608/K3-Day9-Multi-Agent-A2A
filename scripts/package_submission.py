"""Build the complete submission archive after validating all outputs."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_outputs import EXPECTED_CASE_IDS, OUTPUT_DIR, validate_all_outputs  # noqa: E402

DEFAULT_ZIP_PATH = ROOT / "submission.zip"
REQUIRED_ARTIFACTS = {
    ROOT / "architecture.md": "architecture.md",
    ROOT / "logging" / "trace.jsonl": "trace.jsonl",
    ROOT / "logging" / "metadata.json": "metadata.json",
}


def package_submission(output_dir: Path = OUTPUT_DIR, zip_path: Path = DEFAULT_ZIP_PATH) -> Path:
    if not validate_all_outputs(output_dir):
        raise SystemExit("Validation failed, fix the reported errors before packaging.")

    missing_artifacts = [str(path) for path in REQUIRED_ARTIFACTS if not path.is_file()]
    if missing_artifacts:
        raise SystemExit(f"Missing required artifact(s): {missing_artifacts}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for case_id in EXPECTED_CASE_IDS:
            file_path = output_dir / f"{case_id}.json"
            # The submission archive contains the output directory with the
            # 50 required JSON files inside it.
            zf.write(file_path, arcname=f"output/{case_id}.json")
        for file_path, archive_name in REQUIRED_ARTIFACTS.items():
            zf.write(file_path, arcname=archive_name)

    print(f"Wrote {zip_path}")
    return zip_path


if __name__ == "__main__":
    package_submission()
