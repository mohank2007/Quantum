"""FastAPI application entrypoint for the Hybrid QML Platform."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger, setup_logging
from beanie import init_beanie
from app.database.session import get_db_client
from app.database.models import __all__ as all_models_names
import importlib

_beanie_initialized = False


async def init_db() -> bool:
    """Initialize MongoDB client, Beanie document models, and seed default datasets."""
    global _beanie_initialized
    if _beanie_initialized:
        return True

    try:
        client = get_db_client()
        db = client[settings.MONGODB_DB]
        models_module = importlib.import_module("app.database.models")
        document_models = [getattr(models_module, model_name) for model_name in all_models_names]
        
        await init_beanie(database=db, document_models=document_models)
        _beanie_initialized = True
        logger.info("MongoDB and Beanie ODM initialized successfully.")
        
        # Seed bundled default datasets (idempotent — safe to call every startup)
        try:
            from app.core.dataset_seeder import seed_default_datasets
            await seed_default_datasets()
        except Exception as seed_err:
            logger.warning(f"Default dataset seeding (non-fatal): {seed_err}")
            
        return True
    except Exception as mongo_err:
        logger.warning(f"MongoDB/Beanie initialization deferred (verify MONGODB_URL): {mongo_err}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    setup_logging()
    logger.info(
        f"Starting {settings.PROJECT_NAME} [Environment: {settings.ENVIRONMENT}] [Version: {settings.VERSION}]"
    )
    
    # Initialize MongoDB/Beanie
    await init_db()

    yield

    logger.info("Shutting down application and closing MongoDB client.")
    client = get_db_client()
    if client:
        client.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Hybrid Quantum Machine Learning Platform for Early Disease Detection: "
        "Production-grade backend integrating Classical Support Vector Machines (SVM), "
        "Variational Quantum Classifiers (VQC), PennyLane NISQ simulation, and AI-assisted data engineering."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Centralized application exception handler returning standardized error payload."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler preventing stack traces and internal secrets from leaking."""
    logger.error(f"Unhandled system exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred. Please contact the platform administrator.",
                "details": {},
            }
        },
    )


# Mount main API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Root"])
@app.get("/healthz", tags=["Root"])
async def root_health_alias():
    """Alias for /api/v1/health commonly checked by cloud platforms."""
    from app.api.v1.health import health_check
    return await health_check()


# Check for bundled frontend production build
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.environ.get("FRONTEND_DIST")
if not FRONTEND_DIST or not os.path.exists(FRONTEND_DIST):
    candidate_paths = [
        "/app/frontend_dist",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend_dist"),
    ]
    for p in candidate_paths:
        if os.path.exists(p) and os.path.isfile(os.path.join(p, "index.html")):
            FRONTEND_DIST = p
            break

if FRONTEND_DIST and os.path.exists(FRONTEND_DIST):
    logger.info(f"Serving integrated Single Page Application frontend from: {FRONTEND_DIST}")
    
    # Mount assets directory
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")

    # Serve SPA routes and static assets
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API v1 or documentation endpoints
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("docs") or full_path.startswith("openapi"):
            return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "API endpoint not found"}})
            
        target_file = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
            
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
            
        return JSONResponse(status_code=404, content={"error": "index.html not found"})
else:
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint fallback when frontend is not built into container."""
        return {
            "status": "online",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_PREFIX}/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }
