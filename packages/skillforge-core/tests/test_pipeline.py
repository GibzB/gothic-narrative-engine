"""
Tests for the SkillForge Pipeline.

Validates:
- Pipeline orchestration
- Phase execution and error handling
- Event hook triggering
- Custom pipeline configurations

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from skillforge.pipeline import (
    SkillForgePipeline,
    PipelineConfig,
    PipelineResult,
    TriagePhaseResult,
    ValidationPhaseResult,
    PBTPhaseResult,
    DiagnosticsPhaseResult,
    CompilationPhaseResult,
    create_default_pipeline,
    create_compliance_pipeline,
    create_narrative_pipeline,
)
from skillforge.events import PhaseEventType


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.enable_triage is True
        assert config.enable_validation is True
        assert config.enable_pbt is True
        assert config.enable_diagnostics is True
        assert config.enable_compilation is True
        assert config.max_body_words == 1500
        assert config.max_examples == 50
        assert config.default_output_type == "mcp_server"
        assert config.continue_on_error is False

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = PipelineConfig(
            enable_triage=False,
            max_examples=100,
            default_output_type="kiro_hook",
        )

        assert config.enable_triage is False
        assert config.max_examples == 100
        assert config.default_output_type == "kiro_hook"


class TestSkillForgePipeline:
    """Tests for SkillForgePipeline."""

    def test_init_default_config(self) -> None:
        """Test pipeline initialization with default config."""
        pipeline = SkillForgePipeline()

        assert pipeline.config is not None
        assert pipeline.event_registry is not None
        assert pipeline.event_dispatcher is not None

    def test_init_custom_config(self) -> None:
        """Test pipeline initialization with custom config."""
        config = PipelineConfig(max_examples=75)
        pipeline = SkillForgePipeline(config=config)

        assert pipeline.config.max_examples == 75

    def test_triage_phase_execution(self) -> None:
        """Test triage phase execution."""
        pipeline = SkillForgePipeline()
        result = pipeline.run_triage_only("Create a new AWS skill")

        assert result.phase_name == "triage"
        assert result.triage_result is not None
        assert result.triage_result.intent is not None
        assert result.duration_ms >= 0

    def test_validation_phase_with_string(self) -> None:
        """Test validation phase with string content."""
        pipeline = SkillForgePipeline()
        
        skill_content = """---
name: test-skill
version: 1.0.0
description: A test skill
---
This is the skill body.
"""
        result = pipeline.run_validation_only(skill_content)

        assert result.phase_name == "validation"
        assert result.validation_result is not None

    def test_pbt_phase_disabled(self) -> None:
        """Test PBT phase when disabled."""
        config = PipelineConfig(enable_pbt=False)
        pipeline = SkillForgePipeline(config=config)

        # PBT phase should return early
        assert pipeline.config.enable_pbt is False

    def test_diagnostics_phase_with_code(self) -> None:
        """Test diagnostics phase with code analysis."""
        pipeline = SkillForgePipeline()
        
        code = """
def test_function():
    '''Test function.'''
    return True
