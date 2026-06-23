import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, JSON, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(SAEnum("domain", "subdomain", "ip_address", "service", "certificate", "technology", name="asset_type"), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(SAEnum("active", "stale", "archived", name="asset_status"), default="active")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String, default="import")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    env_category: Mapped[str | None] = mapped_column(String, nullable=True)
    criticality: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(nullable=True)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    from_asset_id: Mapped[str] = mapped_column(String, nullable=False)
    to_asset_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
