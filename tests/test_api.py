"""End-to-end API tests through FastAPI's TestClient (offline scripted model)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app

from .conftest import FAKE_KEY, Recorder, looping_model, make_settings, scripted_model

SHOT = {"dose_g": 18, "yield_g": 36, "time_s": 22, "grind_setting": "12", "taste": "sour", "notes": "fast, sour"}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(make_settings(tmp_path), model_override=scripted_model(Recorder())))


def test_health_never_exposes_the_key(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["api_key_configured"] is True and r.json()["provider"] == "portkey"
    assert FAKE_KEY not in r.text


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"dose_g": 0}, "dose_g"),
        ({"dose_g": -5}, "dose_g"),
        ({"dose_g": 250}, "dose_g"),
        ({"yield_g": 1000}, "yield_g"),
        ({"time_s": 0}, "time_s"),
        ({"time_s": 600}, "time_s"),
        ({"taste": "delicious"}, "taste"),
        ({"notes": "x" * 501}, "notes"),
        ({"dose_g": 30, "yield_g": 10}, "ratio"),
        ({"dose_g": "eighteen"}, "dose_g"),
    ],
)
def test_unreasonable_inputs_are_rejected(client, patch, field):
    r = client.post("/api/shots", json={**SHOT, **patch})
    assert r.status_code == 422
    assert field in r.json()["detail"]
    assert client.get("/api/shots").json() == []  # nothing was stored


def test_full_flow_record_diagnose_history_progress_usage(client):
    first = client.post("/api/shots", json=SHOT).json()
    second = client.post("/api/shots", json={**SHOT, "time_s": 29, "taste": "balanced", "grind_setting": "11"}).json()
    assert second["brew_ratio"] == 2.0

    r = client.post(f"/api/shots/{second['id']}/diagnose")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["result"]["recommended_adjustment"]["variable"] == "grind"
    assert body["tools_used"] == ["calculate_brew_ratio", "get_shot_history"]
    assert body["usage"]["input_tokens"] > 0 and body["usage"]["cost_usd"] > 0

    detail = client.get(f"/api/shots/{second['id']}").json()
    assert detail["diagnosis"]["result"]["diagnosis"] == body["result"]["diagnosis"]

    shots = client.get("/api/shots").json()
    assert [s["id"] for s in shots] == [second["id"], first["id"]]
    assert shots[0]["has_diagnosis"] and not shots[1]["has_diagnosis"]

    prog = client.get("/api/progress").json()
    assert prog["verdict"] == "improving" and prog["deltas"]["time_s"] == 7 and prog["deltas"]["grind_changed"]

    usage = client.get("/api/usage").json()
    assert usage["runs"] == 1 and usage["input_tokens"] == body["usage"]["input_tokens"]


def test_missing_api_key_gives_clear_503(tmp_path):
    c = TestClient(create_app(make_settings(tmp_path, api_key=None)))
    shot = c.post("/api/shots", json=SHOT).json()
    r = c.post(f"/api/shots/{shot['id']}/diagnose")
    assert r.status_code == 503 and "PORTKEY_API_KEY" in r.json()["detail"]


def test_failed_run_returns_502_and_is_still_logged(tmp_path):
    c = TestClient(create_app(make_settings(tmp_path), model_override=looping_model(Recorder())))
    shot = c.post("/api/shots", json=SHOT).json()
    r = c.post(f"/api/shots/{shot['id']}/diagnose")
    assert r.status_code == 502 and not r.json()["ok"]
    usage = c.get("/api/usage").json()
    assert usage["runs"] == 1 and usage["ok_runs"] == 0 and usage["input_tokens"] > 0


def test_unknown_shot_404(client):
    assert client.post("/api/shots/999/diagnose").status_code == 404
    assert client.delete("/api/shots/999").status_code == 404


def test_delete_shot(client):
    shot = client.post("/api/shots", json=SHOT).json()
    assert client.delete(f"/api/shots/{shot['id']}").status_code == 204
    assert client.get("/api/shots").json() == []