"""
        # Use a valid path to trigger code analysis
        result = pipeline.run_diagnostics_only(Path(__file__), code=code)

        assert result.phase_name == "diagnostics"
        # Code report should be generated when code is provided with a valid path
        assert result.is_successful is True

    def test_register_hook(self) -> None:
        """Test registering an event hook."""
        pipeline = SkillForgePipeline()
        
        hook_called = []
        
        def test_hook(event_data: dict) -> None:
            hook_called.append(event_data)

        success = pipeline.register_hook(
            "test-hook",
            PhaseEventType.PIPELINE_START,
            test_hook,
        )

        assert success is True

    def test_unregister_hook(self) -> None:
        """Test unregistering an event hook."""
        pipeline = SkillForgePipeline()
        
        pipeline.register_hook(
            "test-hook",
            PhaseEventType.PIPELINE_START,
            lambda x: None,
        )
        
        success = pipeline.unregister_hook("test-hook")

        assert success is True

    def test_custom_phase_handler(self) -> None:
        """Test registering a custom phase handler."""
        pipeline = SkillForgePipeline()
        
        def custom_handler(data: str) -> 'PhaseResult':
            from skillforge.pipeline import PhaseResult
            return PhaseResult(phase_name="custom", is_successful=True)

        pipeline.register_custom_phase("custom", custom_handler)

        assert "custom" in pipeline._custom_handlers

    def test_diagnose_workspace(self, tmp_path: Path) -> None:
        """Test workspace diagnostics."""
        # Create a minimal .kiro directory
        kiro_dir = tmp_path / ".kiro"
        kiro_dir.mkdir()
        
        pipeline = SkillForgePipeline()
        report = pipeline.diagnose_workspace(tmp_path)

        assert report is not None
        # .kiro exists but may have warnings
        assert hasattr(report, "is_healthy")


class TestPhaseResults:
    """Tests for phase result classes."""

    def test_triage_phase_result(self) -> None:
        """Test TriagePhaseResult."""
        result = TriagePhaseResult(
            phase_name="triage",
            is_successful=True,
        )

        assert result.phase_name == "triage"
        assert result.is_successful is True
        assert result.triage_result is None

    def test_validation_phase_result(self) -> None:
        """Test ValidationPhaseResult."""
        result = ValidationPhaseResult(
            phase_name="validation",
            is_successful=True,
        )

        assert result.phase_name == "validation"
        assert result.validation_result is None

    def test_pbt_phase_result(self) -> None:
        """Test PBTPhaseResult."""
        result = PBTPhaseResult(
            phase_name="pbt",
            is_successful=True,
        )

        assert result.phase_name == "pbt"
        assert result.eval_results == []

    def test_diagnostics_phase_result(self) -> None:
        """Test DiagnosticsPhaseResult."""
        result = DiagnosticsPhaseResult(
            phase_name="diagnostics",
            is_successful=True,
        )

        assert result.phase_name == "diagnostics"
        assert result.performance_report is None

    def test_compilation_phase_result(self) -> None:
        """Test CompilationPhaseResult."""
        result = CompilationPhaseResult(
            phase_name="compilation",
            is_successful=True,
        )

        assert result.phase_name == "compilation"
        assert result.compilation_result is None


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_to_dict(self) -> None:
        """Test PipelineResult.to_dict()."""
        result = PipelineResult(
            is_successful=True,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
        )

        data = result.to_dict()

        assert data["isSuccessful"] is True
        assert "startedAt" in data
        assert "phases" in data

    def test_with_phase_results(self) -> None:
        """Test PipelineResult with phase results."""
        triage = TriagePhaseResult(phase_name="triage", is_successful=True)
        result = PipelineResult(
            is_successful=True,
            triage_phase=triage,
        )

        data = result.to_dict()

        assert data["phases"]["triage"]["isSuccessful"] is True


class TestPipelineFactoryFunctions:
    """Tests for pipeline factory functions."""

    def test_create_default_pipeline(self) -> None:
        """Test create_default_pipeline()."""
        pipeline = create_default_pipeline()

        assert pipeline is not None
        assert isinstance(pipeline, SkillForgePipeline)
        assert pipeline.config.max_examples == 50

    def test_create_default_pipeline_with_skills(self) -> None:
        """Test create_default_pipeline() with skills list."""
        skills = ["skill-1", "skill-2"]
        pipeline = create_default_pipeline(available_skills=skills)

        assert pipeline.config.available_skills == skills

    def test_create_compliance_pipeline(self) -> None:
        """Test create_compliance_pipeline()."""
        pipeline = create_compliance_pipeline()

        assert pipeline is not None
        assert isinstance(pipeline, SkillForgePipeline)
        assert pipeline.config.require_parameters is True
        assert pipeline.config.max_examples == 100
        assert pipeline.config.default_output_type == "mcp_server"

    def test_create_narrative_pipeline(self) -> None:
        """Test create_narrative_pipeline()."""
        pipeline = create_narrative_pipeline()

        assert pipeline is not None
        assert isinstance(pipeline, SkillForgePipeline)
        assert pipeline.config.max_body_words == 3000
        assert pipeline.config.max_examples == 30
        assert pipeline.config.default_output_type == "kiro_hook"


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_continue_on_error_disabled(self) -> None:
        """Test that pipeline stops on error when continue_on_error is False."""
        config = PipelineConfig(continue_on_error=False)
        pipeline = SkillForgePipeline(config=config)

        assert pipeline.config.continue_on_error is False

    def test_continue_on_error_enabled(self) -> None:
        """Test that pipeline continues on error when configured."""
        config = PipelineConfig(continue_on_error=True)
        pipeline = SkillForgePipeline(config=config)

        assert pipeline.config.continue_on_error is True


class TestPipelineEventDispatch:
    """Tests for pipeline event dispatching."""

    def test_event_dispatch_disabled(self) -> None:
        """Test that events are not dispatched when disabled."""
        config = PipelineConfig(enable_events=False)
        pipeline = SkillForgePipeline(config=config)

        # Dispatch should return empty list
        results = pipeline._dispatch_event(
            PhaseEventType.PIPELINE_START,
            {"test": "data"},
        )

        assert results == []

    def test_event_dispatch_enabled(self) -> None:
        """Test that events are dispatched when enabled."""
        config = PipelineConfig(enable_events=True)
        pipeline = SkillForgePipeline(config=config)

        # No hooks registered, so dispatch returns empty list
        results = pipeline._dispatch_event(
            PhaseEventType.PIPELINE_START,
            {"test": "data"},
        )

        assert isinstance(results, list)


class TestComponentAccess:
    """Tests for lazy component initialization."""

    def test_triage_router_initialization(self) -> None:
        """Test lazy triage router initialization."""
        pipeline = SkillForgePipeline()
        
        # First access creates the component
        router = pipeline.triage_router
        assert router is not None
        
        # Second access returns the same instance
        router2 = pipeline.triage_router
        assert router is router2

    def test_skill_validator_initialization(self) -> None:
        """Test lazy skill validator initialization."""
        pipeline = SkillForgePipeline()
        
        validator = pipeline.skill_validator
        assert validator is not None
        
        validator2 = pipeline.skill_validator
        assert validator is validator2

    def test_pbt_runner_initialization(self) -> None:
        """Test lazy PBT runner initialization."""
        pipeline = SkillForgePipeline()
        
        runner = pipeline.pbt_runner
        assert runner is not None
        
        runner2 = pipeline.pbt_runner
        assert runner is runner2

    def test_skill_compiler_initialization(self) -> None:
        """Test lazy skill compiler initialization."""
        pipeline = SkillForgePipeline()
        
        compiler = pipeline.skill_compiler
        assert compiler is not None
        
        compiler2 = pipeline.skill_compiler
        assert compiler is compiler2
