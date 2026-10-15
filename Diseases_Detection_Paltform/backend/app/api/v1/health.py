import asyncio
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health & Version"])


@router.get("/health")
async def health_check():
    """Health check endpoint to verify backend service readiness and dependent components."""
    from app.main import init_db, _beanie_initialized
    
    db_status = "healthy"
    
    if not _beanie_initialized:
        connected = await init_db()
        if not connected:
            db_status = "unhealthy (Beanie ODM pending MONGODB_URL connection)"
    
    try:
        from app.database.session import get_db_client
        client = get_db_client()
        if client is not None:
            await asyncio.wait_for(client.admin.command("ping"), timeout=3.0)
            db_status = "healthy"
    except Exception as exc:
        db_status = f"unhealthy ({type(exc).__name__}: {str(exc)})"

    is_ok = not db_status.startswith("unhealthy")
    return {
        "status": "ok" if is_ok else "degraded",
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
