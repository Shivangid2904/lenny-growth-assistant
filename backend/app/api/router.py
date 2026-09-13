from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.config import router as config_router
from app.api.sessions import router as sessions_router

api_router = APIRouter()

# Include health at root level
api_router.include_router(health_router)
# Include config and sessions
api_router.include_router(config_router)
api_router.include_router(sessions_router)
