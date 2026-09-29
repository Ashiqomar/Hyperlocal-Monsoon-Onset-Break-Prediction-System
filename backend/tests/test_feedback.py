from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models import Feedback
from app.services.review import review_store


@pytest.fixture(autouse=True)
def clean() -> Iterator[None]:
    def wipe() -> None:
        review_store.clear()
        with SessionLocal() as db:
            db.execute(delete(Feedback))
            db.commit()

    wipe()
    yield
    wipe()


def submit(client: TestClient, **body) -> dict:
    res = client.post("/feedback", json={"rain_occurred": True, "action_taken": "sowed", **body})
    assert res.status_code == 201, res.text
    return res.json()


def test_submit_stores_report_and_advice_snapshot(client: TestClient) -> None:
    decision = client.get("/decision/GP014").json()
    fb = submit(client, panchayat_id="GP014", rain_occurred=False, action_taken="waited", note="  soil still dry  ")

    assert fb["id"] > 0
    assert fb["panchayat_name"] and fb["block_name"]
    assert fb["crop"] == "cotton"
    assert fb["rain_occurred"] is False
    assert fb["action_taken"] == "waited"
    assert fb["note"] == "soil still dry"
    assert fb["advised_action"] == decision["escalation"]["final_action"]
    assert fb["model_action"] == decision["recommendation"]["action"]
    assert fb["model_confidence"] == decision["recommendation"]["confidence"]
    assert fb["advice_status"] == decision["escalation"]["status"]


def test_snapshot_uses_officer_override(client: TestClient) -> None:
    item = client.get("/review-queue", params={"status": "pending"}).json()[0]
    pid = item["panchayat"]["id"]
    new_action = "WAIT" if item["recommended_action"] != "WAIT" else "SOW"
    client.post(f"/review-queue/{item['id']}/override", json={"action": new_action, "note": "local conditions"})

    fb = submit(client, panchayat_id=pid, action_taken="waited" if new_action == "WAIT" else "sowed")
    assert fb["advised_action"] == new_action
    assert fb["model_action"] == item["recommended_action"]
    assert fb["advice_status"] == "overridden"
    assert fb["followed_advice"] is True


@pytest.mark.parametrize(
    ("action_taken", "followed"), [("sowed", False), ("waited", True), ("nothing", True), ("sprayed", False)]
)
def test_followed_advice_is_derived(client: TestClient, action_taken: str, followed: bool) -> None:
    # Force a WAIT advice via override so the expectation doesn't depend on today's data.
    item = client.get("/review-queue", params={"status": "pending"}).json()[0]
    if item["recommended_action"] == "WAIT":
        client.post(f"/review-queue/{item['id']}/approve", json={})
    else:
        client.post(f"/review-queue/{item['id']}/override", json={"action": "WAIT", "note": "test"})
    fb = submit(client, panchayat_id=item["panchayat"]["id"], action_taken=action_taken)
    assert fb["followed_advice"] is followed


def test_unmodeled_crop_has_no_advice_snapshot(client: TestClient) -> None:
    fb = submit(client, panchayat_id="GP001")  # onion
    assert fb["advised_action"] is None
    assert fb["model_action"] is None
    assert fb["followed_advice"] is None


def test_list_is_newest_first_and_filterable(client: TestClient) -> None:
    first = submit(client, panchayat_id="GP014")
    second = submit(client, panchayat_id="GP001")
    third = submit(client, panchayat_id="GP014", action_taken="nothing")

    rows = client.get("/feedback").json()
    assert [r["id"] for r in rows] == [third["id"], second["id"], first["id"]]
    assert [r["id"] for r in client.get("/feedback", params={"limit": 2}).json()] == [third["id"], second["id"]]
    assert {r["panchayat_id"] for r in client.get("/feedback", params={"panchayat_id": "GP014"}).json()} == {"GP014"}


def test_validation(client: TestClient) -> None:
    assert client.post("/feedback", json={"panchayat_id": "GP999", "rain_occurred": True, "action_taken": "sowed"}).status_code == 404
    bad = [
        {"panchayat_id": "GP014", "action_taken": "sowed"},  # rain_occurred missing
        {"panchayat_id": "GP014", "rain_occurred": True, "action_taken": "harvested"},  # unknown action
        {"panchayat_id": "GP014", "rain_occurred": True, "action_taken": "sowed", "note": "x" * 501},
    ]
    for body in bad:
        assert client.post("/feedback", json=body).status_code == 422
    assert client.get("/feedback", params={"limit": 0}).status_code == 422


def test_timestamps_are_utc(client: TestClient) -> None:
    submit(client, panchayat_id="GP014")
    stamp = client.get("/feedback").json()[0]["submitted_at"]
    assert stamp.endswith("Z") or stamp.endswith("+00:00")
