import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, DependenciesStatus, LivenessResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=LivenessResponse)
def get_liveness() -> LivenessResponse:
    """Lightweight liveness probe.

    Returns 200 when the application process is alive.
    Does NOT check the database, Ollama, or any external dependency.
    Suitable for use as a container liveness check (restart policy).
    """
    return LivenessResponse(status="ok")


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Operational readiness endpoint.

    Checks:
    - database connectivity (live SELECT 1)
    - Ollama reachability (HTTP probe, 2s timeout)
    - Anthropic API key configured (configuration check only — no live API call)

    Overall status is 'ok' when database is reachable.
    Ollama or Claude unavailability alone does not fail the overall status
    (the configured provider is what matters at runtime).
    """
    # 1. Database check (live SELECT 1)
    db_status = "down"
    try:
        db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"

    # 2. Ollama check (live reachability probe, short timeout)
    ollama_status = "down"
    try:
        response = httpx.get(
            f"{settings.ollama_base_url.rstrip('/')}/api/tags",
            timeout=2.0,
        )
        if response.status_code == 200:
            ollama_status = "up"
    except Exception:
        ollama_status = "down"

    # 3. Claude API — configuration check only, no live request
    claude_status = (
        "configured"
        if bool(settings.anthropic_api_key and settings.anthropic_api_key.strip())
        else "not_configured"
    )

    # Overall status: ok if DB is reachable; degraded otherwise
    overall_status = "ok" if db_status == "up" else "degraded"

    return HealthResponse(
        status=overall_status,
        dependencies=DependenciesStatus(
            database=db_status,
            ollama=ollama_status,
            claude_api=claude_status,
        ),
    )
