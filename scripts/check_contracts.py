"""Standard 6 gate: every contracts.md row marked `implemented` must exist in the live
OpenAPI spec at /openapi.json. Fails loudly on drift so the contracts table cannot rot
into a claim no CI job backs (run by the CI smoke job against the compose stack).

Usage: python scripts/check_contracts.py [base_url]    (default http://127.0.0.1:8000)

Path parameter names are normalized ({project_id} and {pid} both become {}) because the
contract documents intent while route decorators pick their own variable names.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
_ROW = re.compile(
    r"^\|[^|]+\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`\s*\|\s*implemented\s*\|")
_PARAM = re.compile(r"\{[^}]+\}")


def _normalize(path: str) -> str:
    return _PARAM.sub("{}", path)


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    spec = httpx.get(f"{base}/openapi.json", timeout=10).json()
    live = {(m.upper(), _normalize(p)) for p, ops in spec["paths"].items() for m in ops}
    rows: list[tuple[str, str]] = []
    for line in (ROOT / "contracts.md").read_text(encoding="utf-8").splitlines():
        m = _ROW.match(line)
        if m:
            rows.append((m.group(1).upper(), _normalize(m.group(2))))
    if not rows:
        print("CONTRACTS CHECK FAILED: no `implemented` rows parsed from contracts.md",
              file=sys.stderr)
        sys.exit(1)
    missing = [r for r in rows if r not in live]
    if missing:
        print(f"CONTRACTS CHECK FAILED: implemented rows missing from /openapi.json: "
              f"{missing}", file=sys.stderr)
        sys.exit(1)
    print(f"CONTRACTS OK: {len(rows)} implemented rows present in the live OpenAPI spec")


if __name__ == "__main__":
    main()
