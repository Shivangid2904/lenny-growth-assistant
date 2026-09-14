"""Skills package — backend-authoritative skill definitions."""
from app.skills.ship30 import (
    build_ship30_system_prompt,
    detect_content_type,
    SHIP30_SKILL_NAME,
    SUPPORTED_CONTENT_TYPES,
)
from app.skills.artifact import (
    ARTIFACT_SKILL_NAME,
    ARTIFACT_SKILL_DESCRIPTION,
    ARTIFACT_TYPE_HTML,
    ARTIFACT_TYPE_MARKDOWN,
    SUPPORTED_ARTIFACT_TYPES,
    detect_artifact_type,
    is_artifact_intent,
    build_artifact_system_prompt,
    extract_artifact_data,
)

__all__ = [
    "build_ship30_system_prompt",
    "detect_content_type",
    "SHIP30_SKILL_NAME",
    "SUPPORTED_CONTENT_TYPES",
    "ARTIFACT_SKILL_NAME",
    "ARTIFACT_SKILL_DESCRIPTION",
    "ARTIFACT_TYPE_HTML",
    "ARTIFACT_TYPE_MARKDOWN",
    "SUPPORTED_ARTIFACT_TYPES",
    "detect_artifact_type",
    "is_artifact_intent",
    "build_artifact_system_prompt",
    "extract_artifact_data",
]
