"""Cadastre schemas. Field names mirror what the frontend already reads."""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ParcelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ulpin: str
    address: str
    ward: str | None
    zone: str | None
    registered_area: str | None
    khasra_no: str | None
    migration_status: str | None


class LevelOut(BaseModel):
    """Shaped like the frontend's LEVELS + LEVEL_DETAIL entries combined."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    code: str
    label: str
    tag: str
    id3d: str = Field(validation_alias="ulpin_3d", serialization_alias="id3d")
    type: str = Field(validation_alias="property_type", serialization_alias="type")
    elevation: str
    elevation_min: float | None
    elevation_max: float | None
    area: str | None
    volume: str | None
    owner: str | None
    source: str | None
    confidence: int
    surveyed_on: str | None = None
    verified_on: str | None = None
    rights: dict = Field(default_factory=dict)
    below: bool = Field(validation_alias="below_grade", serialization_alias="below")
    airspace: bool
    conflict: bool = Field(validation_alias="has_conflict", serialization_alias="conflict")
    h: int = Field(validation_alias="render_height", serialization_alias="h")
    colors: dict


class LevelCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=60)
    tag: str = Field(min_length=1, max_length=12)
    property_type: str = Field(min_length=1, max_length=120)
    elevation: str = Field(min_length=1, max_length=60)
    elevation_min: float | None = None
    elevation_max: float | None = None
    area: str | None = Field(default=None, max_length=40)
    volume: str | None = Field(default=None, max_length=40)
    owner: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=120)
    confidence: int = Field(default=0, ge=0, le=100)
    surveyed_on: str | None = Field(default=None, max_length=40)
    survey_year: int | None = Field(default=None, ge=1900, le=2100)
    rights: dict = Field(default_factory=dict)
    below_grade: bool = False
    airspace: bool = False
    has_conflict: bool = False
    render_height: int = Field(default=34, ge=4, le=200)
    colors: dict = Field(default_factory=dict)
    sort_order: int = 0


class LevelUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=60)
    property_type: str | None = Field(default=None, max_length=120)
    elevation: str | None = Field(default=None, max_length=60)
    elevation_min: float | None = None
    elevation_max: float | None = None
    area: str | None = Field(default=None, max_length=40)
    volume: str | None = Field(default=None, max_length=40)
    owner: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=120)
    confidence: int | None = Field(default=None, ge=0, le=100)
    airspace: bool | None = None
    has_conflict: bool | None = None


class BuildingSummary(BaseModel):
    """Used by the locality map and building pickers (frontend LOCALITY.buildings)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    use: str | None = Field(validation_alias="use_category", serialization_alias="use")
    conflict: bool = Field(validation_alias="has_conflict", serialization_alias="conflict")
    validation_status: str | None
    address: str
    lat: float | None
    lng: float | None
    geometry: dict = Field(validation_alias="map_geometry", serialization_alias="geometry")


class BuildingMeta(BaseModel):
    """Shaped like the frontend's LAKEVIEW_META / BUILDINGS_EXTRA[x].meta."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    parent: str
    floors: int
    basements: int
    address: str
    ward: str | None
    zone: str | None
    surveyNo: str | None = Field(default=None, serialization_alias="surveyNo")
    lat: float | None
    lng: float | None
    landUse: str | None = Field(default=None, serialization_alias="landUse")
    ownershipType: str | None = Field(default=None, serialization_alias="ownershipType")
    boundaryDims: str | None = Field(default=None, serialization_alias="boundaryDims")
    status: str | None
    validationStatus: str | None = Field(default=None, serialization_alias="validationStatus")
    surveyAccuracy: str | None = Field(default=None, serialization_alias="surveyAccuracy")
    gnss: str | None
    lidarAvailability: str | None = Field(default=None, serialization_alias="lidarAvailability")
    infra: dict
    use: str | None
    conflict: bool
    roadInfo: str | None = Field(default=None, serialization_alias="roadInfo")
    geometry: dict


class BuildingDetail(BaseModel):
    """Everything the explorer needs for one building in a single call."""

    meta: BuildingMeta
    levels: list[LevelOut]
    conflict_summary: dict | None


class BuildingCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=160)
    parcel_ulpin: str = Field(min_length=4, max_length=40)
    address: str = Field(min_length=3, max_length=255)
    ward: str | None = Field(default=None, max_length=60)
    zone: str | None = Field(default=None, max_length=80)
    survey_no: str | None = Field(default=None, max_length=60)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    floors: int = Field(default=0, ge=0, le=300)
    basements: int = Field(default=0, ge=0, le=20)
    land_use: str | None = Field(default=None, max_length=80)
    use_category: str | None = Field(default=None, max_length=40)
    ownership_type: str | None = Field(default=None, max_length=160)
    boundary_dims: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=80)
    validation_status: str | None = Field(default="Review required", max_length=80)
    survey_accuracy: str | None = Field(default=None, max_length=80)
    gnss: str | None = Field(default=None, max_length=120)
    lidar_availability: str | None = Field(default=None, max_length=120)
    infra: dict = Field(default_factory=dict)
    map_geometry: dict = Field(default_factory=dict)
    road_info: str | None = None


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    address: str | None = Field(default=None, min_length=3, max_length=255)
    ward: str | None = Field(default=None, max_length=60)
    zone: str | None = Field(default=None, max_length=80)
    floors: int | None = Field(default=None, ge=0, le=300)
    basements: int | None = Field(default=None, ge=0, le=20)
    land_use: str | None = Field(default=None, max_length=80)
    use_category: str | None = Field(default=None, max_length=40)
    ownership_type: str | None = Field(default=None, max_length=160)
    status: str | None = Field(default=None, max_length=80)
    validation_status: str | None = Field(default=None, max_length=80)
    infra: dict | None = None
    road_info: str | None = None


class LocalityOut(BaseModel):
    """Feeds the schematic locality map (frontend LOCALITY object)."""

    name: str
    buildings: list[BuildingSummary]
    genericBuildings: list[dict]
    metro: dict
    rail: dict
    parks: list[dict]


class SearchResultOut(BaseModel):
    addr: str
    parent: str
    buildingId: str
    id3d: str
    status: str
    conf: int
    conflict: bool
    date: str
    level_code: str


class InfraAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: str
    name: str
    agency: str | None
    status: str | None
    depth_m: float | None
    color: str | None
    condition: str | None
    details: dict
    geometry: dict
