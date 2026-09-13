"""Backend-authoritative skill routing interface.

This module provides a bounded, secure skill registry for specialized agent capabilities.
Frontend requests can only invoke explicitly registered skills; arbitrary internal Python
execution is strictly blocked.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

from app.skills.ship30 import (
    detect_content_type,
    SHIP30_SKILL_NAME,
    SHIP30_SKILL_DESCRIPTION,
    SUPPORTED_CONTENT_TYPES,
    CONTENT_TYPE_ESSAY,
)

logger = logging.getLogger("agent.skill_router")


class Skill(ABC):
    """Abstract base class for backend-authoritative skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier (e.g. 'chat', 'ship30', 'artifact')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable skill description."""
        pass

    @property
    def is_stub(self) -> bool:
        """Indicates if this skill is a placeholder for future checkpoints."""
        return False


class ChatSkill(Skill):
    """Default product & growth chat skill grounded in Lenny's Podcast transcripts."""

    @property
    def name(self) -> str:
        return "chat"

    @property
    def description(self) -> str:
        return "Grounded Q&A over Lenny's Podcast transcripts with deterministic retrieval and citations."


class Ship30Skill(Skill):
    """Ship 30 for 30 content-generation skill.

    Transforms Lenny's Podcast transcript insights into structured written content:
    - Long-form Ship 30 for 30 essay (~1,250 words) — PRIMARY required format
    - LinkedIn post
    - X/Twitter thread
    - Concise product/growth insight

    Content-type routing is backend-authoritative: the intent routing table in
    app/skills/ship30.py controls which user phrases map to which content type.
    User text cannot invoke arbitrary Python functions or backend endpoints.
    """

    @property
    def name(self) -> str:
        return SHIP30_SKILL_NAME

    @property
    def description(self) -> str:
        return SHIP30_SKILL_DESCRIPTION

    @property
    def supported_content_types(self) -> set:
        return SUPPORTED_CONTENT_TYPES

    def detect_content_type(self, message: str) -> str:
        """Detect the appropriate content type from the user message.

        Falls back to essay (the primary Ship30 format) if no explicit
        content-type intent is detected.
        """
        detected = detect_content_type(message)
        return detected if detected is not None else CONTENT_TYPE_ESSAY


class ArtifactSkillStub(Skill):
    """Stub for future interactive artifact generation skill (Checkpoint 6)."""

    @property
    def name(self) -> str:
        return "artifact"

    @property
    def description(self) -> str:
        return "Generates isolated Markdown and HTML/CSS visual artifacts (Future Checkpoint)."

    @property
    def is_stub(self) -> bool:
        return True


class SkillRouter:
    """Registry and router controlling skill selection and execution."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        # Register core skills
        self.register(ChatSkill())
        self.register(Ship30Skill())
        self.register(ArtifactSkillStub())

    def register(self, skill: Skill) -> None:
        self._skills[skill.name.lower()] = skill

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name.lower())

    def list_skills(self) -> List[Dict[str, str]]:
        return [
            {"name": s.name, "description": s.description, "is_stub": s.is_stub}
            for s in self._skills.values()
        ]

    def route(self, message: str, explicit_skill: Optional[str] = None) -> Skill:
        """Route a request to an authoritative skill.

        Security model:
        1. If an explicit skill name is provided (e.g., from a trusted frontend action),
           validate it against the allowlisted registry. Reject anything not registered.
        2. Otherwise, perform backend-controlled intent detection using the fixed
           pattern table from app/skills/ship30.py.
        3. Unknown patterns fall back to the default 'chat' skill.

        User-provided text cannot invoke arbitrary Python functions, modules, or
        backend endpoints — only registered skill names and the fixed pattern table
        are consulted.
        """
        if explicit_skill:
            skill = self.get_skill(explicit_skill)
            if not skill:
                raise ValueError(
                    f"Invalid skill '{explicit_skill}'. Available skills: {list(self._skills.keys())}"
                )
            logger.info(
                "skill_routed_explicit",
                extra={"skill": skill.name, "explicit": True},
            )
            return skill

        # Backend-controlled intent detection
        msg_lower = message.lower()

        # Check Ship30 intents via the backend-controlled pattern table
        if detect_content_type(message) is not None:
            logger.info(
                "skill_routed_intent",
                extra={"detected_skill": "ship30", "message_preview": message[:80]},
            )
            return self._skills["ship30"]

        # Explicit keyword fallbacks for common ship30 patterns not in content-type table
        if "ship 30" in msg_lower or "ship30" in msg_lower or "atomic essay" in msg_lower:
            logger.info(
                "skill_routed_keyword",
                extra={"detected_skill": "ship30", "message_preview": message[:80]},
            )
            return self._skills["ship30"]

        return self._skills["chat"]


# Global router singleton
skill_router = SkillRouter()
