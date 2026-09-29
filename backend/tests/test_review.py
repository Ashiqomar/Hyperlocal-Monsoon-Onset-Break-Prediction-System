from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.data.synthetic import BLOCKS
from app.models import Block
from app.schemas.decision import Action, DecisionStatus
from app.schemas.twin import Scenario, TwinResponse
from app.services import decision as decision_service
from app.services.decision import build_decision
from app.services.review import review_store


@pytest.fixture(autouse=True)
def clean_store() -> Iterator[None]:
    review_store.clear()
    yield
    review_store.clear()


def queue(client: TestClient, status: str = "all") -> list[dict]:
    res = client.get("/review-queue", params={"status": status})
    assert res.status_code == 200, res.text
    return res.json()


def first_pending(client: TestClient) -> dict:
    items = queue(client, "pending")
    assert items, "expected at least one flagged decision in the synthetic data"
    return items[0]


# --- Escalation rules -------------------------------------------------------


def _twin_and_block(client: TestClient, pid: str = "GP014") -> tuple[TwinResponse, Block]:
    twin = TwinResponse.model_validate(client.get(f"/twin/{pid}").json())
    spec = next(b for b in BLOCKS if b.id == twin.panchayat.block_id)
    return twin, Block(id=spec.id, rain_day_prob=spec.rain_day_prob, rain_day_mean_mm=spec.rain_day_mean_mm)


def test_certain_normal_season_is_auto_approved(client: TestClient) -> None:
    twin, block = _twin_and_block(client)
    for s in twin.scenarios:
        s.probability = 1.0 if s.scenario == Scenario.NORMAL else 0.0
    esc = build_decision(twin, block).escalation
    assert not esc.needs_officer_review
    assert esc.status == DecisionStatus.AUTO_APPROVED
    assert esc.review_id is None


def test_low_confidence_is_flagged(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    twin, block = _twin_and_block(client)
    monkeypatch.setattr(decision_service, "LOW_CONFIDENCE", 1.01)  # everything is "low"
    monkeypatch.setattr(decision_service, "HIGH_IMPACT_PROFIT_SHARE", 99.0)  # nothing is "high impact"
    esc = build_decision(twin, block).escalation
    assert [r.code for r in esc.reasons] == ["low_confidence"]
    assert esc.status == DecisionStatus.NEEDS_OFFICER_REVIEW


def test_high_impact_cost_is_flagged(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # A certainly-dry season: the best action (WAIT) still loses ~75% of a normal season's profit.
    twin, block = _twin_and_block(client)
    for s in twin.scenarios:
        s.probability = 1.0 if s.scenario == Scenario.DRY else 0.0
    monkeypatch.setattr(decision_service, "LOW_CONFIDENCE", 0.0)

    monkeypatch.setattr(decision_service, "HIGH_IMPACT_PROFIT_SHARE", 1.0)
    assert build_decision(twin, block).escalation.reasons == []

    monkeypatch.setattr(decision_service, "HIGH_IMPACT_PROFIT_SHARE", 0.5)
    d = build_decision(twin, block)
    assert [r.code for r in d.escalation.reasons] == ["high_impact_cost"]
    assert "100% chance (dry)" in d.escalation.reasons[0].message
    assert d.escalation.review_id == f"GP014:cotton:{twin.issued_on.isoformat()}"


def test_decision_includes_escalation(client: TestClient) -> None:
    esc = client.get("/decision/GP014").json()["escalation"]
    assert esc["status"] in {s.value for s in DecisionStatus}
    assert esc["needs_officer_review"] == bool(esc["reasons"])


# --- Queue ---------------------------------------------------------------------


def test_queue_lists_only_flagged_primary_crop_decisions(client: TestClient) -> None:
    items = queue(client)
    assert items
    for item in items:
        assert item["reasons"]
        assert item["status"] == DecisionStatus.NEEDS_OFFICER_REVIEW
        assert item["crop"] == item["panchayat"]["primary_crop"]
        assert item["final_action"] == item["recommended_action"]
    assert queue(client, "reviewed") == []


def test_approve_updates_status_everywhere(client: TestClient) -> None:
    item = first_pending(client)
    res = client.post(f"/review-queue/{item['id']}/approve", json={"note": "Checked with block officer"})
    assert res.status_code == 200, res.text
    approved = res.json()
    assert approved["status"] == DecisionStatus.APPROVED
    assert approved["final_action"] == item["recommended_action"]
    assert approved["review"]["note"] == "Checked with block officer"

    pid = item["panchayat"]["id"]
    esc = client.get(f"/decision/{pid}").json()["escalation"]
    assert esc["status"] == DecisionStatus.APPROVED
    assert item["id"] not in [i["id"] for i in queue(client, "pending")]
    assert item["id"] in [i["id"] for i in queue(client, "reviewed")]


def test_override_changes_final_action_and_map(client: TestClient) -> None:
    item = first_pending(client)
    new_action = next(a for a in Action if a != item["recommended_action"])
    res = client.post(
        f"/review-queue/{item['id']}/override", json={"action": new_action, "note": "Local rain gauge disagrees"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == DecisionStatus.OVERRIDDEN
    assert res.json()["final_action"] == new_action

    pid = item["panchayat"]["id"]
    decision = client.get(f"/decision/{pid}").json()
    assert decision["escalation"]["final_action"] == new_action
    # The model's recommendation itself is preserved for audit.
    assert decision["recommendation"]["action"] == item["recommended_action"]
    marker = next(s for s in client.get("/decisions").json() if s["panchayat"]["id"] == pid)
    assert marker["action"] == new_action
    assert marker["status"] == DecisionStatus.OVERRIDDEN


def test_override_validation(client: TestClient) -> None:
    item = first_pending(client)
    url = f"/review-queue/{item['id']}/override"
    # Same action as recommended -> should approve instead.
    assert client.post(url, json={"action": item["recommended_action"], "note": "same"}).status_code == 422
    # A reason is required.
    other = next(a for a in Action if a != item["recommended_action"])
    assert client.post(url, json={"action": other}).status_code == 422
    assert client.post(url, json={"action": other, "note": ""}).status_code == 422


def test_review_errors(client: TestClient) -> None:
    assert client.post("/review-queue/garbage/approve", json={}).status_code == 404
    assert client.post(f"/review-queue/GP999:cotton:{date.today()}/approve", json={}).status_code == 404

    item = first_pending(client)
    pid, crop, _ = item["id"].split(":")
    yesterday = date.today() - timedelta(days=1)
    assert client.post(f"/review-queue/{pid}:{crop}:{yesterday}/approve", json={}).status_code == 409


def test_unflagged_decision_cannot_be_reviewed(client: TestClient) -> None:
    flagged = {i["panchayat"]["id"] for i in queue(client)}
    unflagged = next(
        (s for s in client.get("/decisions").json() if s["modeled"] and s["panchayat"]["id"] not in flagged), None
    )
    if unflagged is None:
        pytest.skip("every modelled decision is flagged in today's synthetic data")
    rid = f"{unflagged['panchayat']['id']}:{unflagged['crop']}:{date.today()}"
    assert client.post(f"/review-queue/{rid}/approve", json={}).status_code == 409
