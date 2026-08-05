"""Zip output/ into the submission archive. Refuses to package on validation failure."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_outputs import EXPECTED_CASE_IDS, OUTPUT_DIR, validate_all_outputs  # noqa: E402

DEFAULT_ZIP_PATH = ROOT / "output.zip"


def package_submission(output_dir: Path = OUTPUT_DIR, zip_path: Path = DEFAULT_ZIP_PATH) -> Path:
    if not validate_all_outputs(output_dir):
        raise SystemExit("Validation failed, fix the reported errors before packaging.")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for case_id in EXPECTED_CASE_IDS:
            file_path = output_dir / f"{case_id}.json"
            zf.write(file_path, arcname=f"output/{case_id}.json")

    print(f"Wrote {zip_path}")
    return zip_path


if __name__ == "__main__":
    package_submission()
