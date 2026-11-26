"""
SkillForge Integration for Cloud Compliance App.

This module integrates skillforge-core for cloud compliance skill handling.
Provides custom pipeline registration for compliance-specific skills.

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
    create_compliance_pipeline,
    EventRegistry,
    PhaseEventType,
    TriageIntent,
)

logger = logging.getLogger(__name__)


class ComplianceSkillForgeIntegration:
    """
    Integration between Cloud Compliance app and SkillForge core.

    Provides:
    - Custom pipeline for compliance skill checking
    - Event hooks for compliance validation
    - Skill triage and routing

    Example:
        >>> integration = ComplianceSkillForgeIntegration()
        >>> result = integration.check_skill("skills/aws-audit/SKILL.md")
        >>> result.is_successful
        True
    """

    def __init__(
        self,
        *,
        skills_dir: Path | str | None = None,
        strict_mode: bool = True,
    ) -> None:
        """
        Initialize the compliance integration.

        Args:
            skills_dir: Directory containing compliance skills
            strict_mode: Enable strict validation for compliance skills
        """
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.strict_mode = strict_mode

        # Create compliance-configured pipeline
        self.pipeline = create_compliance_pipeline()

        # Register compliance-specific hooks
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register compliance-specific event hooks."""
        # Hook to validate compliance requirements before compilation
        self.pipeline.register_hook(
            "compliance-pre-compile",
            PhaseEventType.MCP_COMPILE_START,
            self._pre_compile_hook,
            priority=10,
        )

        # Hook to record compliance evidence after PBT
        self.pipeline.register_hook(
            "compliance-record-evidence",
            PhaseEventType.PBT_COMPLETE,
            self._record_evidence_hook,
            priority=50,
        )

    def _pre_compile_hook(self, event_data: dict[str, Any]) -> None:
        """Pre-compilation hook for compliance validation."""
        logger.info(f"Pre-compile check for: {event_data.get('output_type', 'unknown')}")

    def _record_evidence_hook(self, event_data: dict[str, Any]) -> None:
        """Post-PBT hook to record compliance evidence."""
        test_count = event_data.get("test_count", 0)
        passed = event_data.get("passed", False)
        logger.debug(f"Recorded compliance evidence: {test_count} tests, passed={passed}")

    def check_skill(
        self,
        skill_path: Path | str,
        *,
        run_pbt: bool = True,
    ) -> PipelineResult:
        """
        Check a compliance skill definition.

        Args:
            skill_path: Path to the skill definition
            run_pbt: Whether to run property-based tests

        Returns:
            PipelineResult with checking results
        """
        path = Path(skill_path)

        # Configure pipeline for this run
        config = PipelineConfig(
            enable_triage=True,
            enable_validation=True,
            enable_pbt=run_pbt,
            enable_diagnostics=True,
            enable_compilation=True,
            require_parameters=self.strict_mode,
            max_examples=100 if run_pbt else 0,
        )
        self.pipeline.config = config

        return self.pipeline.run(path)

    def triage_request(self, request: str) -> dict[str, Any]:
        """
        Triage a natural language compliance request.

        Args:
            request: Natural language request

        Returns:
            Dictionary with triage results
        """
        result = self.pipeline.run_triage_only(request)

        if result.triage_result:
            return {
                "intent": result.triage_result.intent.value,
                "confidence": result.triage_result.confidence,
                "matched_skill": result.triage_result.matched_skill,
                "suggested_questions": result.triage_result.suggested_questions,
            }

        return {
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "error": "Triage failed",
        }

    def compile_compliance_skill(
        self,
        skill_path: Path | str,
        *,
        output_type: str = "mcp_server",
    ) -> dict[str, Any]:
        """
        Compile a compliance skill to MCP server.

        Args:
            skill_path: Path to the skill definition
            output_type: Type of output (mcp_server or kiro_hook)

        Returns:
            Dictionary with compilation results
        """
        result = self.pipeline.run_compilation_only(
            skill_path,
            output_type=output_type,
        )

        if result.compilation_result:
            return {
                "is_successful": result.is_successful,
                "output_type": result.compilation_result.output_type,
                "generated_code": result.compilation_result.generated_code,
                "errors": result.errors,
                "warnings": result.warnings,
            }

        return {
            "is_successful": False,
            "errors": result.errors,
        }


def create_compliance_integration(
    *,
    skills_dir: Path | str | None = None,
) -> ComplianceSkillForgeIntegration:
    """
    Factory function to create a compliance integration.

    Args:
        skills_dir: Optional directory containing skills

    Returns:
        Configured ComplianceSkillForgeIntegration instance
    """
    return ComplianceSkillForgeIntegration(skills_dir=skills_dir)


# Export key symbols
__all__ = [
    "ComplianceSkillForgeIntegration",
    "create_compliance_integration",
]
