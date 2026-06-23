from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.asset import BulkImportRequest, BulkImportResponse, AnalyzeRequest
from app.services import asset as svc
from app.chains import analyze as chains

router = APIRouter()


@router.post("/import", response_model=BulkImportResponse)
async def bulk_import(body: BulkImportRequest, db: AsyncSession = Depends(get_db)):
    return await svc.bulk_import(db, body.assets)


@router.get("/assets")
async def list_assets(
    type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    filters = {}
    if type:
        filters["type"] = type
    if status:
        filters["status"] = status
    if tag:
        filters["tag"] = tag
    assets = await svc.get_all_assets(db, filters)
    return {"total": len(assets), "items": [_asset_dict(a) for a in assets]}


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    asset = await svc.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_dict(asset)


@router.post("/analyze")
async def analyze(body: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    mode = body.mode.strip().lower()

    if mode not in ("query", "risk", "enrich", "report"):
        raise HTTPException(status_code=400, detail="mode must be one of: query, risk, enrich, report")

    if mode == "query":
        if not body.query:
            raise HTTPException(status_code=400, detail="query is required for mode=query")
        assets = await svc.get_all_assets(db)
        return await chains.natural_language_query([_asset_dict(a) for a in assets], body.query)

    if mode == "risk":
        assets = await svc.get_all_assets(db, body.filters)
        return await chains.risk_score([_asset_dict(a) for a in assets], body.asset_id)

    if mode == "enrich":
        if not body.asset_id:
            raise HTTPException(status_code=400, detail="asset_id is required for mode=enrich")
        asset = await svc.get_asset_by_id(db, body.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        result = await chains.enrich_asset(_asset_dict(asset))
        if "error" not in result:
            asset.env_category = result.get("env_category")
            asset.criticality = result.get("criticality")
            meta = {**(asset.metadata_ or {}), **result.get("enriched_metadata", {})}
            asset.metadata_ = meta
            await db.commit()
        return result

    if mode == "report":
        assets = await svc.get_all_assets(db, body.filters)
        return await chains.generate_report([_asset_dict(a) for a in assets], body.filters)


def _asset_dict(a) -> dict:
    return {
        "id": a.id,
        "type": a.type,
        "value": a.value,
        "status": a.status,
        "first_seen": a.first_seen.isoformat() if a.first_seen else None,
        "last_seen": a.last_seen.isoformat() if a.last_seen else None,
        "source": a.source,
        "tags": a.tags or [],
        "metadata": a.metadata_ or {},
        "env_category": a.env_category,
        "criticality": a.criticality,
        "risk_score": a.risk_score,
    }
