from fastapi import APIRouter
from app.config import settings
from app.schemas.config import ConfigResponse

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        active_provider=settings.default_llm_provider,
        cloud_model=settings.anthropic_model,
        local_model=settings.ollama_model,
        embedding_model=settings.embedding_model,
    )
