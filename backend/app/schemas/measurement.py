"""Pydantic schemas for measurement responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class MeasurementOut(BaseModel):
    """Measurement details for a single feature."""

    type: str | None = None        # "area" | "length" | None
    value: float | None = None
    unit: str | None = None        # "m2" | "m" | None
    projected_crs: str | None = None
    status: str                       # OK | NOT_REQUIRED | UNSUPPORTED | FAILED
    note: str | None = None


class FeatureOut(BaseModel):
    """Single feature in a measurements response."""

    model_config = ConfigDict(from_attributes=True)

    index: int
    geometry_type: str | None = None
    crs: str | None = None
    properties: dict[str, Any] | None = None
    geometry: dict[str, Any] | None = None
    measurement: MeasurementOut

    @field_validator("properties", mode="before")
    @classmethod
    def parse_properties(cls, v: Any) -> dict[str, Any] | None:
        """Deserialise JSON string stored in DB into a dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return {}
        return v

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        """Deserialise JSON string stored in DB into a dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v


class Summary(BaseModel):
    """File-level aggregated summary across ALL features (not just the page)."""

    total_area_m2: float
    total_length_m: float
    unsupported: int
    failed: int
    by_geometry_type: dict[str, int]


class MeasurementsResponse(BaseModel):
    """Full response for GET /api/files/{id}/measurements/."""

    file_id: str
    total: int
    summary: Summary
    features: list[FeatureOut]
