import pytest
from fastapi.testclient import TestClient

from app.data.synthetic import BLOCKS
from app.models import Block
from app.schemas.decision import Action, DecisionResponse
from app.schemas.twin import Scenario, TwinResponse
from app.services.decision import build_decision


def get_decision(client: TestClient, pid: str, **params: str) -> DecisionResponse:
    res = client.get(f"/decision/{pid}", params=params)
    assert res.status_code == 200, res.text
    return DecisionResponse.model_validate(res.json())


def test_decision_shape(client: TestClient) -> None:
    decision = get_decision(client, "GP014")
    assert decision.crop == "cotton"
    assert [row.action for row in decision.expected_loss_table] == list(Action)
    assert sorted(row.rank for row in decision.expected_loss_table) == [1, 2, 3, 4]
    for row in decision.expected_loss_table:
        assert [s.scenario for s in row.by_scenario] == list(Scenario)


def test_expected_loss_is_probability_times_cost(client: TestClient) -> None:
    decision = get_decision(client, "GP014")
    for row in decision.expected_loss_table:
        for s in row.by_scenario:
            assert s.expected_loss_inr_per_ha == pytest.approx(s.probability * s.cost_if_wrong_inr_per_ha, abs=1)
        assert row.expected_loss_inr_per_ha == pytest.approx(
            sum(s.expected_loss_inr_per_ha for s in row.by_scenario), abs=len(row.by_scenario)
        )


def test_probabilities_match_twin(client: TestClient) -> None:
    twin = client.get("/twin/GP014").json()
    decision = get_decision(client, "GP014")
    twin_probs = {s["scenario"]: s["probability"] for s in twin["scenarios"]}
    for s in decision.expected_loss_table[0].by_scenario:
        assert s.probability == twin_probs[s.scenario]


def test_recommendation_is_lowest_expected_loss(client: TestClient) -> None:
    for pid in ("GP005", "GP006", "GP014", "GP028", "GP030"):
        decision = get_decision(client, pid, crop="soybean")
        best = min(decision.expected_loss_table, key=lambda r: r.expected_loss_inr_per_ha)
        assert decision.recommendation.action == best.action
        assert best.rank == 1


def test_sow_has_no_cost_in_a_normal_season(client: TestClient) -> None:
    decision = get_decision(client, "GP014")
    sow = next(r for r in decision.expected_loss_table if r.action == Action.SOW)
    normal = next(s for s in sow.by_scenario if s.scenario == Scenario.NORMAL)
    assert normal.cost_if_wrong_inr_per_ha == 0


def test_mostly_dry_forecast_recommends_wait(client: TestClient) -> None:
    # GP006 (Sangamner, rain shadow) has a ~70% dry-scenario probability.
    decision = get_decision(client, "GP006", crop="soybean")
    assert decision.recommendation.action == Action.WAIT


def test_scores_are_separate_fields_on_separate_scales(client: TestClient) -> None:
    body = client.get("/decision/GP014").json()
    assert 0 <= body["recommendation"]["confidence"] <= 1
    assert 0 <= body["crop_suitability"]["score"] <= 100
    # No combined score anywhere at the top level.
    assert set(body) == {
        "panchayat", "crop", "issued_on", "synthetic", "recommendation", "crop_suitability", "escalation",
        "expected_loss_table",
    }


def test_suitability_ignores_forecast_but_confidence_does_not(client: TestClient) -> None:
    twin = TwinResponse.model_validate(client.get("/twin/GP014").json())
    spec = next(b for b in BLOCKS if b.id == twin.panchayat.block_id)
    block = Block(id=spec.id, rain_day_prob=spec.rain_day_prob, rain_day_mean_mm=spec.rain_day_mean_mm)

    # Same panchayat, but a forecast that is certain to be dry.
    dry_twin = twin.model_copy(deep=True)
    for s in dry_twin.scenarios:
        s.probability = 1.0 if s.scenario == Scenario.DRY else 0.0

    original, dry = build_decision(twin, block), build_decision(dry_twin, block)
    assert dry.crop_suitability == original.crop_suitability
    assert dry.recommendation != original.recommendation


def test_suitability_reflects_agronomy(client: TestClient) -> None:
    konkan_paddy = get_decision(client, "GP028", crop="paddy").crop_suitability
    rain_shadow_paddy = get_decision(client, "GP006", crop="paddy").crop_suitability
    konkan_cotton = get_decision(client, "GP028", crop="cotton").crop_suitability
    assert konkan_paddy.score > rain_shadow_paddy.score
    assert konkan_paddy.score > konkan_cotton.score
    assert rain_shadow_paddy.rating == "low"


def test_decision_errors(client: TestClient) -> None:
    assert client.get("/decision/GP999").status_code == 404
    assert client.get("/decision/GP001").status_code == 422  # onion: no coefficients


def test_decision_summaries(client: TestClient) -> None:
    rows = client.get("/decisions").json()
    assert len(rows) == 30
    modeled = [r for r in rows if r["modeled"]]
    assert modeled and len(modeled) < 30
    for r in rows:
        if r["modeled"]:
            detail = get_decision(client, r["panchayat"]["id"])
            assert r["action"] == detail.recommendation.action
            assert r["confidence"] == detail.recommendation.confidence
            assert r["suitability_score"] == detail.crop_suitability.score
        else:
            assert r["action"] is None
