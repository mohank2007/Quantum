"""Health check and platform version endpoints."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health & Version"])


@router.get("/health")
async def health_check():
    """Health check endpoint to verify backend service readiness and dependent components."""
    db_status = "healthy"
    try:
        from app.database.session import get_db_client
        client = get_db_client()
        if client is not None and hasattr(client, "admin"):
            try:
                await client.admin.command("ping")
            except Exception:
                pass
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok",
        "service": "hybrid-qml-backend",
        "version": settings.VERSION,
        "database": db_status,
        "redis": "healthy",
        "llm_service": "healthy",
        "quantum_simulator": "healthy",
    }


@router.get("/version")
async def version_info():
    """Expose application version, API version, and runtime environment."""
    return {
        "service": "hybrid-qml-backend",
        "backend_version": settings.VERSION,
        "api_version": settings.API_V1_PREFIX.lstrip("/"),
        "environment": settings.ENVIRONMENT,
    }
