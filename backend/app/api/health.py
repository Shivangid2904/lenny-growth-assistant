import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, DependenciesStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    # 1. Database check (live SELECT 1)
    db_status = "down"
    try:
        db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"

    # 2. Ollama check (live reachability probe)
    ollama_status = "down"
    try:
        # Check Ollama tags or version with a short timeout
        response = httpx.get(
            f"{settings.ollama_base_url.rstrip('/')}/api/tags",
            timeout=2.0,
        )
        if response.status_code == 200:
            ollama_status = "up"
    except Exception:
        ollama_status = "down"

    # 3. Claude API check (configuration check only, no live request)
    claude_status = "configured" if bool(settings.anthropic_api_key and settings.anthropic_api_key.strip()) else "not_configured"

    overall_status = "ok" if db_status == "up" else "degraded"

    return HealthResponse(
        status=overall_status,
        dependencies=DependenciesStatus(
            database=db_status,
            ollama=ollama_status,
            claude_api=claude_status,
        ),
    )
