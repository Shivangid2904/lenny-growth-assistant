from pydantic import BaseModel, ConfigDict


class ConfigResponse(BaseModel):
    active_provider: str
    cloud_model: str
    local_model: str
    embedding_model: str

    model_config = ConfigDict(extra="forbid")
