import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.database import engine, Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="DarkAtlas AI - Asset Analysis API",
    version="1.0.0",
    description="LangChain-powered asset analysis for Attack Surface Monitoring",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok"}


from app.routers.main import router
app.include_router(router, prefix="/api/v1")
