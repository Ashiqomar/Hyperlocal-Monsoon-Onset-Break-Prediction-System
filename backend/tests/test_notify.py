import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.schemas.decision import Action
from app.services.review import review_store


@pytest.fixture(autouse=True)
def clean_store() -> Iterator[None]:
    review_store.clear()
    yield
    review_store.clear()


def pending_panchayat(client: TestClient) -> dict:
    items = client.get("/review-queue", params={"status": "pending"}).json()
    assert items, "expected a flagged decision in the synthetic data"
    return items[0]


def unflagged_modeled_panchayat(client: TestClient) -> str:
    rows = client.get("/decisions").json()
    row = next((r for r in rows if r["modeled"] and r["status"] == "auto_approved"), None)
    if row is None:
        pytest.skip("every modelled decision is flagged in today's synthetic data")
    return row["panchayat"]["id"]


def test_preview_shape(client: TestClient) -> None:
    pid = unflagged_modeled_panchayat(client)
    msg = client.get(f"/notify/{pid}").json()
    assert msg["channel"] == "whatsapp"
    assert msg["language"] == "en"
    assert msg["can_send"] is True
    assert msg["char_count"] == len(msg["text"]) < 1000  # short, well under WhatsApp's 4096 limit
    assert msg["farmer_url"].endswith(f"/farmer/{pid}")
    assert msg["farmer_url"] in msg["text"]
    assert msg["translations"] == [{"language": "mr", "language_name": "Marathi", "status": "pending", "text": None}]


def test_preview_does_not_log(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.notify"):
        client.get(f"/notify/{unflagged_modeled_panchayat(client)}")
    assert not [r for r in caplog.records if r.name == "app.notify"]


def test_send_logs_instead_of_sending(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    pid = unflagged_modeled_panchayat(client)
    with caplog.at_level(logging.INFO, logger="app.notify"):
        res = client.post(f"/notify/{pid}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["delivery"]["provider"] == "log"
    assert body["delivery"]["status"] == "logged"
    logged = [r for r in caplog.records if r.name == "app.notify"]
    assert len(logged) == 1
    assert body["message"]["text"] in logged[0].getMessage()


def test_flagged_decision_cannot_be_sent_until_reviewed(client: TestClient) -> None:
    item = pending_panchayat(client)
    pid = item["panchayat"]["id"]

    preview = client.get(f"/notify/{pid}").json()
    assert preview["can_send"] is False
    assert "review" in preview["blocked_reason"]
    assert client.post(f"/notify/{pid}").status_code == 409

    client.post(f"/review-queue/{item['id']}/approve", json={})
    res = client.post(f"/notify/{pid}")
    assert res.status_code == 200, res.text
    assert "Checked by your agriculture officer" in res.json()["message"]["text"]


def test_message_uses_officer_override(client: TestClient) -> None:
    item = pending_panchayat(client)
    pid = item["panchayat"]["id"]
    new_action = Action.WAIT if item["recommended_action"] != Action.WAIT else Action.SOW
    client.post(f"/review-queue/{item['id']}/override", json={"action": new_action, "note": "local conditions"})

    msg = client.get(f"/notify/{pid}").json()
    assert msg["final_action"] == new_action
    headline = {"WAIT": "Wait before sowing", "SOW": "Good time to sow"}[new_action]
    assert headline in msg["text"]
    assert "Updated by your agriculture officer" in msg["text"]


def test_unmodeled_crop_gets_weather_only_message(client: TestClient) -> None:
    msg = client.get("/notify/GP001").json()  # onion: no advice model
    assert msg["decision_status"] is None
    assert msg["final_action"] is None
    assert "Advice for onion is coming soon" in msg["text"]
    assert "This week:" in msg["text"]
    assert msg["can_send"] is True


def test_unknown_panchayat(client: TestClient) -> None:
    assert client.get("/notify/GP999").status_code == 404
    assert client.post("/notify/GP999").status_code == 404
