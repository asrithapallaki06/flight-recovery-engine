"""Tests that hit the real API endpoints, the same way the dashboard does."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_model_beats_the_baseline():
    metrics = client.get("/api/model").json()
    assert metrics["model_auc"] > metrics["baseline_auc"]


def test_simulate_returns_all_three_strategies():
    resp = client.post("/api/simulate", json={"ground_stop_start": 14, "ground_stop_end": 17,
                                              "reserve_crews": 6, "use_risk": True})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["strategies"]) == {"original", "greedy", "optimized"}
    for s in body["strategies"].values():
        assert s["metrics"]["completed"] + s["metrics"]["cancelled"] == s["metrics"]["flights"]


def test_simulate_rejects_a_backwards_ground_stop():
    resp = client.post("/api/simulate", json={"ground_stop_start": 17, "ground_stop_end": 14})
    assert resp.status_code == 422
