"""Export the FastAPI OpenAPI document without starting a server.

Usage (from the repository root):

    python scripts/export-openapi.py

The generated file is consumed by `openapi-typescript` in apps/web.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"
OUTPUT = ROOT / "apps" / "web" / "lib" / "openapi.json"

sys.path.insert(0, str(API_DIR))

# Import-time settings should not create runtime folders inside the repo.
import os  # noqa: E402

os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="cbl-openapi-"))
# Keep the published contract independent of a developer's local .env.
os.environ["APP_NAME"] = "Campus Book Loop"

from app.main import app  # noqa: E402


def main() -> None:
    document = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
