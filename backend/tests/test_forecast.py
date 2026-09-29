from fastapi.testclient import TestClient

from app.data.synthetic import generate_panchayats
from app.schemas.forecast import ForecastResponse

# Rough Maharashtra bounding box.
MH_LAT = (15.6, 22.1)
MH_LON = (72.6, 80.9)


def test_seeded_dataset(client: TestClient) -> None:
    panchayats = client.get("/panchayats").json()
    assert len(panchayats) == 30
    assert len({p["block_id"] for p in panchayats}) == 10
    for p in panchayats:
        assert MH_LAT[0] < p["lat"] < MH_LAT[1]
        assert MH_LON[0] < p["lon"] < MH_LON[1]


def test_dataset_generation_is_deterministic() -> None:
    assert generate_panchayats() == generate_panchayats()


def test_forecast_shape(client: TestClient) -> None:
    res = client.get("/forecast/GP001")
    assert res.status_code == 200
    forecast = ForecastResponse.model_validate(res.json())
    assert forecast.panchayat.id == "GP001"
    assert [w.week for w in forecast.weeks] == [1, 2, 3, 4]
    assert forecast.weeks[0].lead_days_start == 1
    assert forecast.weeks[-1].lead_days_end == 28
    for w in forecast.weeks:
        q = w.rainfall_mm
        assert 0 <= q.p10 <= q.p50 <= q.p90


def test_forecast_is_consistent_per_panchayat(client: TestClient) -> None:
    first = client.get("/forecast/GP007").json()
    second = client.get("/forecast/GP007").json()
    assert first["weeks"] == second["weeks"]


def test_forecasts_differ_between_panchayats(client: TestClient) -> None:
    a = client.get("/forecast/GP001").json()["weeks"]
    b = client.get("/forecast/GP002").json()["weeks"]
    assert a != b


def test_konkan_is_wetter_than_rain_shadow(client: TestClient) -> None:
    def mean_p50(pid: str) -> float:
        weeks = client.get(f"/forecast/{pid}").json()["weeks"]
        return sum(w["rainfall_mm"]["p50"] for w in weeks) / len(weeks)

    # GP028-030 are in Chiplun (Konkan); GP019-021 in Pandharpur (rain shadow).
    assert mean_p50("GP028") > 3 * mean_p50("GP019")


def test_unknown_panchayat_returns_404(client: TestClient) -> None:
    assert client.get("/forecast/GP999").status_code == 404
