"""API tests on an injected sqlite engine (StaticPool, check_same_thread=False) with no
network and no LLM: the keyless loop is exercised end to end; the key-gated narration
endpoint is tested for its loud 503 and, separately, through an injected stub gateway."""
import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app import db
from app.main import app

GOLDEN = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "synthetic" / "golden" /
     "golden.json").read_text(encoding="utf-8"))
CASE = GOLDEN["cases"][0]


@pytest.fixture()
def client():
    engine = sa.create_engine(
        "sqlite://",
        poolclass=sa.pool.StaticPool,
        connect_args={"check_same_thread": False},   # TestClient serves on another thread
    )
    db.metadata.create_all(engine)
    db.set_engine_for_tests(engine)
    return TestClient(app)


def _seed(client) -> int:
    ws = [{"key": k, "paths": v} for k, v in CASE["workstreams"].items()]
    pid = client.post("/api/v1/projects",
                      json={"name": CASE["project"], "workstreams": ws}).json()["project_id"]
    client.post(f"/api/v1/projects/{pid}/claimed/import", json={"items": CASE["claimed"]})
    client.post(f"/api/v1/projects/{pid}/observed/import",
                json={"commits": CASE["commits"]})
    return pid


def test_full_drift_brief_loop(client):
    pid = _seed(client)
    r = client.post(f"/api/v1/projects/{pid}/drift/compute")
    assert r.status_code == 201, r.text
    rows = r.json()["rows"]
    assert rows[0]["workstream"] == CASE["planted_drifting"]
    assert all(0.0 <= row["drift_index"] <= 1.0 for row in rows)

    b = client.post(f"/api/v1/projects/{pid}/brief")
    assert b.status_code == 201, b.text
    assert b.json()["markdown"].startswith("# Morning Brief")

    stored = client.get(f"/api/v1/projects/{pid}/drift").json()
    assert stored["rows"][0]["workstream"] == CASE["planted_drifting"]
    latest = client.get(f"/api/v1/projects/{pid}/brief").json()
    assert latest["brief"]["markdown"] and latest["stats"]


def test_workstream_drift_detail(client):
    pid = _seed(client)
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    rows = client.get(f"/api/v1/projects/{pid}/drift").json()["rows"]
    assert rows, "no stored drift rows"
    # workstream ids are 1..n in insert order for this fresh sqlite db
    detail = client.get("/api/v1/workstreams/1/drift")
    assert detail.status_code == 200
    assert detail.json()["rollup"] is not None


def test_compute_requires_imports_and_brief_requires_compute(client):
    ws = [{"key": "a", "paths": ["a/"]}]
    pid = client.post("/api/v1/projects",
                      json={"name": "empty", "workstreams": ws}).json()["project_id"]
    assert client.post(f"/api/v1/projects/{pid}/drift/compute").status_code == 422
    assert client.post(f"/api/v1/projects/{pid}/brief").status_code == 422
    assert client.get(f"/api/v1/projects/{pid}/drift").status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/brief").status_code == 404


def test_import_rejects_unknown_workstreams_and_malformed_rows(client):
    ws = [{"key": "a", "paths": ["a/"]}]
    pid = client.post("/api/v1/projects",
                      json={"name": "p", "workstreams": ws}).json()["project_id"]
    r = client.post(f"/api/v1/projects/{pid}/claimed/import", json={"items": [
        {"item_key": "X-1", "workstream": "ghost", "title": "t", "status": "todo"}]})
    assert r.status_code == 422 and "ghost" in r.json()["detail"]
    r = client.post(f"/api/v1/projects/{pid}/claimed/import",
                    json={"items": [{"item_key": "X-1"}]})
    assert r.status_code == 422
    r = client.post(f"/api/v1/projects/{pid}/observed/import",
                    json={"commits": [{"sha": "tiny"}]})
    assert r.status_code == 422


def test_reimport_is_idempotent_not_append_only(client):
    """Re-delivered payloads upsert onto (workstream, item_key) / (project, sha): a
    tracker export re-imported after todo->done must not half-weight claims, and a
    re-posted commit payload must not double commit counts."""
    pid = _seed(client)
    items = [dict(i) for i in CASE["claimed"]]
    for i in items:
        i["status"] = "done"
        i.pop("claimed_progress", None)
    assert client.post(f"/api/v1/projects/{pid}/claimed/import",
                       json={"items": items}).status_code == 201
    assert client.post(f"/api/v1/projects/{pid}/observed/import",
                       json={"commits": CASE["commits"]}).status_code == 201
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    rows = client.get(f"/api/v1/projects/{pid}/drift").json()["rows"]
    for row in rows:
        assert row["status"] == "completed", row       # every claim is now done, once
        assert row["claimed_fraction"] == 1.0, row
    # one unattributed commit in the golden case; the rest exist exactly once
    assert sum(r["commit_count"] for r in rows) == len(CASE["commits"]) - 1


