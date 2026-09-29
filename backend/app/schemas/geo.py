from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SoilType(StrEnum):
    DEEP_BLACK = "deep_black"
    MEDIUM_BLACK = "medium_black"
    SHALLOW_BLACK = "shallow_black"
    LATERITE = "laterite"
    RED_LOAMY = "red_loamy"


class IrrigationType(StrEnum):
    RAINFED = "rainfed"
    CANAL = "canal"
    BOREWELL = "borewell"
    OPEN_WELL = "open_well"
    DRIP = "drip"
    TANK = "tank"


class Crop(StrEnum):
    SOYBEAN = "soybean"
    COTTON = "cotton"
    TUR = "tur"
    SUGARCANE = "sugarcane"
    JOWAR = "jowar"
    BAJRA = "bajra"
    ONION = "onion"
    GRAPES = "grapes"
    PADDY = "paddy"
    NACHNI = "nachni"


class PanchayatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    block_id: str
    block_name: str
    district: str
    lat: float
    lon: float
    soil_type: SoilType
    irrigation_type: IrrigationType
    primary_crop: Crop
