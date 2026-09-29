"""Static crop-suitability factors (soil, water, irrigation).

Illustrative values reflecting general Maharashtra agronomy; replace with
agronomist-validated tables before real use.
"""

from app.schemas.geo import Crop, IrrigationType, SoilType

S = SoilType

# 0-1 fit of each soil for each crop.
SOIL_FIT: dict[Crop, dict[SoilType, float]] = {
    # Classic "black cotton soil": deep, moisture-retentive vertisols.
    Crop.COTTON: {S.DEEP_BLACK: 1.0, S.MEDIUM_BLACK: 0.85, S.SHALLOW_BLACK: 0.55, S.RED_LOAMY: 0.5, S.LATERITE: 0.2},
    # Needs good drainage; deep black soils can waterlog.
    Crop.SOYBEAN: {S.MEDIUM_BLACK: 1.0, S.DEEP_BLACK: 0.9, S.SHALLOW_BLACK: 0.6, S.RED_LOAMY: 0.6, S.LATERITE: 0.3},
    # Konkan paddy is grown on laterite and red soils; heavy clays hold standing water.
    Crop.PADDY: {S.LATERITE: 0.85, S.RED_LOAMY: 0.75, S.DEEP_BLACK: 0.7, S.MEDIUM_BLACK: 0.5, S.SHALLOW_BLACK: 0.3},
}

# Seasonal (Jun-Sep) rainfall range, in mm, in which the rainfed crop does well.
WATER_RANGE_MM: dict[Crop, tuple[int, int]] = {
    Crop.COTTON: (600, 1200),
    Crop.SOYBEAN: (500, 900),
    Crop.PADDY: (1200, 4000),
}

# Share of a rainfall *deficit* that irrigation can make up. It cannot fix excess rain.
IRRIGATION_DEFICIT_COVER: dict[IrrigationType, float] = {
    IrrigationType.RAINFED: 0.0,
    IrrigationType.OPEN_WELL: 0.4,
    IrrigationType.TANK: 0.4,
    IrrigationType.BOREWELL: 0.5,
    IrrigationType.CANAL: 0.6,
    IrrigationType.DRIP: 0.7,
}