def test_narrate_without_key_fails_loud(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    pid = _seed(client)
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    bid = client.post(f"/api/v1/projects/{pid}/brief").json()["brief_id"]
    r = client.post(f"/api/v1/briefs/{bid}/narrate")
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]


def test_narrate_without_model_fails_loud_naming_the_slot(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_extraction", "")
    pid = _seed(client)
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    bid = client.post(f"/api/v1/projects/{pid}/brief").json()["brief_id"]
    r = client.post(f"/api/v1/briefs/{bid}/narrate")
    assert r.status_code == 503
    assert "LLM_MODEL_EXTRACTION" in r.json()["detail"]


def test_gateway_client_carries_the_configured_timeout(monkeypatch):
    from app import routes
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    gw = routes._gateway()
    assert gw._client.timeout == settings.llm_timeout_seconds


class _StubGateway:
    """Typed stub: returns schema-shaped narration citing a real stat id plus one
    fabricated sentence the deterministic gate must reject."""

    def complete(self, *, model, messages, json_schema=None, temperature=0.0):
        assert json_schema is not None, "narration must force a JSON schema"
        return {"sentences": [
            {"text": "Checkout drifts furthest.", "stat_ids": ["ws:checkout:drift"]},
            # integer stat echoed verbatim: passes only if int formatting survives the
            # database round-trip (FAILURES.md FAIL-0004 regression pin)
            {"text": "Search logged 12 commits.", "stat_ids": ["ws:search:commits"]},
            {"text": "Velocity hit 9999 units.", "stat_ids": ["ws:checkout:drift"]},
        ]}


def test_narrate_with_stub_gateway_gates_sentences(client, monkeypatch):
    from app import routes
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_extraction", "stub/model")
    monkeypatch.setattr(routes, "_gateway", lambda: _StubGateway())
    pid = _seed(client)
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    bid = client.post(f"/api/v1/projects/{pid}/brief").json()["brief_id"]
    r = client.post(f"/api/v1/briefs/{bid}/narrate")
    assert r.status_code == 201, r.text
    body = r.json()
    assert [s["text"] for s in body["accepted"]] == [
        "Checkout drifts furthest.", "Search logged 12 commits."]
    assert len(body["rejected"]) == 1 and "ungrounded" in body["rejected"][0]["reason"]
    assert body["narrative"] == "Checkout drifts furthest. Search logged 12 commits."


def test_narrate_llm_call_runs_outside_db_transaction(client, monkeypatch):
    """The gateway network call must never run inside an open DB transaction: a slow
    provider would pin a pooled connection for the whole call."""
    from app import routes
    from app.config import settings
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model_extraction", "stub/model")
    monkeypatch.setattr(routes, "_gateway", lambda: _StubGateway())
    pid = _seed(client)
    client.post(f"/api/v1/projects/{pid}/drift/compute")
    bid = client.post(f"/api/v1/projects/{pid}/brief").json()["brief_id"]

    sessions = []
    real_get_session = db.get_session

    def tracking_get_session():
        s = real_get_session()
        sessions.append(s)
        return s

    monkeypatch.setattr(db, "get_session", tracking_get_session)
    real_narrate = routes.narrate
    seen = {}

    def spy_narrate(gateway, model, markdown, stats):
        seen["open_txns"] = [s for s in sessions if s.in_transaction()]
        return real_narrate(gateway, model, markdown, stats)

    monkeypatch.setattr(routes, "narrate", spy_narrate)
    r = client.post(f"/api/v1/briefs/{bid}/narrate")
    assert r.status_code == 201, r.text
    assert seen["open_txns"] == [], "LLM call ran inside an open DB transaction"


def test_bearer_auth_enforced_when_token_set(client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "smoke_test_token", "sekrit")
    ws = [{"key": "a", "paths": []}]
    assert client.post("/api/v1/projects",
                       json={"name": "p", "workstreams": ws}).status_code == 401
    assert client.post("/api/v1/projects", json={"name": "p", "workstreams": ws},
                       headers={"Authorization": "Bearer sekrit"}).status_code == 201


def test_duplicate_workstream_keys_rejected(client):
    ws = [{"key": "a", "paths": []}, {"key": "a", "paths": []}]
    r = client.post("/api/v1/projects", json={"name": "p", "workstreams": ws})
    assert r.status_code == 422
