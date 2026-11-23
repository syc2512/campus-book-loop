from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, validate_production_settings
from app.core.observability import RequestContextMiddleware, configure_logging
from app.database import init_db
from app.routers import admin, auth, catalog, listings, orders, pricing, recommendations
from app.schemas import HealthResponse
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    if settings.auto_create_schema:
        init_db()
    if settings.seed_on_startup:
        seed_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Campus Book Loop 的参考 API。估价模型使用合成数据训练，"
        "仅用于软件与 AI 实验展示。"
    ),
    lifespan=lifespan,
)

configure_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)

for api_router in [
    auth.router,
    catalog.router,
    listings.router,
    pricing.router,
    recommendations.router,
    orders.router,
    admin.router,
]:
    app.include_router(api_router, prefix=settings.api_prefix)

# Listing images are written below upload_dir and served by the API host.
media_root = Path(settings.upload_dir)
media_root.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.media_url_prefix,
    StaticFiles(directory=media_root),
    name="media",
)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Campus Book Loop API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
    )
