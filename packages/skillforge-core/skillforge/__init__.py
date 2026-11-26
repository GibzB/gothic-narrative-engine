"""
Kiro-SkillForge Core Engine

A modular Python skeleton framework that turns natural language requests into
validated, property-tested AI skills and compiles them into Model Context Protocol
(MCP) tools and Kiro Agent Hooks.

4-Phase Pipeline:
1. Synthesis (triage + init + schema) - Route requests and generate SKILL.md specs
2. Evidence-Driven Evaluation & PBT (validate + evals) - Structural linting and PBT
3. Ecosystem Diagnostics (doctor + friction) - Scan .kiro/ for health issues
4. Cross-Runtime Compilation (compile + mcp) - Transpile to MCP servers/hooks
"""

__version__ = "0.1.0"
__author__ = "Kiro-SkillForge Team"

from skillforge.frontmatter import parse_frontmatter, FrontmatterResult
from skillforge.triage import TriageRouter, TriageIntent
from skillforge.validate import SkillValidator, ValidationResult
from skillforge.evals import (
    PBTRunner,
    EvalResult,
    RegressionChecker,
    RegressionBaseline,
    PerformanceDrift,
    EvidenceRecorder,
    EvidenceRecord,
)
from skillforge.diagnostics import (
    PerformanceAnalyzer,
    PerformanceIssue,
    PerformanceReport,
    CodeAnalyzer,
    CodeIssue,
    CodeAnalysisReport,
    HistoricalAnalyzer,
    FailurePattern,
    HistoricalReport,
    TestRunRecord,
)
from skillforge.doctor import EcosystemDoctor, DiagnosticReport
from skillforge.compiler import (
    SkillCompiler,
    CompilationResult,
    MCPCompiler,
    MCPToolDefinition,
    HookCompiler,
    HookDefinition,
    HookTrigger,
    HookActionType,
    RuntimeValidator,
    RuntimeValidationResult,
)
from skillforge.mcp_server import MCPServer
from skillforge.events import (
    EventRegistry,
    EventDispatcher,
    AsyncHookQueue,
    AsyncEventDispatcher,
    PhaseEventType,
    HookExecutionStatus,
    RegisteredHook,
    HookExecutionResult,
)
from skillforge.gatekeeper import (
    AdversarialGatekeeper,
    MaliciousInputGenerator,
    ExploitMonitor,
    VulnerabilityRecorder,
    MaliciousInput,
    Anomaly,
    VulnerabilityReport,
    VulnerabilityType,
    VulnerabilitySeverity,
    AnomalyType,
    GatekeeperResult,
    GatekeeperConfig,
)
from skillforge.governance import (
    TimestampRecorder,
    VersionTracker,
    PermissionEnforcer,
    GovernanceModule,
    LifecycleEventType,
    PermissionLevel,
    TimestampRecord,
    VersionSnapshot,
    Permission,
    GovernanceRecord,
)
from skillforge.doctor import (
    ConfigValidator,
    ConfigValidationResult,
    HealthReporter,
    HealthReport,
    EnvironmentStatus,
    ConflictAnalyzer,
    ConflictAnalysisReport,
    IdentifierCollision,
    CircularDependency,
    MissingCredential,
    run_full_diagnostics,
)
from skillforge.pipeline import (
    SkillForgePipeline,
    PipelineConfig,
    PipelineResult,
    PhaseResult,
    TriagePhaseResult,
    ValidationPhaseResult,
    PBTPhaseResult,
    DiagnosticsPhaseResult,
    CompilationPhaseResult,
    create_default_pipeline,
    create_compliance_pipeline,
    create_narrative_pipeline,
)

__all__ = [
    "__version__",
    # Frontmatter
    "parse_frontmatter",
    "FrontmatterResult",
    # Triage
    "TriageRouter",
    "TriageIntent",
    # Validation
    "SkillValidator",
    "ValidationResult",
    # Evaluation
    "PBTRunner",
    "EvalResult",
    "RegressionChecker",
    "RegressionBaseline",
    "PerformanceDrift",
    "EvidenceRecorder",
    "EvidenceRecord",
    # Diagnostics
    "PerformanceAnalyzer",
    "PerformanceIssue",
    "PerformanceReport",
    "CodeAnalyzer",
    "CodeIssue",
    "CodeAnalysisReport",
    "HistoricalAnalyzer",
    "FailurePattern",
    "HistoricalReport",
    "TestRunRecord",
    # Doctor
    "EcosystemDoctor",
    "DiagnosticReport",
    # Compiler
    "SkillCompiler",
    "CompilationResult",
    "MCPCompiler",
    "MCPToolDefinition",
    "HookCompiler",
    "HookDefinition",
    "HookTrigger",
    "HookActionType",
    "RuntimeValidator",
    "RuntimeValidationResult",
    # MCP Server
    "MCPServer",
    # Events
    "EventRegistry",
    "EventDispatcher",
    "AsyncHookQueue",
    "AsyncEventDispatcher",
    "PhaseEventType",
    "HookExecutionStatus",
    "RegisteredHook",
    "HookExecutionResult",
    # Gatekeeper
    "AdversarialGatekeeper",
    "MaliciousInputGenerator",
    "ExploitMonitor",
    "VulnerabilityRecorder",
    "MaliciousInput",
    "Anomaly",
    "VulnerabilityReport",
    "VulnerabilityType",
    "VulnerabilitySeverity",
    "AnomalyType",
    "GatekeeperResult",
    "GatekeeperConfig",
    # Governance
    "TimestampRecorder",
    "VersionTracker",
    "PermissionEnforcer",
    "GovernanceModule",
    "LifecycleEventType",
    "PermissionLevel",
    "TimestampRecord",
    "VersionSnapshot",
    "Permission",
    "GovernanceRecord",
    # Doctor enhancements
    "ConfigValidator",
    "ConfigValidationResult",
    "HealthReporter",
    "HealthReport",
    "EnvironmentStatus",
    "ConflictAnalyzer",
    "ConflictAnalysisReport",
    "IdentifierCollision",
    "CircularDependency",
    "MissingCredential",
    "run_full_diagnostics",
    # Pipeline
    "SkillForgePipeline",
    "PipelineConfig",
    "PipelineResult",
    "PhaseResult",
    "TriagePhaseResult",
    "ValidationPhaseResult",
    "PBTPhaseResult",
    "DiagnosticsPhaseResult",
    "CompilationPhaseResult",
    "create_default_pipeline",
    "create_compliance_pipeline",
    "create_narrative_pipeline",
]
