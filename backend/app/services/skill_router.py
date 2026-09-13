"""Backend-authoritative skill routing interface.

This module provides a bounded, secure skill registry for specialized agent capabilities.
Frontend requests can only invoke explicitly registered skills; arbitrary internal Python
execution is strictly blocked.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

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


class Ship30SkillStub(Skill):
    """Stub for future Ship 30 for 30 essay generation skill (Checkpoint 4/5)."""

    @property
    def name(self) -> str:
        return "ship30"

    @property
    def description(self) -> str:
        return "Transforms transcript insights into a Ship 30 for 30 structured framework essay (Future Checkpoint)."

    @property
    def is_stub(self) -> bool:
        return True


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
        self.register(Ship30SkillStub())
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

        1. If an explicit skill is requested, validate that it is registered.
        2. Otherwise, check for keywords or fallback to default 'chat'.
        """
        if explicit_skill:
            skill = self.get_skill(explicit_skill)
            if not skill:
                raise ValueError(
                    f"Invalid skill '{explicit_skill}'. Available skills: {list(self._skills.keys())}"
                )
            return skill

        # Intent detection stub for future model-inferred routing fallback:
        # e.g., if user mentions "Ship 30" or "write an atomic essay"
        msg_lower = message.lower()
        if "ship 30" in msg_lower or "ship30" in msg_lower or "atomic essay" in msg_lower:
            logger.info("routing_intent_detected", extra={"detected_skill": "ship30"})
            # In Checkpoint 3, Ship30 is a stub, but routing interface correctly detects it.
            return self._skills["ship30"]

        return self._skills["chat"]


# Global router singleton
skill_router = SkillRouter()
