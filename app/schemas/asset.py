from datetime import datetime
from typing import Any
from pydantic import BaseModel


class AssetIn(BaseModel):
    id: str | None = None
    type: str
    value: str
    status: str = "active"
    source: str = "import"
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    parent: str | None = None
    covers: str | None = None
    resolves_to: str | None = None


class AssetOut(BaseModel):
    id: str
    type: str
    value: str
    status: str
    first_seen: datetime
    last_seen: datetime
    source: str
    tags: list[str]
    metadata: dict[str, Any]
    env_category: str | None
    criticality: str | None
    risk_score: float | None

    model_config = {"from_attributes": True}


class BulkImportRequest(BaseModel):
    assets: list[AssetIn]


class BulkImportResponse(BaseModel):
    imported: int
    updated: int
    errors: list[str]


class AnalyzeRequest(BaseModel):
    mode: str
    query: str | None = None
    asset_id: str | None = None
    filters: dict[str, Any] | None = None
