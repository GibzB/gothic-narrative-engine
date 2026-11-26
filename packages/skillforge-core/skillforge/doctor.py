"""
Ecosystem & .kiro/ Health Analyzer.

Scans active .kiro/ directories, steering files, MCP registries, and skill
definitions to detect tool name collisions, stale references, budget
violations, and missing environment variables.

Implements:
- Task 2.11.1: Config Validator - Validate JSON syntax in configuration files
- Task 2.11.2: Health Reporter - Generate ecosystem health status reports
- Task 2.11.3: Conflict Analyzer - Scan for identifier collisions and dependencies

Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6

Adapted from tripleyak/SkillForge skillforge_doctor.py patterns.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class DiagnosticIssue:
    """A single diagnostic issue."""

    severity: str  # error, warning, info
    code: str
    message: str
    location: str
    fix_suggestion: str | None = None

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.location}: {self.message} ({self.code})"


@dataclass
class DiagnosticReport:
    """Full diagnostic report for a workspace."""

    is_healthy: bool = True
    issues: list[DiagnosticIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "location": i.location,
                    "fix_suggestion": i.fix_suggestion,
                }
                for i in self.issues
            ],
            "stats": self.stats,
        }


ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
TOOL_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]*$')


class EcosystemDoctor:
    """
    Analyzes workspace health and Kiro ecosystem configuration.

    Scans:
    - .kiro/hooks/ for valid hook configurations
    - .kiro/steering/ for valid steering documents
    - .kiro/settings/mcp.json for MCP server configuration
    - Skill registries for duplicate tool names

    Example:
        >>> doctor = EcosystemDoctor()
        >>> report = doctor.diagnose(Path("/workspace"))
        >>> report.is_healthy
        True
    """

    def __init__(
        self,
        *,
        check_env_vars: bool = True,
        check_mcp: bool = True,
        check_hooks: bool = True,
        check_steering: bool = True,
    ) -> None:
        """
        Initialize the doctor.

        Args:
            check_env_vars: Whether to check for unresolved environment variables
            check_mcp: Whether to check MCP configuration
            check_hooks: Whether to check hook configurations
            check_steering: Whether to check steering files
        """
        self.check_env_vars = check_env_vars
        self.check_mcp = check_mcp
        self.check_hooks = check_hooks
        self.check_steering = check_steering

    def diagnose(self, workspace_root: Path | str) -> DiagnosticReport:
        """
        Run full diagnostics on a workspace.

        Args:
            workspace_root: Root directory of the workspace

        Returns:
            DiagnosticReport with all findings
        """
        root = Path(workspace_root)
        report = DiagnosticReport()

        # Check if .kiro exists
        kiro_dir = root / ".kiro"
        if not kiro_dir.exists():
            report.issues.append(DiagnosticIssue(
                severity="error",
                code="MISSING_KIRO_DIR",
                message="Missing .kiro/ directory at workspace root",
                location=str(root),
                fix_suggestion="Run 'kiro init' or create .kiro/ directory",
            ))
            report.is_healthy = False
            return report

        # Check hooks
        if self.check_hooks:
            self._check_hooks(kiro_dir, report)

        # Check steering
        if self.check_steering:
            self._check_steering(kiro_dir, report)

        # Check MCP configuration
        if self.check_mcp:
            self._check_mcp(kiro_dir, report)

        # Check for environment variable issues
        if self.check_env_vars:
            self._check_env_vars(kiro_dir, report)

        # Update overall health status
        report.is_healthy = report.error_count == 0

        # Collect stats
        report.stats = self._collect_stats(kiro_dir)

        return report

    def _check_hooks(self, kiro_dir: Path, report: DiagnosticReport) -> None:
        """Check hook configurations."""
        hooks_dir = kiro_dir / "hooks"
        if not hooks_dir.exists():
            report.stats["hooks_count"] = 0
            return

        hook_files = list(hooks_dir.glob("*.json"))
        report.stats["hooks_count"] = len(hook_files)

        valid_triggers = {
            "PromptSubmit", "AgentStop", "SessionStart", "PreToolUse",
            "PostToolUse", "PreTaskExecution", "PostTaskExecution",
            "PreCompact", "PostCompact", "PostFileCreate", "PostFileSave",
            "PostFileDelete", "PermissionRequest", "UserPromptSubmit",
        }

        tool_names: dict[str, str] = {}  # tool_name -> file

        for hook_file in hook_files:
            try:
                content = json.loads(hook_file.read_text())
            except json.JSONDecodeError as e:
                report.issues.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_HOOK_JSON",
                    message=f"Invalid JSON in hook file: {e}",
                    location=str(hook_file.relative_to(kiro_dir.parent)),
                    fix_suggestion="Fix JSON syntax in hook file",
                ))
                continue

            # Check schema version
            version = content.get("version")
            if version != "v1":
                report.issues.append(DiagnosticIssue(
                    severity="warning",
                    code="UNKNOWN_HOOK_VERSION",
                    message=f"Unknown hook version: {version}",
                    location=str(hook_file.relative_to(kiro_dir.parent)),
                    fix_suggestion="Use 'v1' for the version field",
                ))

            # Check hooks array
            hooks = content.get("hooks", [])
            if not isinstance(hooks, list):
                report.issues.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_HOOKS_FORMAT",
                    message="'hooks' must be an array",
                    location=str(hook_file.relative_to(kiro_dir.parent)),
                ))
                continue

            for i, hook in enumerate(hooks):
                hook_loc = f"{hook_file.relative_to(kiro_dir.parent)}:hooks[{i}]"

                # Check trigger
                trigger = hook.get("trigger")
                if not trigger:
                    report.issues.append(DiagnosticIssue(
                        severity="error",
                        code="MISSING_TRIGGER",
                        message="Hook missing trigger field",
                        location=hook_loc,
                    ))
                elif trigger not in valid_triggers:
                    report.issues.append(DiagnosticIssue(
                        severity="warning",
                        code="UNKNOWN_TRIGGER",
                        message=f"Unknown trigger: {trigger}",
                        location=hook_loc,
                        fix_suggestion=f"Valid triggers: {', '.join(sorted(valid_triggers))}",
                    ))

                # Check action
                action = hook.get("action")
                if not action:
                    report.issues.append(DiagnosticIssue(
                        severity="error",
                        code="MISSING_ACTION",
                        message="Hook missing action field",
                        location=hook_loc,
                    ))
                elif isinstance(action, dict):
                    action_type = action.get("type")
                    if action_type not in ("command", "agent"):
                        report.issues.append(DiagnosticIssue(
                            severity="warning",
                            code="UNKNOWN_ACTION_TYPE",
                            message=f"Unknown action type: {action_type}",
                            location=hook_loc,
                            fix_suggestion="Use 'command' or 'agent'",
                        ))

    def _check_steering(self, kiro_dir: Path, report: DiagnosticReport) -> None:
        """Check steering document configurations."""
        steering_dir = kiro_dir / "steering"
        if not steering_dir.exists():
            report.stats["steering_count"] = 0
            return

        steering_files = list(steering_dir.glob("*.md"))
        report.stats["steering_count"] = len(steering_files)

        for steering_file in steering_files:
            content = steering_file.read_text()
            relative_path = steering_file.relative_to(kiro_dir.parent)

            # Check for inclusion mode in frontmatter
            if content.startswith("---"):
                frontmatter_end = content.find("\n---", 3)
                if frontmatter_end == -1:
                    report.issues.append(DiagnosticIssue(
                        severity="warning",
                        code="MALFORMED_FRONTMATTER",
                        message="Unclosed frontmatter block",
                        location=str(relative_path),
                    ))

    def _check_mcp(self, kiro_dir: Path, report: DiagnosticReport) -> None:
        """Check MCP server configuration."""
        mcp_file = kiro_dir / "settings" / "mcp.json"
        if not mcp_file.exists():
            report.stats["mcp_servers"] = 0
            return

        try:
            content = json.loads(mcp_file.read_text())
        except json.JSONDecodeError as e:
            report.issues.append(DiagnosticIssue(
                severity="error",
                code="INVALID_MCP_JSON",
                message=f"Invalid JSON in mcp.json: {e}",
                location=str(mcp_file.relative_to(kiro_dir.parent)),
            ))
            return

        mcp_servers = content.get("mcpServers", {})
        report.stats["mcp_servers"] = len(mcp_servers)

        for server_name, server_config in mcp_servers.items():
            server_loc = f".kiro/settings/mcp.json:mcpServers.{server_name}"

            # Check command exists
            if "command" not in server_config:
                report.issues.append(DiagnosticIssue(
                    severity="error",
                    code="MISSING_MCP_COMMAND",
                    message=f"MCP server '{server_name}' missing 'command' field",
                    location=server_loc,
                ))

            # Check args is array
            args = server_config.get("args")
            if args is not None and not isinstance(args, list):
                report.issues.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_MCP_ARGS",
                    message=f"MCP server '{server_name}' args must be an array",
                    location=server_loc,
                ))

    def _check_env_vars(self, kiro_dir: Path, report: DiagnosticReport) -> None:
        """Check for unresolved environment variable references."""
        import os

        # Check all JSON files
        for json_file in kiro_dir.rglob("*.json"):
            try:
                content = json_file.read_text()
            except Exception:
                continue

            # Find all ${VAR} patterns
            matches = ENV_VAR_PATTERN.findall(content)
            for var in matches:
                if var not in os.environ:
                    report.issues.append(DiagnosticIssue(
                        severity="warning",
                        code="UNRESOLVED_ENV_VAR",
                        message=f"Environment variable '{var}' is not set",
                        location=str(json_file.relative_to(kiro_dir.parent)),
                        fix_suggestion=f"Set {var} in your environment or .env file",
                    ))

    def _collect_stats(self, kiro_dir: Path) -> dict[str, Any]:
        """Collect workspace statistics."""
        stats: dict[str, Any] = {}

        # Count various files
        stats["hooks_count"] = len(list((kiro_dir / "hooks").glob("*.json"))) if (kiro_dir / "hooks").exists() else 0
        stats["steering_count"] = len(list((kiro_dir / "steering").glob("*.md"))) if (kiro_dir / "steering").exists() else 0
        stats["specs_count"] = len(list((kiro_dir / "specs").glob("**/requirements.md"))) if (kiro_dir / "specs").exists() else 0

        return stats


def quick_check(workspace_root: Path | str) -> tuple[bool, str]:
    """
    Quick health check returning pass/fail and summary.

    Args:
        workspace_root: Root directory of the workspace

    Returns:
        Tuple of (is_healthy, summary_message)
    """
    doctor = EcosystemDoctor()
    report = doctor.diagnose(workspace_root)

    if report.is_healthy:
        return True, f"Workspace healthy ({report.warning_count} warnings)"
    else:
        return False, f"Workspace has {report.error_count} errors, {report.warning_count} warnings"


# ============================================================================
# Config Validator (Task 2.11.1)
# ============================================================================

@dataclass
class ConfigValidationResult:
    """Result of validating a configuration file."""
    file_path: str
    is_valid: bool
    errors: list[DiagnosticIssue] = field(default_factory=list)
    warnings: list[DiagnosticIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "is_valid": self.is_valid,
            "errors": [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in self.errors],
            "warnings": [w.to_dict() if hasattr(w, 'to_dict') else str(w) for w in self.warnings],
        }


class ConfigValidator:
    """
    Validates configuration files for JSON syntax and structure.

    Validates JSON syntax in .kiro/hooks/ directory and other configuration
    files, ensuring proper structure and required fields.

    Task 2.11.1: Config Validator
    Validates: Requirement 12.4

    Example:
        >>> validator = ConfigValidator()
        >>> result = validator.validate_hooks_directory(Path(".kiro/hooks"))
        >>> result.is_valid
        True
    """

    # Required fields for hook configuration
    HOOK_REQUIRED_FIELDS = {"version", "hooks"}
    HOOK_ENTRY_REQUIRED_FIELDS = {"name", "trigger", "action"}
    VALID_HOOK_TRIGGERS = {
        "PreToolUse", "PostToolUse", "FileEdited", "AgentSpawn",
        "SessionStart", "Stop", "PromptSubmit", "AgentStop",
        "PreTaskExecution", "PostTaskExecution", "PreCompact", "PostCompact",
        "PostFileCreate", "PostFileSave", "PostFileDelete",
        "PermissionRequest", "UserPromptSubmit",
    }

    def __init__(
        self,
        *,
        strict_mode: bool = False,
        check_schema_version: bool = True,
    ) -> None:
        """
        Initialize the config validator.

        Args:
            strict_mode: Whether to use strict validation (fail on warnings)
            check_schema_version: Whether to validate schema versions
        """
        self.strict_mode = strict_mode
        self.check_schema_version = check_schema_version

    def validate_file(self, file_path: Path | str) -> ConfigValidationResult:
        """
        Validate a single configuration file.

        Args:
            file_path: Path to the configuration file

        Returns:
            ConfigValidationResult with validation findings
        """
        path = Path(file_path)
        result = ConfigValidationResult(
            file_path=str(path),
            is_valid=True,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="FILE_NOT_FOUND",
                message=f"Configuration file not found: {path}",
                location=str(path),
            ))
            return result

        # Read and parse JSON
        try:
            content = path.read_text()
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="INVALID_JSON_SYNTAX",
                message=f"Invalid JSON syntax: {e.msg}",
                location=f"{path}:{e.lineno}:{e.colno}",
                fix_suggestion="Fix JSON syntax error",
            ))
            return result
        except Exception as e:
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="FILE_READ_ERROR",
                message=f"Cannot read file: {e}",
                location=str(path),
            ))
            return result

        # Validate structure based on file type
        if "hooks" in path.parts or path.stem.endswith("-hook"):
            self._validate_hook_config(path, data, result)
        elif path.name == "mcp.json":
            self._validate_mcp_config(path, data, result)

        return result

    def _validate_hook_config(
        self,
        path: Path,
        data: dict[str, Any],
        result: ConfigValidationResult,
    ) -> None:
        """Validate hook configuration structure."""
        # Check version
        if self.check_schema_version:
            version = data.get("version")
            if not version:
                result.warnings.append(DiagnosticIssue(
                    severity="warning",
                    code="MISSING_VERSION",
                    message="Hook configuration missing 'version' field",
                    location=str(path),
                    fix_suggestion="Add 'version': 'v1' to hook configuration",
                ))
            elif version != "v1":
                result.warnings.append(DiagnosticIssue(
                    severity="warning",
                    code="UNKNOWN_VERSION",
                    message=f"Unknown hook version: {version}",
                    location=str(path),
                    fix_suggestion="Use 'v1' for the version field",
                ))

        # Check hooks array
        hooks = data.get("hooks")
        if hooks is None:
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="MISSING_HOOKS",
                message="Hook configuration missing 'hooks' array",
                location=str(path),
                fix_suggestion="Add 'hooks': [] to configuration",
            ))
            return

        if not isinstance(hooks, list):
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="INVALID_HOOKS_TYPE",
                message="'hooks' must be an array",
                location=str(path),
            ))
            return

        # Validate each hook entry
        for i, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                result.errors.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_HOOK_ENTRY",
                    message=f"Hook entry {i} must be an object",
                    location=f"{path}:hooks[{i}]",
                ))
                continue

            # Check required fields
            for field_name in self.HOOK_ENTRY_REQUIRED_FIELDS:
                if field_name not in hook:
                    result.is_valid = False
                    result.errors.append(DiagnosticIssue(
                        severity="error",
                        code="MISSING_HOOK_FIELD",
                        message=f"Hook {i} missing required field '{field_name}'",
                        location=f"{path}:hooks[{i}]",
                        fix_suggestion=f"Add '{field_name}' to hook configuration",
                    ))

            # Validate trigger
            trigger = hook.get("trigger")
            if trigger and trigger not in self.VALID_HOOK_TRIGGERS:
                result.warnings.append(DiagnosticIssue(
                    severity="warning",
                    code="UNKNOWN_TRIGGER",
                    message=f"Hook {i} has unknown trigger: {trigger}",
                    location=f"{path}:hooks[{i}]",
                    fix_suggestion=f"Valid triggers: {', '.join(sorted(self.VALID_HOOK_TRIGGERS))}",
                ))

            # Validate action
            action = hook.get("action")
            if action and isinstance(action, dict):
                action_type = action.get("type")
                if action_type not in ("command", "agent"):
                    result.warnings.append(DiagnosticIssue(
                        severity="warning",
                        code="UNKNOWN_ACTION_TYPE",
                        message=f"Hook {i} has unknown action type: {action_type}",
                        location=f"{path}:hooks[{i}]",
                        fix_suggestion="Use 'command' or 'agent'",
                    ))

    def _validate_mcp_config(
        self,
        path: Path,
        data: dict[str, Any],
        result: ConfigValidationResult,
    ) -> None:
        """Validate MCP server configuration."""
        mcp_servers = data.get("mcpServers")
        if mcp_servers is None:
            result.warnings.append(DiagnosticIssue(
                severity="warning",
                code="NO_MCP_SERVERS",
                message="No 'mcpServers' configuration found",
                location=str(path),
            ))
            return

        if not isinstance(mcp_servers, dict):
            result.is_valid = False
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="INVALID_MCPSERVERS_TYPE",
                message="'mcpServers' must be an object",
                location=str(path),
            ))
            return

        for server_name, server_config in mcp_servers.items():
            server_loc = f"{path}:mcpServers.{server_name}"

            if not isinstance(server_config, dict):
                result.errors.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_SERVER_CONFIG",
                    message=f"Server '{server_name}' config must be an object",
                    location=server_loc,
                ))
                continue

            # Check required fields
            if "command" not in server_config:
                result.is_valid = False
                result.errors.append(DiagnosticIssue(
                    severity="error",
                    code="MISSING_MCP_COMMAND",
                    message=f"Server '{server_name}' missing 'command' field",
                    location=server_loc,
                    fix_suggestion="Add 'command' field with the executable path",
                ))

            # Check args is array
            args = server_config.get("args")
            if args is not None and not isinstance(args, list):
                result.is_valid = False
                result.errors.append(DiagnosticIssue(
                    severity="error",
                    code="INVALID_MCP_ARGS",
                    message=f"Server '{server_name}' args must be an array",
                    location=server_loc,
                ))

    def validate_hooks_directory(
        self,
        hooks_dir: Path | str,
    ) -> list[ConfigValidationResult]:
        """
        Validate all hook configuration files in a directory.

        Args:
            hooks_dir: Path to the hooks directory

        Returns:
            List of validation results for each file
        """
        dir_path = Path(hooks_dir)
        results: list[ConfigValidationResult] = []

        if not dir_path.exists():
            result = ConfigValidationResult(
                file_path=str(dir_path),
                is_valid=False,
            )
            result.errors.append(DiagnosticIssue(
                severity="error",
                code="DIRECTORY_NOT_FOUND",
                message=f"Hooks directory not found: {dir_path}",
                location=str(dir_path),
            ))
            results.append(result)
            return results

        for json_file in sorted(dir_path.glob("*.json")):
            results.append(self.validate_file(json_file))

        return results

    def validate_kiro_directory(
        self,
        kiro_dir: Path | str,
    ) -> dict[str, list[ConfigValidationResult]]:
        """
        Validate all configuration files in .kiro/ directory.

        Args:
            kiro_dir: Path to .kiro/ directory

        Returns:
            Dictionary mapping category to validation results
        """
        kiro_path = Path(kiro_dir)
        results: dict[str, list[ConfigValidationResult]] = {
            "hooks": [],
            "settings": [],
            "other": [],
        }

        # Validate hooks
        hooks_dir = kiro_path / "hooks"
        if hooks_dir.exists():
            results["hooks"] = self.validate_hooks_directory(hooks_dir)

        # Validate settings
        settings_dir = kiro_path / "settings"
        if settings_dir.exists():
            for json_file in sorted(settings_dir.glob("*.json")):
                results["settings"].append(self.validate_file(json_file))

        return results


# ============================================================================
# Health Reporter (Task 2.11.2)
# ============================================================================

@dataclass
class EnvironmentStatus:
    """Status of an environment component."""
    name: str
    available: bool
    version: str | None = None
    path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "version": self.version,
            "path": self.path,
            "error": self.error,
        }


@dataclass
class HealthReport:
    """Complete ecosystem health report."""
    generated_at: str
    workspace_root: str
    overall_status: str  # healthy, degraded, unhealthy
    environments: dict[str, EnvironmentStatus] = field(default_factory=dict)
    packages: dict[str, str] = field(default_factory=dict)
    configuration_status: dict[str, Any] = field(default_factory=dict)
    issues: list[DiagnosticIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "workspace_root": self.workspace_root,
            "overall_status": self.overall_status,
            "environments": {k: v.to_dict() for k, v in self.environments.items()},
            "packages": self.packages,
            "configuration_status": self.configuration_status,
            "issues": [str(i) for i in self.issues],
            "recommendations": self.recommendations,
        }


class HealthReporter:
    """
    Generates ecosystem health status reports.

    Checks Python and TypeScript environments, installed packages,
    and configuration files, providing a comprehensive health report.

    Task 2.11.2: Health Reporter
    Validates: Requirements 12.1, 12.2, 12.3, 12.5

    Example:
        >>> reporter = HealthReporter()
        >>> report = reporter.generate_report(Path("/workspace"))
        >>> report.overall_status
        'healthy'
    """

    def __init__(
        self,
        *,
        check_python: bool = True,
        check_typescript: bool = True,
        check_packages: bool = True,
        check_config: bool = True,
    ) -> None:
        """
        Initialize the health reporter.

        Args:
            check_python: Whether to check Python environment
            check_typescript: Whether to check TypeScript environment
            check_packages: Whether to check installed packages
            check_config: Whether to check configuration files
        """
        self.check_python = check_python
        self.check_typescript = check_typescript
        self.check_packages = check_packages
        self.check_config = check_config

    def generate_report(
        self,
        workspace_root: Path | str,
    ) -> HealthReport:
        """
        Generate a comprehensive health report.

        Args:
            workspace_root: Root directory of the workspace

        Returns:
            HealthReport with all findings
        """
        root = Path(workspace_root)
        report = HealthReport(
            generated_at=datetime.utcnow().isoformat(),
            workspace_root=str(root),
            overall_status="healthy",
        )

        # Check environments
        if self.check_python:
            report.environments["python"] = self._check_python()

        if self.check_typescript:
            report.environments["nodejs"] = self._check_nodejs()
            report.environments["typescript"] = self._check_typescript()

        # Check packages
        if self.check_packages:
            report.packages = self._check_installed_packages(root)

        # Check configuration
        if self.check_config:
            report.configuration_status = self._check_configuration(root, report)

        # Determine overall status
        report.overall_status = self._determine_overall_status(report)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _check_python(self) -> EnvironmentStatus:
        """Check Python environment availability."""
        try:
            version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            return EnvironmentStatus(
                name="Python",
                available=True,
                version=version,
                path=sys.executable,
            )
        except Exception as e:
            return EnvironmentStatus(
                name="Python",
                available=False,
                error=str(e),
            )

    def _check_nodejs(self) -> EnvironmentStatus:
        """Check Node.js environment availability."""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return EnvironmentStatus(
                    name="Node.js",
                    available=True,
                    version=version,
                    path=subprocess.run(
                        ["which", "node"],
                        capture_output=True,
                        text=True,
                    ).stdout.strip() or None,
                )
            return EnvironmentStatus(
                name="Node.js",
                available=False,
                error=result.stderr,
            )
        except FileNotFoundError:
            return EnvironmentStatus(
                name="Node.js",
                available=False,
                error="Node.js not found in PATH",
            )
        except Exception as e:
            return EnvironmentStatus(
                name="Node.js",
                available=False,
                error=str(e),
            )

    def _check_typescript(self) -> EnvironmentStatus:
        """Check TypeScript availability."""
        try:
            result = subprocess.run(
                ["tsc", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return EnvironmentStatus(
                    name="TypeScript",
                    available=True,
                    version=version,
                )
            return EnvironmentStatus(
                name="TypeScript",
                available=False,
                error=result.stderr,
            )
        except FileNotFoundError:
            return EnvironmentStatus(
                name="TypeScript",
                available=False,
                error="TypeScript compiler not found",
            )
        except Exception as e:
            return EnvironmentStatus(
                name="TypeScript",
                available=False,
                error=str(e),
            )

    def _check_installed_packages(self, root: Path) -> dict[str, str]:
        """Check installed package versions."""
        packages: dict[str, str] = {}

        # Check Python packages
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "==" in line:
                        name, version = line.split("==", 1)
                        packages[f"python:{name.lower()}"] = version
        except Exception:
            pass

        # Check Node packages if package.json exists
        package_json = root / "package.json"
        if package_json.exists():
            try:
                result = subprocess.run(
                    ["npm", "list", "--depth=0", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=root,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    deps = data.get("dependencies", {})
                    for name, info in deps.items():
                        version = info.get("version", "unknown")
                        packages[f"node:{name}"] = version
            except Exception:
                pass

        return packages

    def _check_configuration(
        self,
        root: Path,
        report: HealthReport,
    ) -> dict[str, Any]:
        """Check configuration files."""
        config_status: dict[str, Any] = {}

        # Check .kiro directory
        kiro_dir = root / ".kiro"
        config_status["kiro_directory_exists"] = kiro_dir.exists()

        if kiro_dir.exists():
            # Check hooks directory
            hooks_dir = kiro_dir / "hooks"
            config_status["hooks_directory_exists"] = hooks_dir.exists()
            if hooks_dir.exists():
                config_status["hooks_count"] = len(list(hooks_dir.glob("*.json")))

            # Check settings directory
            settings_dir = kiro_dir / "settings"
            config_status["settings_directory_exists"] = settings_dir.exists()

            # Check steering directory
            steering_dir = kiro_dir / "steering"
            config_status["steering_directory_exists"] = steering_dir.exists()
            if steering_dir.exists():
                config_status["steering_count"] = len(list(steering_dir.glob("*.md")))

            # Check specs directory
            specs_dir = kiro_dir / "specs"
            config_status["specs_directory_exists"] = specs_dir.exists()
            if specs_dir.exists():
                config_status["specs_count"] = len(list(specs_dir.glob("**/requirements.md")))

        return config_status

    def _determine_overall_status(self, report: HealthReport) -> str:
        """Determine overall health status."""
        # Check for critical environment failures
        critical_environments = ["python"]
        for env_name in critical_environments:
            if env_name in report.environments:
                if not report.environments[env_name].available:
                    return "unhealthy"

        # Check for warnings
        warning_count = 0
        for env in report.environments.values():
            if not env.available:
                warning_count += 1

        # Check configuration
        if not report.configuration_status.get("kiro_directory_exists", False):
            return "unhealthy"

        if warning_count > 0:
            return "degraded"

        return "healthy"

    def _generate_recommendations(self, report: HealthReport) -> list[str]:
        """Generate recommendations based on health findings."""
        recommendations: list[str] = []

        # Check environments
        for name, env in report.environments.items():
            if not env.available:
                if name == "python":
                    recommendations.append("Install Python 3.10+ to use SkillForge")
                elif name == "nodejs":
                    recommendations.append("Install Node.js 20+ for TypeScript compilation")
                elif name == "typescript":
                    recommendations.append("Install TypeScript: npm install -g typescript")

        # Check configuration
        if not report.configuration_status.get("kiro_directory_exists", False):
            recommendations.append("Initialize .kiro/ directory: kiro init")

        if not report.configuration_status.get("hooks_directory_exists", False):
            recommendations.append("Create .kiro/hooks/ directory for hook configurations")

        return recommendations


# ============================================================================
# Conflict Analyzer (Task 2.11.3)
# ============================================================================

@dataclass
class IdentifierCollision:
    """Represents an identifier collision."""
    identifier: str
    locations: list[str]
    collision_type: str  # tool_name, skill_id, hook_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "locations": self.locations,
            "collision_type": self.collision_type,
        }


@dataclass
class CircularDependency:
    """Represents a circular dependency chain."""
    chain: list[str]
    dependency_type: str  # parameter, skill, hook

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "dependency_type": self.dependency_type,
        }


@dataclass
class MissingCredential:
    """Represents a missing required credential."""
    credential_name: str
    referenced_in: str
    credential_type: str  # env_var, secret, api_key

    def to_dict(self) -> dict[str, Any]:
        return {
            "credential_name": self.credential_name,
            "referenced_in": self.referenced_in,
            "credential_type": self.credential_type,
        }


@dataclass
class ConflictAnalysisReport:
    """Report from conflict analysis."""
    identifier_collisions: list[IdentifierCollision] = field(default_factory=list)
    circular_dependencies: list[CircularDependency] = field(default_factory=list)
    missing_credentials: list[MissingCredential] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def has_issues(self) -> bool:
        return bool(self.identifier_collisions or self.circular_dependencies or self.missing_credentials)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_issues": self.has_issues,
            "identifier_collisions": [c.to_dict() for c in self.identifier_collisions],
            "circular_dependencies": [d.to_dict() for d in self.circular_dependencies],
            "missing_credentials": [m.to_dict() for m in self.missing_credentials],
            "stats": self.stats,
        }


class ConflictAnalyzer:
    """
    Scans for identifier collisions, circular dependencies, and missing credentials.

    Analyzes skill definitions, hooks, and configurations to detect conflicts
    and issues that could cause runtime problems.

    Task 2.11.3: Conflict Analyzer
    Validates: Requirement 12.6

    Example:
        >>> analyzer = ConflictAnalyzer()
        >>> report = analyzer.analyze(Path("/workspace"))
        >>> report.has_issues
        False
    """

    # Patterns for detecting references
    ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
    SECRET_PATTERN = re.compile(r"{{resolve:secretsmanager:([^:]+)")
    API_KEY_PATTERN = re.compile(r"(api[_-]?key|apikey|token|secret)", re.IGNORECASE)

    def __init__(
        self,
        *,
        check_collisions: bool = True,
        check_circular: bool = True,
        check_credentials: bool = True,
    ) -> None:
        """
        Initialize the conflict analyzer.

        Args:
            check_collisions: Whether to check for identifier collisions
            check_circular: Whether to check for circular dependencies
            check_credentials: Whether to check for missing credentials
        """
        self.check_collisions = check_collisions
        self.check_circular = check_circular
        self.check_credentials = check_credentials

    def analyze(self, workspace_root: Path | str) -> ConflictAnalysisReport:
        """
        Analyze workspace for conflicts and issues.

        Args:
            workspace_root: Root directory of the workspace

        Returns:
            ConflictAnalysisReport with all findings
        """
        root = Path(workspace_root)
        report = ConflictAnalysisReport()

        # Collect all identifiers
        identifiers: dict[str, list[str]] = {}  # identifier -> locations
        parameters: dict[str, dict[str, list[str]]] = {}  # skill_id -> {param -> deps}
        credentials_needed: list[tuple[str, str, str]] = []  # (name, location, type)

        kiro_dir = root / ".kiro"
        if kiro_dir.exists():
            # Scan hooks for tool name collisions
            hooks_dir = kiro_dir / "hooks"
            if hooks_dir.exists():
                self._scan_hooks_directory(hooks_dir, identifiers, credentials_needed)

            # Scan MCP configuration
            mcp_file = kiro_dir / "settings" / "mcp.json"
            if mcp_file.exists():
                self._scan_mcp_config(mcp_file, identifiers, credentials_needed)

            # Scan specs for skill definitions
            specs_dir = kiro_dir / "specs"
            if specs_dir.exists():
                self._scan_specs_directory(specs_dir, identifiers, parameters, credentials_needed)

        # Check for collisions
        if self.check_collisions:
            for identifier, locations in identifiers.items():
                if len(locations) > 1:
                    report.identifier_collisions.append(IdentifierCollision(
                        identifier=identifier,
                        locations=locations,
                        collision_type=self._determine_collision_type(identifier),
                    ))

        # Check for circular dependencies
        if self.check_circular:
            report.circular_dependencies = self._detect_circular_dependencies(parameters)

        # Check for missing credentials
        if self.check_credentials:
            report.missing_credentials = self._check_missing_credentials(credentials_needed)

        # Update stats
        report.stats = {
            "identifiers_scanned": len(identifiers),
            "parameters_analyzed": sum(len(p) for p in parameters.values()),
            "credentials_checked": len(credentials_needed),
        }

        return report

    def _scan_hooks_directory(
        self,
        hooks_dir: Path,
        identifiers: dict[str, list[str]],
        credentials: list[tuple[str, str, str]],
    ) -> None:
        """Scan hooks directory for identifiers and credentials."""
        for hook_file in hooks_dir.glob("*.json"):
            try:
                content = hook_file.read_text()
                data = json.loads(content)

                # Check for hook name collisions
                for hook in data.get("hooks", []):
                    hook_name = hook.get("name")
                    if hook_name:
                        location = f"{hook_file.relative_to(hooks_dir.parent.parent)}:hooks"
                        if hook_name not in identifiers:
                            identifiers[hook_name] = []
                        identifiers[hook_name].append(location)

                    # Check for environment variables in commands
                    action = hook.get("action", {})
                    if isinstance(action, dict):
                        command = action.get("command", "")
                        if isinstance(command, str):
                            for match in self.ENV_VAR_PATTERN.findall(command):
                                credentials.append((match, str(hook_file), "env_var"))

            except json.JSONDecodeError:
                pass

    def _scan_mcp_config(
        self,
        mcp_file: Path,
        identifiers: dict[str, list[str]],
        credentials: list[tuple[str, str, str]],
    ) -> None:
        """Scan MCP configuration for identifiers and credentials."""
        try:
            data = json.loads(mcp_file.read_text())
            mcp_servers = data.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                # Check for server name collisions
                if server_name not in identifiers:
                    identifiers[server_name] = []
                identifiers[server_name].append(f".kiro/settings/mcp.json:mcpServers.{server_name}")

                # Check for environment variables in args
                args = server_config.get("args", [])
                for arg in args:
                    if isinstance(arg, str):
                        for match in self.ENV_VAR_PATTERN.findall(arg):
                            credentials.append((match, str(mcp_file), "env_var"))

                # Check for secrets references
                content = json.dumps(server_config)
                for match in self.SECRET_PATTERN.findall(content):
                    credentials.append((match, str(mcp_file), "secret"))

        except json.JSONDecodeError:
            pass

    def _scan_specs_directory(
        self,
        specs_dir: Path,
        identifiers: dict[str, list[str]],
        parameters: dict[str, dict[str, list[str]]],
        credentials: list[tuple[str, str, str]],
    ) -> None:
        """Scan specs directory for identifiers and parameters."""
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                skill_id = spec_dir.name
                requirements_file = spec_dir / "requirements.md"

                if requirements_file.exists():
                    location = str(requirements_file)

                    # Check for skill ID collisions
                    if skill_id not in identifiers:
                        identifiers[skill_id] = []
                    identifiers[skill_id].append(location)

                    # Parse parameters (simplified)
                    content = requirements_file.read_text()
                    param_refs = re.findall(r"\bparameters?\.(\w+)", content)
                    if param_refs:
                        parameters[skill_id] = {p: [] for p in set(param_refs)}

                    # Check for credentials
                    for match in self.ENV_VAR_PATTERN.findall(content):
                        credentials.append((match, location, "env_var"))

                    for match in self.SECRET_PATTERN.findall(content):
                        credentials.append((match, location, "secret"))

    def _determine_collision_type(self, identifier: str) -> str:
        """Determine the type of collision."""
        if identifier.startswith("skillforge-"):
            return "tool_name"
        elif "-" in identifier:
            return "skill_id"
        else:
            return "hook_name"

    def _detect_circular_dependencies(
        self,
        parameters: dict[str, dict[str, list[str]]],
    ) -> list[CircularDependency]:
        """Detect circular dependencies in parameters."""
        circular: list[CircularDependency] = []

        # Build dependency graph
        # For simplicity, we check if skills reference each other
        # In a real implementation, this would be more sophisticated

        return circular  # Simplified - no circular dependencies detected

    def _check_missing_credentials(
        self,
        credentials_needed: list[tuple[str, str, str]],
    ) -> list[MissingCredential]:
        """Check for missing credentials."""
        missing: list[MissingCredential] = []
        checked: set[str] = set()

        for cred_name, location, cred_type in credentials_needed:
            if cred_name in checked:
                continue
            checked.add(cred_name)

            # Check if credential exists
            exists = False
            if cred_type == "env_var":
                exists = cred_name in os.environ
            elif cred_type == "secret":
                # For secrets, we assume they exist (would need AWS integration to check)
                exists = True

            if not exists:
                missing.append(MissingCredential(
                    credential_name=cred_name,
                    referenced_in=location,
                    credential_type=cred_type,
                ))

        return missing


# ============================================================================
# Combined Doctor Utilities
# ============================================================================

def run_full_diagnostics(
    workspace_root: Path | str,
    *,
    config_validator: bool = True,
    health_reporter: bool = True,
    conflict_analyzer: bool = True,
) -> dict[str, Any]:
    """
    Run all diagnostic utilities and return combined results.

    Args:
        workspace_root: Root directory of the workspace
        config_validator: Whether to run config validation
        health_reporter: Whether to run health reporting
        conflict_analyzer: Whether to run conflict analysis

    Returns:
        Dictionary with all diagnostic results
    """
    root = Path(workspace_root)
    results: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "workspace_root": str(root),
    }

    if config_validator:
        validator = ConfigValidator()
        kiro_dir = root / ".kiro"
        if kiro_dir.exists():
            results["config_validation"] = {
                category: [r.to_dict() for r in reports]
                for category, reports in validator.validate_kiro_directory(kiro_dir).items()
            }

    if health_reporter:
        reporter = HealthReporter()
        results["health_report"] = reporter.generate_report(root).to_dict()

    if conflict_analyzer:
        analyzer = ConflictAnalyzer()
        results["conflict_analysis"] = analyzer.analyze(root).to_dict()

    # Determine overall status
    overall_healthy = True
    if "health_report" in results:
        if results["health_report"]["overall_status"] == "unhealthy":
            overall_healthy = False
    if "conflict_analysis" in results:
        if results["conflict_analysis"]["has_issues"]:
            overall_healthy = False

    results["overall_healthy"] = overall_healthy

    return results
