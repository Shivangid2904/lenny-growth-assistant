from pydantic import BaseModel, ConfigDict


class LivenessResponse(BaseModel):
    """Response model for /healthz liveness probe."""
    status: str  # always "ok" when process is alive

    model_config = ConfigDict(extra="forbid")


class DependenciesStatus(BaseModel):
    database: str
    ollama: str
    claude_api: str

    model_config = ConfigDict(extra="forbid")


class HealthResponse(BaseModel):
    status: str
    dependencies: DependenciesStatus

    model_config = ConfigDict(extra="forbid")
