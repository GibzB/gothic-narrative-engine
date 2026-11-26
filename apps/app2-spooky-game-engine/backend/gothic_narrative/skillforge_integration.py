"""
SkillForge Integration for Gothic Narrative Engine.

This module integrates skillforge-core for narrative skill handling.
Provides custom pipeline registration for narrative/game skills.

Task 6.2: Wire applications to core
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

# Import skillforge-core
from skillforge import (
    SkillForgePipeline,
    PipelineConfig,
    PipelineResult,
    create_narrative_pipeline,
    EventRegistry,
    PhaseEventType,
    TriageIntent,
)

logger = logging.getLogger(__name__)


class NarrativeSkillForgeIntegration:
    """
    Integration between Gothic Narrative Engine and SkillForge core.

    Provides:
    - Custom pipeline for narrative skill synthesis
    - Event hooks for narrative generation
    - Skill triage and routing for game mechanics

    Example:
        >>> integration = NarrativeSkillForgeIntegration()
        >>> result = integration.synthesize_narrative_skill("Create a spooky forest encounter")
        >>> result.is_successful
        True
    """

    def __init__(
        self,
        *,
        skills_dir: Path | str | None = None,
        narrative_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the narrative integration.

        Args:
            skills_dir: Directory containing narrative skills
            narrative_context: Context for narrative generation
        """
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.narrative_context = narrative_context or {}

        # Create narrative-configured pipeline
        self.pipeline = create_narrative_pipeline()

        # Register narrative-specific hooks
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register narrative-specific event hooks."""
        # Hook to enhance narrative context before synthesis
        self.pipeline.register_hook(
            "narrative-pre-synthesis",
            PhaseEventType.SYNTHESIS_START,
            self._pre_synthesis_hook,
            priority=10,
        )

        # Hook to capture narrative artifacts after compilation
        self.pipeline.register_hook(
            "narrative-post-compile",
            PhaseEventType.MCP_COMPILE_COMPLETE,
            self._post_compile_hook,
            priority=50,
        )

    def _pre_synthesis_hook(self, event_data: dict[str, Any]) -> None:
        """Pre-synthesis hook to inject narrative context."""
        logger.debug(f"Enhancing narrative context for: {event_data.get('phase', 'unknown')}")

    def _post_compile_hook(self, event_data: dict[str, Any]) -> None:
        """Post-compilation hook to capture narrative artifacts."""
        is_successful = event_data.get("is_successful", False)
        logger.info(f"Narrative artifact compiled: success={is_successful}")

    def synthesize_narrative_skill(
        self,
        request: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """
        Synthesize a narrative skill from a natural language request.

        Args:
            request: Natural language narrative request
            context: Optional narrative context

        Returns:
            PipelineResult with synthesis results
        """
        # Merge context
        merged_context = {**self.narrative_context, **(context or {})}

        # Configure pipeline for narrative synthesis
        config = PipelineConfig(
            enable_triage=True,
            enable_validation=True,
            enable_pbt=True,
            enable_diagnostics=True,
            enable_compilation=True,
            max_body_words=3000,  # Allow longer narratives
            max_examples=30,  # Moderate testing for narrative skills
            default_output_type="kiro_hook",
            default_hook_trigger="UserPromptSubmit",
        )
        self.pipeline.config = config

        return self.pipeline.run(request)

    def triage_narrative_request(self, request: str) -> dict[str, Any]:
        """
        Triage a natural language narrative request.

        Args:
            request: Natural language request

        Returns:
            Dictionary with triage results
        """
        result = self.pipeline.run_triage_only(request)

        if result.triage_result:
            intent = result.triage_result.intent
            return {
                "intent": intent.value,
                "confidence": result.triage_result.confidence,
                "matched_skill": result.triage_result.matched_skill,
                "matched_skills": result.triage_result.matched_skills,
                "suggested_questions": result.triage_result.suggested_questions,
                "is_create_intent": intent == TriageIntent.CREATE,
                "is_improve_intent": intent == TriageIntent.IMPROVE,
            }

        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "error": "Triage failed",
        }

    def validate_narrative_skill(
        self,
        skill_path: Path | str,
    ) -> dict[str, Any]:
        """
        Validate a narrative skill definition.

        Args:
            skill_path: Path to the skill definition

        Returns:
            Dictionary with validation results
        """
        result = self.pipeline.run_validation_only(skill_path)

        if result.validation_result:
            return {
                "is_valid": result.validation_result.is_valid,
                "error_count": result.validation_result.error_count,
                "warning_count": result.validation_result.warning_count,
                "errors": [e.message for e in result.validation_result.errors],
                "warnings": [w.message for w in result.validation_result.warnings],
            }

        return {
            "is_valid": False,
            "errors": result.errors,
        }

    def compile_narrative_hook(
        self,
        skill_path: Path | str,
        *,
        trigger: str = "UserPromptSubmit",
        matcher: str | None = None,
    ) -> dict[str, Any]:
        """
        Compile a narrative skill to a Kiro Agent Hook.

        Args:
            skill_path: Path to the skill definition
            trigger: Hook trigger type
            matcher: Optional regex matcher for trigger

        Returns:
            Dictionary with compilation results
        """
        result = self.pipeline.run_compilation_only(
            skill_path,
            output_type="kiro_hook",
            trigger=trigger,
        )

        if result.compilation_result:
            return {
                "is_successful": result.is_successful,
                "generated_code": result.compilation_result.generated_code,
                "errors": result.errors,
                "warnings": result.warnings,
            }

        return {
            "is_successful": False,
            "errors": result.errors,
        }


def create_narrative_integration(
    *,
    skills_dir: Path | str | None = None,
    narrative_context: dict[str, Any] | None = None,
) -> NarrativeSkillForgeIntegration:
    """
    Factory function to create a narrative integration.

    Args:
        skills_dir: Optional directory containing skills
        narrative_context: Optional narrative context

    Returns:
        Configured NarrativeSkillForgeIntegration instance
    """
    return NarrativeSkillForgeIntegration(
        skills_dir=skills_dir,
        narrative_context=narrative_context,
    )


# Export key symbols
__all__ = [
    "NarrativeSkillForgeIntegration",
    "create_narrative_integration",
]
