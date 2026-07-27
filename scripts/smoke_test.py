"""Smoke test: the real keyless business loop against a live instance (Standard 2).

Creates a project, imports the golden claimed items and commit records, computes drift,
builds the brief, and reads both back — asserting non-empty, schema-valid data at every
step, including that the planted drifter from the golden case ranks highest. No LLM key,
no mock data: this is the deterministic product path end to end.
"""
import json
import os
import sys
from pathlib import Path

import httpx

BASE = f"http://{os.getenv('API_HOST', '127.0.0.1')}:{os.getenv('API_PORT', '8000')}"
TOKEN = os.getenv("SMOKE_TEST_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GOLDEN = (Path(__file__).resolve().parent.parent / "data" / "synthetic" / "golden" /
          "golden.json")


def post(path: str, body: dict | None = None):
    r = httpx.post(BASE + path, json=body, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), f"POST {path} -> {r.status_code}: {r.text[:200]}"
    return r.json()


def get(path: str):
    r = httpx.get(BASE + path, headers=HEADERS, timeout=10)
    r.raise_for_status()
    body = r.json()
    assert body, f"{path} returned an empty body"
    return body


def main():
    get("/health")

    case = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"][0]
    ws = [{"key": k, "paths": v} for k, v in case["workstreams"].items()]
    pid = post("/api/v1/projects",
               {"name": f"smoke-{case['project']}", "workstreams": ws})["project_id"]

    imported = post(f"/api/v1/projects/{pid}/claimed/import",
                    {"items": case["claimed"]})["imported"]
    assert imported == len(case["claimed"]), "claimed import count mismatch"
    obs = post(f"/api/v1/projects/{pid}/observed/import", {"commits": case["commits"]})
    assert obs["imported"] == len(case["commits"]), "observed import count mismatch"

    computed = post(f"/api/v1/projects/{pid}/drift/compute")
    assert computed["rows"], "drift compute returned no rows"
    assert computed["rows"][0]["workstream"] == case["planted_drifting"], \
        "planted drifter did not rank highest"

    brief = post(f"/api/v1/projects/{pid}/brief")
    assert brief["markdown"].startswith("# Morning Brief"), "brief markdown malformed"
    assert brief["stats"] > 0, "brief stored no stats"

    drift = get(f"/api/v1/projects/{pid}/drift")
    assert drift["rows"], "stored drift read-back empty"
    latest = get(f"/api/v1/projects/{pid}/brief")
    assert latest["brief"]["markdown"] and latest["stats"], "brief read-back empty"

    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
