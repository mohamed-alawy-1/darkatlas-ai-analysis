from datetime import datetime, timezone
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, Relationship
from app.schemas.asset import AssetIn


async def bulk_import(db: AsyncSession, assets: list[AssetIn]) -> dict:
    imported = 0
    updated = 0
    errors = []
    rel_queue = []

    for item in assets:
        try:
            value = item.value.strip().lower()
            result = await db.execute(
                select(Asset).where(Asset.type == item.type, Asset.value == value)
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.last_seen = datetime.now(timezone.utc)
                existing.status = "active"
                existing.tags = list(set(existing.tags or []) | set(item.tags))
                existing.metadata_ = {**(existing.metadata_ or {}), **item.metadata}
                updated += 1
                asset_id = existing.id
            else:
                now = datetime.now(timezone.utc)
                asset = Asset(
                    id=item.id or None,
                    type=item.type,
                    value=value,
                    status=item.status,
                    source=item.source,
                    tags=item.tags,
                    metadata_=item.metadata,
                    first_seen=now,
                    last_seen=now,
                )
                db.add(asset)
                await db.flush()
                asset_id = asset.id
                imported += 1

            if item.parent:
                rel_queue.append(("subdomain_of", asset_id, item.parent))
            if item.covers:
                rel_queue.append(("covered_by", asset_id, item.covers))
            if item.resolves_to:
                rel_queue.append(("resolves_to", asset_id, item.resolves_to))

        except Exception as exc:
            errors.append(f"{item.value}: {exc}")

    for rel_type, from_id, to_id in rel_queue:
        try:
            existing = await db.execute(
                select(Relationship).where(
                    Relationship.from_asset_id == from_id,
                    Relationship.to_asset_id == to_id,
                    Relationship.type == rel_type,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(Relationship(from_asset_id=from_id, to_asset_id=to_id, type=rel_type))
        except Exception:
            pass

    await db.commit()
    return {"imported": imported, "updated": updated, "errors": errors}


async def get_all_assets(db: AsyncSession, filters: dict | None = None) -> list[Asset]:
    stmt = select(Asset)
    if filters:
        if t := filters.get("type"):
            stmt = stmt.where(Asset.type == t)
        if s := filters.get("status"):
            stmt = stmt.where(Asset.status == s)
        if tag := filters.get("tag"):
            stmt = stmt.where(Asset.tags.contains([tag]))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_asset_by_id(db: AsyncSession, asset_id: str) -> Asset | None:
    return await db.get(Asset, asset_id)
