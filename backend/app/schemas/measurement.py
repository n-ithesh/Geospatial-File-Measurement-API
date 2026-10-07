"""Pydantic schemas for measurement responses."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class MeasurementOut(BaseModel):
    """Measurement details for a single feature."""

    type: Optional[str] = None        # "area" | "length" | None
    value: Optional[float] = None
    unit: Optional[str] = None        # "m2" | "m" | None
    projected_crs: Optional[str] = None
    status: str                       # OK | NOT_REQUIRED | UNSUPPORTED | FAILED
    note: Optional[str] = None


class FeatureOut(BaseModel):
    """Single feature in a measurements response."""

    model_config = ConfigDict(from_attributes=True)

    index: int
    geometry_type: Optional[str] = None
    crs: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    geometry: Optional[Dict[str, Any]] = None
    measurement: MeasurementOut

    @field_validator("properties", mode="before")
    @classmethod
    def parse_properties(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Deserialise JSON string stored in DB into a dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return {}
        return v

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> Optional[Dict[str, Any]]:
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
    by_geometry_type: Dict[str, int]


class MeasurementsResponse(BaseModel):
    """Full response for GET /api/files/{id}/measurements/."""

    file_id: str
    total: int
    summary: Summary
    features: List[FeatureOut]
