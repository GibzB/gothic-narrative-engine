"""
SkillForge Pipeline - Orchestrates the 4-Phase Skill Synthesis Process.

This module provides the main pipeline that wires together all core components:
1. Synthesis (Triage → Validator)
2. Evidence-Driven Evaluation & PBT (Validator → PBT)
3. Diagnostics (PBT → Diagnostics)
4. Cross-Runtime Compilation (Diagnostics → MCP Compilation)

The pipeline handles error propagation, event hooks, and phase transitions.

Implements:
- Task 6.1: Wire core components together
- Task 6.2: Wire applications to core

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from skillforge.triage import TriageRouter, TriageIntent, TriageResult
from skillforge.validate import SkillValidator, ValidationResult
from skillforge.evals import PBTRunner, EvalResult, EvidenceRecorder, EvidenceRecord
from skillforge.diagnostics import (
    PerformanceAnalyzer,
    PerformanceReport,
    CodeAnalyzer,
    CodeAnalysisReport,
    HistoricalAnalyzer,
    HistoricalReport,
)
from skillforge.compiler import (
    SkillCompiler,
    CompilationResult,
    MCPCompiler,
    MCPToolDefinition,
    HookCompiler,
    HookDefinition,
    HookTrigger,
    RuntimeValidator,
    RuntimeValidationResult,
)
from skillforge.events import (
    EventRegistry,
    EventDispatcher,
    AsyncEventDispatcher,
    PhaseEventType,
    HookExecutionResult,
)
from skillforge.frontmatter import parse_frontmatter, parse_frontmatter_file, FrontmatterResult
from skillforge.doctor import EcosystemDoctor, DiagnosticReport

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Pipeline Phase Results
# ============================================================================

@dataclass
class PhaseResult:
    """Base result for a pipeline phase."""
    phase_name: str
    is_successful: bool = True
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriagePhaseResult(PhaseResult):
    """Result of the triage phase."""
    triage_result: TriageResult | None = None


@dataclass
class ValidationPhaseResult(PhaseResult):
    """Result of the validation phase."""
    validation_result: ValidationResult | None = None
    frontmatter_result: FrontmatterResult | None = None


@dataclass
class PBTPhaseResult(PhaseResult):
    """Result of the PBT phase."""
    eval_results: list[EvalResult] = field(default_factory=list)
    evidence_records: list[EvidenceRecord] = field(default_factory=list)


@dataclass
class DiagnosticsPhaseResult(PhaseResult):
    """Result of the diagnostics phase."""
    performance_report: PerformanceReport | None = None
    code_report: CodeAnalysisReport | None = None
    historical_report: HistoricalReport | None = None


@dataclass
class CompilationPhaseResult(PhaseResult):
    """Result of the compilation phase."""
    compilation_result: CompilationResult | None = None
    runtime_validation: RuntimeValidationResult | None = None


@dataclass
class PipelineResult:
    """Complete result of running the full pipeline."""
    is_successful: bool = True
    started_at: str = ""
    completed_at: str = ""
    total_duration_ms: float = 0.0
    triage_phase: TriagePhaseResult | None = None
    validation_phase: ValidationPhaseResult | None = None
    pbt_phase: PBTPhaseResult | None = None
    diagnostics_phase: DiagnosticsPhaseResult | None = None
    compilation_phase: CompilationPhaseResult | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "isSuccessful": self.is_successful,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "totalDurationMs": self.total_duration_ms,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "phases": {
                "triage": {
                    "isSuccessful": self.triage_phase.is_successful if self.triage_phase else None,
                    "intent": self.triage_phase.triage_result.intent.value if self.triage_phase and self.triage_phase.triage_result else None,
                },
                "validation": {
                    "isSuccessful": self.validation_phase.is_successful if self.validation_phase else None,
                    "isValid": self.validation_phase.validation_result.is_valid if self.validation_phase and self.validation_phase.validation_result else None,
                },
                "pbt": {
                    "isSuccessful": self.pbt_phase.is_successful if self.pbt_phase else None,
                    "passed": all(r.passed for r in self.pbt_phase.eval_results) if self.pbt_phase and self.pbt_phase.eval_results else None,
                },
                "diagnostics": {
                    "isSuccessful": self.diagnostics_phase.is_successful if self.diagnostics_phase else None,
                    "hasCriticalIssues": self.diagnostics_phase.performance_report.has_critical_issues if self.diagnostics_phase and self.diagnostics_phase.performance_report else None,
                },
                "compilation": {
                    "isSuccessful": self.compilation_phase.is_successful if self.compilation_phase else None,
                    "outputType": self.compilation_phase.compilation_result.output_type if self.compilation_phase and self.compilation_phase.compilation_result else None,
                },
            },
        }


# ============================================================================
# Pipeline Configuration
# ============================================================================

@dataclass
class PipelineConfig:
    """Configuration for the SkillForge pipeline."""
    # Triage settings
    enable_triage: bool = True
    available_skills: list[str] | None = None
    confidence_threshold: float = 0.6

    # Validation settings
    enable_validation: bool = True
    max_body_words: int = 1500
    require_parameters: bool = False

    # PBT settings
    enable_pbt: bool = True
    max_examples: int = 50
    pbt_timeout_seconds: int = 30

    # Diagnostics settings
    enable_diagnostics: bool = True
    performance_thresholds: dict[str, tuple[float, float]] | None = None

    # Compilation settings
    enable_compilation: bool = True
    default_output_type: str = "mcp_server"  # mcp_server, kiro_hook, steering
    default_hook_trigger: str = "PreToolUse"

    # Event settings
    enable_events: bool = True
    async_events: bool = False

    # Error handling
    continue_on_error: bool = False
    log_errors: bool = True


# ============================================================================
# SkillForge Pipeline
# ============================================================================

class SkillForgePipeline:
    """
    Main pipeline orchestrating the 4-phase skill synthesis process.

    The pipeline connects all core components in sequence:
    1. Triage → Classify skill request intent
    2. Validator → Validate skill definition structure
    3. Synthesis → Generate skill specification
    4. PBT → Run property-based tests
    5. Diagnostics → Analyze performance and code quality
    6. MCP Compilation → Generate MCP tools/hooks

    Error handling is built in between phases, with event hooks triggered
    on phase completion and failure.

    Example:
        >>> pipeline = SkillForgePipeline()
        >>> result = pipeline.run("Create a new skill for AWS cost analysis")
        >>> result.is_successful
        True
    """

    def __init__(
        self,
        *,
        config: PipelineConfig | None = None,
        event_registry: EventRegistry | None = None,
    ) -> None:
        """
        Initialize the SkillForge pipeline.

        Args:
            config: Pipeline configuration options
            event_registry: Optional shared event registry
        """
        self.config = config or PipelineConfig()
        self.event_registry = event_registry or EventRegistry()

        # Initialize event dispatcher
        if self.config.async_events:
            self.event_dispatcher = AsyncEventDispatcher(self.event_registry)
        else:
            self.event_dispatcher = EventDispatcher(
                self.event_registry,
                continue_on_error=self.config.continue_on_error,
                log_errors=self.config.log_errors,
            )

        # Initialize phase components
        self._triage_router: TriageRouter | None = None
        self._skill_validator: SkillValidator | None = None
        self._pbt_runner: PBTRunner | None = None
        self._evidence_recorder: EvidenceRecorder | None = None
        self._performance_analyzer: PerformanceAnalyzer | None = None
        self._code_analyzer: CodeAnalyzer | None = None
        self._historical_analyzer: HistoricalAnalyzer | None = None
        self._skill_compiler: SkillCompiler | None = None
        self._runtime_validator: RuntimeValidator | None = None

        # Custom phase handlers for extensibility
        self._custom_handlers: dict[str, Callable[..., PhaseResult]] = {}

    # ========================================================================
    # Phase Component Accessors (Lazy Initialization)
    # ========================================================================

    @property
    def triage_router(self) -> TriageRouter:
        """Get or create the triage router."""
        if self._triage_router is None:
            self._triage_router = TriageRouter(
                available_skills=self.config.available_skills,
                confidence_threshold=self.config.confidence_threshold,
            )
        return self._triage_router

    @property
    def skill_validator(self) -> SkillValidator:
        """Get or create the skill validator."""
        if self._skill_validator is None:
            self._skill_validator = SkillValidator(
                max_body_words=self.config.max_body_words,
                require_parameters=self.config.require_parameters,
            )
        return self._skill_validator

    @property
    def pbt_runner(self) -> PBTRunner:
        """Get or create the PBT runner."""
        if self._pbt_runner is None:
            self._pbt_runner = PBTRunner(
                max_examples=self.config.max_examples,
                timeout_seconds=self.config.pbt_timeout_seconds,
            )
        return self._pbt_runner

    @property
    def evidence_recorder(self) -> EvidenceRecorder:
        """Get or create the evidence recorder."""
        if self._evidence_recorder is None:
            self._evidence_recorder = EvidenceRecorder()
        return self._evidence_recorder

    @property
    def performance_analyzer(self) -> PerformanceAnalyzer:
        """Get or create the performance analyzer."""
        if self._performance_analyzer is None:
            self._performance_analyzer = PerformanceAnalyzer(
                thresholds=self.config.performance_thresholds,
            )
        return self._performance_analyzer

    @property
    def code_analyzer(self) -> CodeAnalyzer:
        """Get or create the code analyzer."""
        if self._code_analyzer is None:
            self._code_analyzer = CodeAnalyzer()
        return self._code_analyzer

    @property
    def historical_analyzer(self) -> HistoricalAnalyzer:
        """Get or create the historical analyzer."""
        if self._historical_analyzer is None:
            self._historical_analyzer = HistoricalAnalyzer()
        return self._historical_analyzer

    @property
    def skill_compiler(self) -> SkillCompiler:
        """Get or create the skill compiler."""
        if self._skill_compiler is None:
            self._skill_compiler = SkillCompiler()
        return self._skill_compiler

    @property
    def runtime_validator(self) -> RuntimeValidator:
        """Get or create the runtime validator."""
        if self._runtime_validator is None:
            self._runtime_validator = RuntimeValidator()
        return self._runtime_validator

    # ========================================================================
    # Pipeline Execution
    # ========================================================================

    def run(
        self,
        request: str | Path,
        *,
        output_type: str | None = None,
        trigger: str | None = None,
    ) -> PipelineResult:
        """
        Run the full pipeline on a skill request.

        Args:
            request: Natural language request or path to SKILL.md
            output_type: Override default output type (mcp_server, kiro_hook, steering)
            trigger: Override default hook trigger

        Returns:
            PipelineResult with all phase results
        """
        result = PipelineResult(
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        # Start async event dispatcher if needed
        if self.config.async_events and isinstance(self.event_dispatcher, AsyncEventDispatcher):
            self.event_dispatcher.start()

        try:
            # Dispatch pipeline start event
            self._dispatch_event(PhaseEventType.PIPELINE_START, {
                "request": str(request),
                "output_type": output_type or self.config.default_output_type,
            })

            # Phase 1: Triage
            if self.config.enable_triage:
                result.triage_phase = self._run_triage_phase(request)
                if not result.triage_phase.is_successful and not self.config.continue_on_error:
                    result.errors.extend(result.triage_phase.errors)
                    result.is_successful = False
                    return self._finalize_result(result, start_time)

            # Phase 2: Validation
            if self.config.enable_validation:
                result.validation_phase = self._run_validation_phase(request)
                if not result.validation_phase.is_successful and not self.config.continue_on_error:
                    result.errors.extend(result.validation_phase.errors)
                    result.is_successful = False
                    return self._finalize_result(result, start_time)

            # Phase 3: PBT (Property-Based Testing)
            if self.config.enable_pbt:
                result.pbt_phase = self._run_pbt_phase(request, result.validation_phase)
                if not result.pbt_phase.is_successful and not self.config.continue_on_error:
                    result.errors.extend(result.pbt_phase.errors)
                    result.is_successful = False
                    return self._finalize_result(result, start_time)

            # Phase 4: Diagnostics
            if self.config.enable_diagnostics:
                result.diagnostics_phase = self._run_diagnostics_phase(request, result.pbt_phase)
                if not result.diagnostics_phase.is_successful and not self.config.continue_on_error:
                    result.errors.extend(result.diagnostics_phase.errors)
                    result.is_successful = False
                    return self._finalize_result(result, start_time)

            # Phase 5: Compilation
            if self.config.enable_compilation:
                result.compilation_phase = self._run_compilation_phase(
                    request,
                    output_type=output_type or self.config.default_output_type,
                    trigger=trigger or self.config.default_hook_trigger,
                )
                if not result.compilation_phase.is_successful and not self.config.continue_on_error:
                    result.errors.extend(result.compilation_phase.errors)
                    result.is_successful = False
                    return self._finalize_result(result, start_time)

            # Dispatch pipeline complete event
            self._dispatch_event(PhaseEventType.PIPELINE_COMPLETE, {
                "is_successful": True,
                "phases_completed": 5,
            })

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Pipeline error: {e}")
            logger.error(f"Pipeline execution failed: {e}")

            # Dispatch pipeline failure event
            self._dispatch_event(PhaseEventType.PIPELINE_FAILURE, {
                "error": str(e),
            })

        finally:
            # Stop async event dispatcher if needed
            if self.config.async_events and isinstance(self.event_dispatcher, AsyncEventDispatcher):
                self.event_dispatcher.stop()

        return self._finalize_result(result, start_time)

    def run_triage_only(self, request: str) -> TriagePhaseResult:
        """
        Run only the triage phase.

        Args:
            request: Natural language skill request

        Returns:
            TriagePhaseResult with classification
        """
        return self._run_triage_phase(request)

    def run_validation_only(self, skill_path: Path | str) -> ValidationPhaseResult:
        """
        Run only the validation phase.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            ValidationPhaseResult with validation findings
        """
        return self._run_validation_phase(skill_path)

    def run_pbt_only(self, skill_path: Path | str) -> PBTPhaseResult:
        """
        Run only the PBT phase.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            PBTPhaseResult with test results
        """
        return self._run_pbt_phase(skill_path, None)

    def run_diagnostics_only(
        self,
        skill_path: Path | str,
        code: str | None = None,
    ) -> DiagnosticsPhaseResult:
        """
        Run only the diagnostics phase.

        Args:
            skill_path: Path to SKILL.md file
            code: Optional code content to analyze

        Returns:
            DiagnosticsPhaseResult with analysis reports
        """
        return self._run_diagnostics_phase(skill_path, None, code=code)

    def run_compilation_only(
        self,
        skill_path: Path | str,
        output_type: str = "mcp_server",
        trigger: str = "PreToolUse",
    ) -> CompilationPhaseResult:
        """
        Run only the compilation phase.

        Args:
            skill_path: Path to SKILL.md file
            output_type: Type of output to generate
            trigger: Hook trigger type

        Returns:
            CompilationPhaseResult with generated code
        """
        return self._run_compilation_phase(skill_path, output_type=output_type, trigger=trigger)

    # ========================================================================
    # Phase Implementations
    # ========================================================================

    def _run_triage_phase(self, request: str | Path) -> TriagePhaseResult:
        """Run the triage phase to classify the request."""
        result = TriagePhaseResult(
            phase_name="triage",
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        try:
            self._dispatch_event(PhaseEventType.SYNTHESIS_START, {"phase": "triage"})

            # Perform triage
            triage_result = self.triage_router.triage(str(request))
            result.triage_result = triage_result
            result.is_successful = True

            result.metadata["intent"] = triage_result.intent.value
            result.metadata["confidence"] = triage_result.confidence
            result.metadata["matched_skill"] = triage_result.matched_skill

            self._dispatch_event(PhaseEventType.SYNTHESIS_COMPLETE, {
                "intent": triage_result.intent.value,
                "confidence": triage_result.confidence,
            })

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Triage failed: {e}")
            logger.error(f"Triage phase failed: {e}")

            self._dispatch_event(PhaseEventType.SYNTHESIS_FAILURE, {
                "error": str(e),
            })

        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return result

    def _run_validation_phase(self, request: str | Path) -> ValidationPhaseResult:
        """Run the validation phase to check skill structure."""
        result = ValidationPhaseResult(
            phase_name="validation",
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        try:
            path = Path(request) if isinstance(request, str) and "/" in request else None

            if path and path.exists():
                # Validate from file
                validation_result = self.skill_validator.validate_file(path)
                fm_result = parse_frontmatter_file(path, validate_word_count=False)
            else:
                # Validate from content
                validation_result = self.skill_validator.validate_content(str(request))
                fm_result = parse_frontmatter(str(request), validate_word_count=False)

            result.validation_result = validation_result
            result.frontmatter_result = fm_result
            result.is_successful = validation_result.is_valid

            result.metadata["error_count"] = validation_result.error_count
            result.metadata["warning_count"] = validation_result.warning_count

            if validation_result.errors:
                result.errors.extend([e.message for e in validation_result.errors])
            if validation_result.warnings:
                result.warnings.extend([w.message for w in validation_result.warnings])

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Validation failed: {e}")
            logger.error(f"Validation phase failed: {e}")

        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return result

    def _run_pbt_phase(
        self,
        request: str | Path,
        validation_result: ValidationPhaseResult | None,
    ) -> PBTPhaseResult:
        """Run the PBT phase for property-based testing."""
        result = PBTPhaseResult(
            phase_name="pbt",
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        try:
            self._dispatch_event(PhaseEventType.PBT_START, {})

            path = Path(request) if isinstance(request, str) and "/" in request else None

            if path and path.exists():
                # Run tests from file
                eval_results = self.pbt_runner.run_skill_tests(path)
            elif validation_result and validation_result.frontmatter_result:
                # Run tests from frontmatter parameters
                fm = validation_result.frontmatter_result
                if fm.parameters:
                    schema_result = self.pbt_runner.run_schema_tests(fm.parameters)
                    eval_results = [schema_result]
                else:
                    eval_results = []
            else:
                eval_results = []

            result.eval_results = eval_results
            result.is_successful = all(r.passed for r in eval_results) if eval_results else True

            result.metadata["test_count"] = sum(r.test_count for r in eval_results)
            result.metadata["failure_count"] = sum(r.failure_count for r in eval_results)

            for r in eval_results:
                if r.errors:
                    result.errors.extend(r.errors)

            self._dispatch_event(PhaseEventType.PBT_COMPLETE, {
                "test_count": result.metadata["test_count"],
                "passed": result.is_successful,
            })

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"PBT failed: {e}")
            logger.error(f"PBT phase failed: {e}")

            self._dispatch_event(PhaseEventType.PBT_FAILURE, {"error": str(e)})

        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return result

    def _run_diagnostics_phase(
        self,
        request: str | Path,
        pbt_result: PBTPhaseResult | None,
        code: str | None = None,
    ) -> DiagnosticsPhaseResult:
        """Run the diagnostics phase for performance and code analysis."""
        result = DiagnosticsPhaseResult(
            phase_name="diagnostics",
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        try:
            self._dispatch_event(PhaseEventType.DIAGNOSTICS_START, {})

            path = Path(request) if isinstance(request, str) and "/" in request else None

            # Performance analysis
            if pbt_result and pbt_result.eval_results:
                metrics = {
                    "execution_time_ms": sum(r.performance_ms for r in pbt_result.eval_results),
                }
                result.performance_report = self.performance_analyzer.analyze(
                    path.stem if path else "skill",
                    metrics,
                )

            # Code analysis
            if code or (path and path.exists()):
                code_content = code or path.read_text() if path else None
                if code_content:
                    result.code_report = self.code_analyzer.analyze_code(
                        path.stem if path else "skill",
                        code_content,
                        str(path) if path else "<inline>",
                    )

            # Historical analysis (if available)
            if self._historical_analyzer and self._historical_analyzer._history:
                result.historical_report = self.historical_analyzer.analyze()

            # Determine success
            has_critical = (
                result.performance_report and result.performance_report.has_critical_issues
            ) or (
                result.code_report and result.code_report.has_errors
            )
            result.is_successful = not has_critical

            if result.performance_report:
                result.metadata["performance_issues"] = result.performance_report.issue_count
            if result.code_report:
                result.metadata["code_issues"] = result.code_report.error_count
                result.metadata["has_security_issues"] = result.code_report.has_security_issues

            self._dispatch_event(PhaseEventType.DIAGNOSTICS_COMPLETE, {
                "is_successful": result.is_successful,
            })

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Diagnostics failed: {e}")
            logger.error(f"Diagnostics phase failed: {e}")

            self._dispatch_event(PhaseEventType.DIAGNOSTICS_FAILURE, {"error": str(e)})

        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return result

    def _run_compilation_phase(
        self,
        request: str | Path,
        output_type: str = "mcp_server",
        trigger: str = "PreToolUse",
    ) -> CompilationPhaseResult:
        """Run the compilation phase to generate outputs."""
        result = CompilationPhaseResult(
            phase_name="compilation",
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        try:
            self._dispatch_event(PhaseEventType.MCP_COMPILE_START, {
                "output_type": output_type,
            })

            path = Path(request) if isinstance(request, str) and "/" in request else None

            if not path or not path.exists():
                result.is_successful = False
                result.errors.append("Compilation requires a valid skill file path")
                return self._complete_compilation_phase(result, start_time)

            # Compile based on output type
            if output_type == "mcp_server":
                compilation_result = self.skill_compiler.compile_to_mcp(path)
            elif output_type == "kiro_hook":
                compilation_result = self.skill_compiler.compile_to_hook(
                    path, trigger=trigger
                )
            elif output_type == "steering":
                compilation_result = self.skill_compiler.compile_to_steering(path)
            else:
                result.is_successful = False
                result.errors.append(f"Unknown output type: {output_type}")
                return self._complete_compilation_phase(result, start_time)

            result.compilation_result = compilation_result
            result.is_successful = compilation_result.is_successful

            if compilation_result.errors:
                result.errors.extend(compilation_result.errors)
            if compilation_result.warnings:
                result.warnings.extend(compilation_result.warnings)

            # Runtime validation
            if compilation_result.is_successful and compilation_result.generated_code:
                if output_type == "mcp_server":
                    result.runtime_validation = self.runtime_validator.validate_python(
                        compilation_result.generated_code
                    )
                # Add TypeScript validation when needed

            result.metadata["output_type"] = output_type
            result.metadata["code_length"] = len(compilation_result.generated_code)

            self._dispatch_event(PhaseEventType.MCP_COMPILE_COMPLETE, {
                "output_type": output_type,
                "is_successful": result.is_successful,
            })

        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Compilation failed: {e}")
            logger.error(f"Compilation phase failed: {e}")

            self._dispatch_event(PhaseEventType.MCP_COMPILE_FAILURE, {"error": str(e)})

        return self._complete_compilation_phase(result, start_time)

    def _complete_compilation_phase(
        self,
        result: CompilationPhaseResult,
        start_time: datetime,
    ) -> CompilationPhaseResult:
        """Complete the compilation phase and set timestamps."""
        result.completed_at = datetime.utcnow().isoformat()
        result.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result

    # ========================================================================
    # Event Handling
    # ========================================================================

    def _dispatch_event(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> list[HookExecutionResult]:
        """Dispatch an event to registered hooks."""
        if not self.config.enable_events:
            return []

        return self.event_dispatcher.dispatch(event_type, event_data)

    def register_hook(
        self,
        hook_id: str,
        event_type: PhaseEventType,
        action: Callable[[dict[str, Any]], None] | str,
        **kwargs: Any,
    ) -> bool:
        """
        Register a hook for a pipeline event.

        Args:
            hook_id: Unique identifier for the hook
            event_type: Event type to hook
            action: Callback function or command string
            **kwargs: Additional hook configuration

        Returns:
            True if registration succeeded
        """
        return self.event_registry.register_hook(
            hook_id,
            event_type,
            action,
            **kwargs,
        )

    def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a hook by ID."""
        return self.event_registry.unregister_hook(hook_id)

    # ========================================================================
    # Custom Phase Handlers
    # ========================================================================

    def register_custom_phase(
        self,
        phase_name: str,
        handler: Callable[..., PhaseResult],
    ) -> None:
        """
        Register a custom phase handler.

        Args:
            phase_name: Name of the custom phase
            handler: Function to handle the phase
        """
        self._custom_handlers[phase_name] = handler

    def run_custom_phase(
        self,
        phase_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> PhaseResult | None:
        """
        Run a custom phase by name.

        Args:
            phase_name: Name of the custom phase
            *args: Arguments to pass to the handler
            **kwargs: Keyword arguments to pass to the handler

        Returns:
            PhaseResult from the custom handler, or None if not found
        """
        handler = self._custom_handlers.get(phase_name)
        if handler:
            return handler(*args, **kwargs)
        return None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _finalize_result(
        self,
        result: PipelineResult,
        start_time: datetime,
    ) -> PipelineResult:
        """Finalize the pipeline result with timestamps."""
        result.completed_at = datetime.utcnow().isoformat()
        result.total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return result

    def diagnose_workspace(self, workspace_root: Path | str) -> DiagnosticReport:
        """
        Run ecosystem diagnostics on a workspace.

        Args:
            workspace_root: Root directory of the workspace

        Returns:
            DiagnosticReport with ecosystem health findings
        """
        doctor = EcosystemDoctor()
        return doctor.diagnose(workspace_root)


# ============================================================================
# Pipeline Factory Functions
# ============================================================================

def create_default_pipeline(
    *,
    available_skills: list[str] | None = None,
) -> SkillForgePipeline:
    """
    Create a pipeline with default configuration.

    Args:
        available_skills: List of known skill names for triage

    Returns:
        Configured SkillForgePipeline instance
    """
    config = PipelineConfig(
        available_skills=available_skills,
    )
    return SkillForgePipeline(config=config)


def create_compliance_pipeline() -> SkillForgePipeline:
    """
    Create a pipeline configured for cloud compliance checking.

    Returns:
        SkillForgePipeline configured for compliance skills
    """
    config = PipelineConfig(
        require_parameters=True,
        max_examples=100,  # More thorough testing
        default_output_type="mcp_server",
        available_skills=[
            "aws-audit",
            "aws-cost-analysis",
            "aws-security-check",
            "cloud-compliance-check",
        ],
    )
    return SkillForgePipeline(config=config)


def create_narrative_pipeline() -> SkillForgePipeline:
    """
    Create a pipeline configured for narrative skill synthesis.

    Returns:
        SkillForgePipeline configured for narrative/game skills
    """
    config = PipelineConfig(
        require_parameters=False,
        max_body_words=3000,  # Allow longer narratives
        max_examples=30,
        default_output_type="kiro_hook",
        default_hook_trigger="UserPromptSubmit",
    )
    return SkillForgePipeline(config=config)
