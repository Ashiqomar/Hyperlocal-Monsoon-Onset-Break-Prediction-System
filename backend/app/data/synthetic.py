"""Synthetic Blocks and Panchayats in Maharashtra.

Block names and centroids are real talukas spread across the state's agro-climatic
zones (Konkan, Western Maharashtra rain-shadow, North Maharashtra, Marathwada,
Vidarbha). Panchayat names, locations and attributes are fake: generated around
each block centroid with a fixed seed, so every database gets identical data.
"""

import random
from dataclasses import dataclass

from app.schemas.geo import Crop, IrrigationType, SoilType

DATASET_SEED = 2026
PANCHAYATS_PER_BLOCK = 3
# Max offset of a panchayat from its block centroid, in degrees (~8 km).
JITTER_DEG = 0.07


@dataclass(frozen=True)
class BlockSpec:
    id: str
    name: str
    district: str
    lat: float
    lon: float
    rain_day_prob: float  # chance a monsoon day is wet
    rain_day_mean_mm: float  # mean rainfall on a wet day
    soils: tuple[SoilType, ...]
    irrigation: tuple[IrrigationType, ...]
    crops: tuple[Crop, ...]


S, I, C = SoilType, IrrigationType, Crop

BLOCKS: tuple[BlockSpec, ...] = (
    BlockSpec("BLK01", "Baramati", "Pune", 18.151, 74.577, 0.35, 9.0,
              (S.MEDIUM_BLACK, S.SHALLOW_BLACK), (I.CANAL, I.BOREWELL, I.DRIP), (C.SUGARCANE, C.BAJRA, C.ONION)),
    BlockSpec("BLK02", "Sangamner", "Ahilyanagar", 19.567, 74.211, 0.40, 9.0,
              (S.MEDIUM_BLACK, S.SHALLOW_BLACK), (I.RAINFED, I.OPEN_WELL, I.CANAL), (C.BAJRA, C.SOYBEAN, C.ONION)),
    BlockSpec("BLK03", "Niphad", "Nashik", 20.080, 74.110, 0.50, 11.0,
              (S.DEEP_BLACK, S.MEDIUM_BLACK), (I.CANAL, I.DRIP, I.OPEN_WELL), (C.GRAPES, C.ONION, C.SOYBEAN)),
    BlockSpec("BLK04", "Paithan", "Chhatrapati Sambhajinagar", 19.476, 75.385, 0.45, 10.0,
              (S.DEEP_BLACK, S.MEDIUM_BLACK), (I.RAINFED, I.CANAL, I.BOREWELL), (C.COTTON, C.SOYBEAN, C.TUR)),
    BlockSpec("BLK05", "Ambajogai", "Beed", 18.733, 76.386, 0.45, 11.0,
              (S.MEDIUM_BLACK, S.SHALLOW_BLACK), (I.RAINFED, I.BOREWELL), (C.SOYBEAN, C.TUR, C.COTTON)),
    BlockSpec("BLK06", "Ausa", "Latur", 18.253, 76.499, 0.47, 11.0,
              (S.DEEP_BLACK, S.MEDIUM_BLACK), (I.RAINFED, I.BOREWELL, I.TANK), (C.SOYBEAN, C.TUR, C.JOWAR)),
    BlockSpec("BLK07", "Pandharpur", "Solapur", 17.678, 75.328, 0.33, 9.0,
              (S.MEDIUM_BLACK, S.SHALLOW_BLACK), (I.CANAL, I.BOREWELL, I.RAINFED), (C.SUGARCANE, C.JOWAR, C.TUR)),
    BlockSpec("BLK08", "Pusad", "Yavatmal", 19.913, 77.573, 0.55, 14.0,
              (S.DEEP_BLACK, S.MEDIUM_BLACK), (I.RAINFED, I.OPEN_WELL), (C.COTTON, C.SOYBEAN, C.TUR)),
    BlockSpec("BLK09", "Hinganghat", "Wardha", 20.548, 78.839, 0.55, 14.0,
              (S.DEEP_BLACK, S.MEDIUM_BLACK), (I.RAINFED, I.TANK, I.CANAL), (C.COTTON, C.SOYBEAN, C.TUR)),
    BlockSpec("BLK10", "Chiplun", "Ratnagiri", 17.533, 73.516, 0.80, 32.0,
              (S.LATERITE, S.RED_LOAMY), (I.RAINFED, I.TANK), (C.PADDY, C.NACHNI)),
)

# Common Maharashtra village-name patterns; assigned in order, 3 per block.
PANCHAYAT_NAMES: tuple[str, ...] = (
    "Katewadi", "Malegaon Khurd", "Pimpli",
    "Nimgaon", "Wadgaon Pan", "Ghulewadi",
    "Pimpalgaon", "Shirasgaon", "Kasbe Sukene",
    "Dhangaon", "Borgaon", "Chincholi",
    "Sawargaon", "Deulgaon", "Mangrul",
    "Takli", "Belkund", "Jambhulwadi",
    "Mhasawad", "Karkamb", "Sonwadi",
    "Dhanora", "Kinhi", "Hivra",
    "Warud", "Yelgaon", "Kolhewadi",
    "Kondhwe", "Pedhe", "Dalwatne",
)

assert len(PANCHAYAT_NAMES) == len(BLOCKS) * PANCHAYATS_PER_BLOCK


def generate_panchayats() -> list[dict]:
    rng = random.Random(DATASET_SEED)
    rows: list[dict] = []
    names = iter(PANCHAYAT_NAMES)
    for block in BLOCKS:
        for _ in range(PANCHAYATS_PER_BLOCK):
            rows.append(
                {
                    "id": f"GP{len(rows) + 1:03d}",
                    "name": next(names),
                    "block_id": block.id,
                    "lat": round(block.lat + rng.uniform(-JITTER_DEG, JITTER_DEG), 4),
                    "lon": round(block.lon + rng.uniform(-JITTER_DEG, JITTER_DEG), 4),
                    "soil_type": rng.choice(block.soils).value,
                    "irrigation_type": rng.choice(block.irrigation).value,
                    "primary_crop": rng.choice(block.crops).value,
                }
            )
    return rows
