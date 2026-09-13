from pydantic import BaseModel, ConfigDict


class DependenciesStatus(BaseModel):
    database: str
    ollama: str
    claude_api: str

    model_config = ConfigDict(extra="forbid")


class HealthResponse(BaseModel):
    status: str
    dependencies: DependenciesStatus

    model_config = ConfigDict(extra="forbid")
