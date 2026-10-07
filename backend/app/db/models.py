"""SQLAlchemy ORM models for the Geospatial File Measurement API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UploadedFile(Base):
    """Represents a geospatial file that has been uploaded for processing."""

    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="UUID primary key",
    )
    filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Original client-provided filename (sanitised)",
    )
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment='"shapefile" or "kml"',
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="PENDING | PROCESSING | COMPLETED | FAILED",
    )
    crs: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment='CRS string, e.g. "EPSG:4326"',
    )
    feature_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of features extracted",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable error if status=FAILED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        comment="UTC timestamp when the record was created",
    )

    # Relationship
    features: Mapped[list[Feature]] = relationship(
        "Feature",
        back_populates="uploaded_file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UploadedFile id={self.id!r} filename={self.filename!r} status={self.status!r}>"


class Feature(Base):
    """Represents a single geospatial feature extracted from an uploaded file."""

    __tablename__ = "features"
    __table_args__ = (
        Index("ix_features_file_id", "file_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key to UploadedFile",
    )
    feature_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Zero-based index of this feature in the source file",
    )
    geometry_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Shapely geometry type, e.g. Polygon",
    )
    geometry: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="GeoJSON geometry as a JSON string",
    )
    crs: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Source CRS for this feature",
    )
    properties: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Feature attribute properties as a JSON string",
    )
    measurement_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment='"area", "length", or null',
    )
    measurement_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Computed measurement value",
    )
    measurement_unit: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment='"m2", "m", or null',
    )
    projected_crs: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="UTM EPSG used for projection",
    )
    measurement_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OK",
        comment="OK | NOT_REQUIRED | UNSUPPORTED | FAILED",
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional note about measurement",
    )

    # Relationship
    uploaded_file: Mapped[UploadedFile] = relationship(
        "UploadedFile",
        back_populates="features",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Feature id={self.id} file_id={self.file_id!r} "
            f"type={self.geometry_type!r} status={self.measurement_status!r}>"
        )
