from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str

    model_config = ConfigDict(extra="forbid")


class ErrorEnvelope(BaseModel):
    error: ErrorDetail

    model_config = ConfigDict(extra="forbid")
