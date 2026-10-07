"""Pydantic schemas for file-level responses."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    """Response schema for POST /api/files/ (upload)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    feature_count: Optional[int] = None
    crs: Optional[str] = None
    status: str


class FileDetailOut(BaseModel):
    """Response schema for GET /api/files/{id}/."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: Optional[int] = None
    crs: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class FileListOut(BaseModel):
    """Response schema for GET /api/files/ (paginated list)."""

    total: int
    limit: int
    offset: int
    items: List[FileDetailOut]
