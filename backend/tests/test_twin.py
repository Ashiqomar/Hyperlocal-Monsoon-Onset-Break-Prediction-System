import pytest
from fastapi.testclient import TestClient

from app.schemas.twin import Scenario, TwinResponse
from app.services.twin import classify_member

# GP014 grows cotton, GP001 grows onion (no coefficients), GP028 grows paddy.
COTTON_PANCHAYAT = "GP014"
UNSUPPORTED_CROP_PANCHAYAT = "GP001"


def get_twin(client: TestClient, pid: str, **params: str) -> TwinResponse:
    res = client.get(f"/twin/{pid}", params=params)
    assert res.status_code == 200, res.text
    return TwinResponse.model_validate(res.json())


def test_twin_shape_and_probabilities(client: TestClient) -> None:
    twin = get_twin(client, COTTON_PANCHAYAT)
    assert twin.economics.crop == "cotton"
    assert [s.scenario for s in twin.scenarios] == list(Scenario)
    assert sum(s.probability for s in twin.scenarios) == pytest.approx(1.0, abs=0.01)
    assert twin.summary.most_likely_scenario == max(twin.scenarios, key=lambda s: s.probability).scenario


def test_twin_economics_are_consistent(client: TestClient) -> None:
    twin = get_twin(client, COTTON_PANCHAYAT)
    by_scenario = {s.scenario: s for s in twin.scenarios}

    normal = by_scenario[Scenario.NORMAL]
    assert normal.yield_impact_pct == 0
    assert normal.cost_impact_inr_per_ha == 0
    assert normal.expected_profit_inr_per_ha == twin.summary.baseline_profit_inr_per_ha

    for s in twin.scenarios:
        assert s.profit_p10_inr_per_ha <= s.expected_profit_inr_per_ha
        # Every adverse scenario should be worse than a normal season.
        if s.scenario != Scenario.NORMAL:
            assert s.expected_profit_inr_per_ha < normal.expected_profit_inr_per_ha
            assert s.downside_risk_inr_per_ha > normal.downside_risk_inr_per_ha

    weighted = sum(s.probability * s.expected_profit_inr_per_ha for s in twin.scenarios)
    assert twin.summary.expected_profit_inr_per_ha == pytest.approx(weighted, rel=0.01)


def test_twin_is_deterministic(client: TestClient) -> None:
    first = get_twin(client, COTTON_PANCHAYAT)
    second = get_twin(client, COTTON_PANCHAYAT)
    assert first.scenarios == second.scenarios


def test_crop_override(client: TestClient) -> None:
    twin = get_twin(client, UNSUPPORTED_CROP_PANCHAYAT, crop="soybean")
    assert twin.economics.crop == "soybean"


def test_paddy_tolerates_wet_better_than_soybean(client: TestClient) -> None:
    def wet_yield_impact(crop: str) -> float:
        twin = get_twin(client, "GP028", crop=crop)
        return next(s.yield_impact_pct for s in twin.scenarios if s.scenario == Scenario.WET)

    assert wet_yield_impact("paddy") > wet_yield_impact("soybean")


def test_unsupported_crop_returns_422(client: TestClient) -> None:
    res = client.get(f"/twin/{UNSUPPORTED_CROP_PANCHAYAT}")
    assert res.status_code == 422
    assert "cotton, soybean, paddy" in res.json()["detail"]


def test_unknown_panchayat_returns_404(client: TestClient) -> None:
    assert client.get("/twin/GP999").status_code == 404


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        # 10 mm every day for 28 days = 280 mm vs a 280 mm normal.
        ([10.0] * 28, Scenario.NORMAL),
        ([5.0] * 28, Scenario.DRY),
        ([15.0] * 28, Scenario.WET),
        # 30 mm onset in week 1, then 12 dry days, then rain.
        ([10.0] * 7 + [0.0] * 12 + [30.0] * 9, Scenario.FALSE_ONSET),
        # Same dry gap but no onset rain in week 1: not a false onset (277 mm = normal).
        ([1.0] * 7 + [0.0] * 12 + [30.0] * 9, Scenario.NORMAL),
    ],
)
def test_classify_member(days: list[float], expected: Scenario) -> None:
    assert classify_member(days, normal_total_mm=280.0) == expected
