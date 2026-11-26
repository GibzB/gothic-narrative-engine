"""
Performance & Correctness Diagnostics for Skills.

Analyzes skill execution timing metrics, code quality, and historical test
results to identify performance issues, potential correctness issues, and
recurring failure patterns.

Implements Task 2.6: Diagnostics Phase
- Task 2.6.1: Performance Analyzer
- Task 2.6.2: Code Analyzer
- Task 2.6.3: Historical Analyzer
"""

from __future__ import annotations

import ast
import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================================
# Performance Analyzer (Task 2.6.1)
# ============================================================================

@dataclass
class PerformanceIssue:
    """A detected performance issue."""

    skill_name: str
    metric_name: str
    value: float
    threshold: float
    severity: str  # critical, warning, info
    message: str
    suggestion: str | None = None


@dataclass
class PerformanceReport:
    """Report of performance analysis results."""

    skill_name: str
    analyzed_at: str
    total_metrics: int
    issues: list[PerformanceIssue] = field(default_factory=list)
    summary: str = ""
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skillName": self.skill_name,
            "analyzedAt": self.analyzed_at,
            "totalMetrics": self.total_metrics,
            "issueCount": self.issue_count,
            "hasCriticalIssues": self.has_critical_issues,
            "issues": [
                {
                    "skillName": i.skill_name,
                    "metricName": i.metric_name,
                    "value": i.value,
                    "threshold": i.threshold,
                    "severity": i.severity,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "summary": self.summary,
            "metrics": self.metrics,
        }


# Default performance thresholds (in milliseconds)
DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
    # metric_name: (warning_threshold, critical_threshold)
    "execution_time_ms": (1000.0, 5000.0),
    "p99_latency_ms": (2000.0, 10000.0),
    "p95_latency_ms": (1500.0, 7500.0),
    "p50_latency_ms": (500.0, 2500.0),
    "memory_peak_mb": (256.0, 1024.0),
    "cpu_time_ms": (800.0, 4000.0),
    "io_operations": (1000.0, 5000.0),
}


class PerformanceAnalyzer:
    """
    Analyzes skill execution timing metrics.

    Flags performance issues exceeding configured thresholds and generates
    performance reports with remediation suggestions.

    Example:
        >>> analyzer = PerformanceAnalyzer()
        >>> metrics = {"execution_time_ms": 1500.0, "memory_peak_mb": 128.0}
        >>> report = analyzer.analyze("my-skill", metrics)
        >>> report.has_critical_issues
        False
    """

    def __init__(
        self,
        *,
        thresholds: dict[str, tuple[float, float]] | None = None,
        custom_thresholds: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """
        Initialize the performance analyzer.

        Args:
            thresholds: Override default thresholds entirely
            custom_thresholds: Additional thresholds to merge with defaults
        """
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        if custom_thresholds:
            self.thresholds.update(custom_thresholds)

    def analyze(
        self,
        skill_name: str,
        metrics: dict[str, float],
    ) -> PerformanceReport:
        """
        Analyze performance metrics for a skill.

        Args:
            skill_name: Name of the skill being analyzed
            metrics: Dictionary of metric names to values

        Returns:
            PerformanceReport with analysis results
        """
        issues: list[PerformanceIssue] = []

        for metric_name, value in metrics.items():
            issue = self._check_metric(skill_name, metric_name, value)
            if issue:
                issues.append(issue)

        report = PerformanceReport(
            skill_name=skill_name,
            analyzed_at=datetime.utcnow().isoformat(),
            total_metrics=len(metrics),
            issues=issues,
            metrics=metrics,
        )

        report.summary = self._generate_summary(report)
        return report

    def analyze_batch(
        self,
        skills_metrics: dict[str, dict[str, float]],
    ) -> list[PerformanceReport]:
        """
        Analyze performance metrics for multiple skills.

        Args:
            skills_metrics: Dictionary mapping skill names to their metrics

        Returns:
            List of PerformanceReports for each skill
        """
        return [
            self.analyze(skill_name, metrics)
            for skill_name, metrics in skills_metrics.items()
        ]

    def get_threshold(self, metric_name: str) -> tuple[float, float] | None:
        """
        Get the warning and critical thresholds for a metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Tuple of (warning_threshold, critical_threshold) or None
        """
        return self.thresholds.get(metric_name)

    def set_threshold(
        self,
        metric_name: str,
        warning_threshold: float,
        critical_threshold: float,
    ) -> None:
        """
        Set a threshold for a metric.

        Args:
            metric_name: Name of the metric
            warning_threshold: Threshold for warning severity
            critical_threshold: Threshold for critical severity
        """
        self.thresholds[metric_name] = (warning_threshold, critical_threshold)

    def _check_metric(
        self,
        skill_name: str,
        metric_name: str,
        value: float,
    ) -> PerformanceIssue | None:
        """Check a single metric against thresholds."""
        thresholds = self.thresholds.get(metric_name)

        if thresholds is None:
            # No threshold defined for this metric
            return None

        warning_threshold, critical_threshold = thresholds

        if value >= critical_threshold:
            return PerformanceIssue(
                skill_name=skill_name,
                metric_name=metric_name,
                value=value,
                threshold=critical_threshold,
                severity="critical",
                message=f"{metric_name} ({value:.2f}) exceeds critical threshold ({critical_threshold})",
                suggestion=self._get_suggestion(metric_name, "critical"),
            )
        elif value >= warning_threshold:
            return PerformanceIssue(
                skill_name=skill_name,
                metric_name=metric_name,
                value=value,
                threshold=warning_threshold,
                severity="warning",
                message=f"{metric_name} ({value:.2f}) exceeds warning threshold ({warning_threshold})",
                suggestion=self._get_suggestion(metric_name, "warning"),
            )

        return None

    def _get_suggestion(self, metric_name: str, severity: str) -> str:
        """Get remediation suggestion for a metric issue."""
        suggestions: dict[str, dict[str, str]] = {
            "execution_time_ms": {
                "warning": "Consider optimizing algorithm complexity or caching results.",
                "critical": "Immediate optimization required. Profile to identify bottlenecks.",
            },
            "p99_latency_ms": {
                "warning": "Review tail latency causes. Consider async processing.",
                "critical": "Critical tail latency. May need architecture changes.",
            },
            "memory_peak_mb": {
                "warning": "Review memory allocation patterns. Consider streaming.",
                "critical": "Memory usage critical. Risk of OOM errors.",
            },
            "cpu_time_ms": {
                "warning": "CPU usage elevated. Consider algorithm optimization.",
                "critical": "CPU saturation. May impact system responsiveness.",
            },
            "io_operations": {
                "warning": "High I/O count. Consider batching operations.",
                "critical": "Excessive I/O. May cause system slowdown.",
            },
        }

        return suggestions.get(metric_name, {}).get(
            severity, "Review and optimize this metric."
        )

    def _generate_summary(self, report: PerformanceReport) -> str:
        """Generate a human-readable summary."""
        if not report.issues:
            return f"No performance issues detected for {report.skill_name}"

        critical_count = sum(1 for i in report.issues if i.severity == "critical")
        warning_count = sum(1 for i in report.issues if i.severity == "warning")

        parts: list[str] = []
        if critical_count > 0:
            parts.append(f"{critical_count} critical")
        if warning_count > 0:
            parts.append(f"{warning_count} warning")

        return f"Found {', '.join(parts)} performance issue(s) in {report.skill_name}"


# ============================================================================
# Code Analyzer (Task 2.6.2)
# ============================================================================

@dataclass
class CodeIssue:
    """A detected code quality or security issue."""

    code: str
    severity: str  # error, warning, info
    message: str
    location: str
    line: int | None = None
    suggestion: str | None = None


@dataclass
class CodeAnalysisReport:
    """Report of code analysis results."""

    skill_name: str
    analyzed_at: str
    file_path: str
    issues: list[CodeIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_security_issues(self) -> bool:
        security_codes = {
            "HARD_CODED_SECRET",
            "SQL_INJECTION_RISK",
            "COMMAND_INJECTION_RISK",
            "PATH_TRAVERSAL_RISK",
            "UNSAFE_DESERIALIZE",
        }
        return any(i.code in security_codes for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "skillName": self.skill_name,
            "analyzedAt": self.analyzed_at,
            "filePath": self.file_path,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "hasSecurityIssues": self.has_security_issues,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "location": i.location,
                    "line": i.line,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "stats": self.stats,
        }


# Anti-pattern patterns for static analysis
ANTIPATTERN_RULES: list[dict[str, Any]] = [
    {
        "code": "HARD_CODED_SECRET",
        "pattern": r"(?i)(password|api_key|secret|token)\s*=\s*['\"][^'\"]+['\"]",
        "severity": "error",
        "message": "Hard-coded secret detected",
        "suggestion": "Use environment variables or secure secret storage",
    },
    {
        "code": "SQL_INJECTION_RISK",
        "pattern": r"execute\s*\(\s*['\"]SELECT.*\+|f['\"]SELECT.*\{",
        "severity": "error",
        "message": "Potential SQL injection vulnerability",
        "suggestion": "Use parameterized queries",
    },
    {
        "code": "COMMAND_INJECTION_RISK",
        "pattern": r"subprocess\..*\(\s*['\"].*\+|os\.system\s*\(",
        "severity": "error",
        "message": "Potential command injection vulnerability",
        "suggestion": "Use subprocess with shell=False and argument list",
    },
    {
        "code": "PATH_TRAVERSAL_RISK",
        "pattern": r"open\s*\(\s*[^'\"]*\+|Path\s*\(\s*[^'\"]*\+",
        "severity": "warning",
        "message": "Potential path traversal vulnerability",
        "suggestion": "Validate and sanitize file paths",
    },
    {
        "code": "UNSAFE_DESERIALIZE",
        "pattern": r"pickle\.loads?\s*\(|yaml\.load\s*\([^)]*\)(?!.*Loader)",
        "severity": "error",
        "message": "Unsafe deserialization",
        "suggestion": "Use json or yaml.safe_load",
    },
    {
        "code": "BARE_EXCEPT",
        "pattern": r"except\s*:",
        "severity": "warning",
        "message": "Bare except clause catches all exceptions",
        "suggestion": "Catch specific exceptions",
    },
    {
        "code": "PRINT_IN_PRODUCTION",
        "pattern": r"print\s*\(",
        "severity": "info",
        "message": "Print statement found",
        "suggestion": "Consider using logging module",
    },
    {
        "code": "TODO_UNRESOLVED",
        "pattern": r"#\s*TODO|#\s*FIXME|#\s*XXX",
        "severity": "info",
        "message": "Unresolved TODO comment",
        "suggestion": "Resolve or track in issue tracker",
    },
]


class CodeAnalyzer:
    """
    Identifies potential correctness issues via static analysis.

    Checks for common anti-patterns and security vulnerabilities using
    pattern matching and AST analysis.

    Example:
        >>> analyzer = CodeAnalyzer()
        >>> report = analyzer.analyze_code("my-skill", code_content, "skill.py")
        >>> report.has_security_issues
        False
    """

    def __init__(
        self,
        *,
        custom_rules: list[dict[str, Any]] | None = None,
        exclude_rules: set[str] | None = None,
    ) -> None:
        """
        Initialize the code analyzer.

        Args:
            custom_rules: Additional rules to check
            exclude_rules: Rule codes to exclude from analysis
        """
        self.rules = ANTIPATTERN_RULES.copy()
        if custom_rules:
            self.rules.extend(custom_rules)

        self.exclude_rules = exclude_rules or set()

    def analyze_code(
        self,
        skill_name: str,
        code: str,
        file_path: str = "<inline>",
    ) -> CodeAnalysisReport:
        """
        Analyze code for correctness issues.

        Args:
            skill_name: Name of the skill being analyzed
            code: Source code to analyze
            file_path: Path to the file (for location reporting)

        Returns:
            CodeAnalysisReport with analysis results
        """
        issues: list[CodeIssue] = []

        # Run pattern-based analysis
        issues.extend(self._pattern_analysis(code, file_path))

        # Run AST-based analysis
        issues.extend(self._ast_analysis(code, file_path))

        # Collect stats
        stats = self._collect_stats(code)

        return CodeAnalysisReport(
            skill_name=skill_name,
            analyzed_at=datetime.utcnow().isoformat(),
            file_path=file_path,
            issues=issues,
            stats=stats,
        )

    def analyze_file(
        self,
        skill_name: str,
        file_path: Path | str,
    ) -> CodeAnalysisReport:
        """
        Analyze a file for correctness issues.

        Args:
            skill_name: Name of the skill being analyzed
            file_path: Path to the file to analyze

        Returns:
            CodeAnalysisReport with analysis results
        """
        path = Path(file_path)

        if not path.exists():
            return CodeAnalysisReport(
                skill_name=skill_name,
                analyzed_at=datetime.utcnow().isoformat(),
                file_path=str(file_path),
                issues=[CodeIssue(
                    code="FILE_NOT_FOUND",
                    severity="error",
                    message=f"File not found: {file_path}",
                    location=str(file_path),
                )],
            )

        try:
            code = path.read_text(encoding="utf-8")
        except Exception as e:
            return CodeAnalysisReport(
                skill_name=skill_name,
                analyzed_at=datetime.utcnow().isoformat(),
                file_path=str(file_path),
                issues=[CodeIssue(
                    code="FILE_READ_ERROR",
                    severity="error",
                    message=f"Error reading file: {e}",
                    location=str(file_path),
                )],
            )

        return self.analyze_code(skill_name, code, str(file_path))

    def _pattern_analysis(self, code: str, file_path: str) -> list[CodeIssue]:
        """Run pattern-based analysis."""
        issues: list[CodeIssue] = []
        lines = code.split("\n")

        for rule in self.rules:
            code_id = rule.get("code", "")
            if code_id in self.exclude_rules:
                continue

            pattern = rule.get("pattern", "")
            if not pattern:
                continue

            try:
                regex = re.compile(pattern)
            except re.error:
                continue

            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    issues.append(CodeIssue(
                        code=code_id,
                        severity=rule.get("severity", "warning"),
                        message=rule.get("message", "Issue detected"),
                        location=f"{file_path}:{line_num}",
                        line=line_num,
                        suggestion=rule.get("suggestion"),
                    ))

        return issues

    def _ast_analysis(self, code: str, file_path: str) -> list[CodeIssue]:
        """Run AST-based analysis for deeper code inspection."""
        issues: list[CodeIssue] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(CodeIssue(
                code="SYNTAX_ERROR",
                severity="error",
                message=f"Syntax error: {e.msg}",
                location=f"{file_path}:{e.lineno}",
                line=e.lineno,
            ))
            return issues

        # Check for various AST patterns
        for node in ast.walk(tree):
            # Check for eval() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "eval":
                    issues.append(CodeIssue(
                        code="EVAL_USAGE",
                        severity="warning",
                        message="eval() usage is dangerous",
                        location=file_path,
                        line=node.lineno,
                        suggestion="Avoid eval() in production code",
                    ))

            # Check for exec() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "exec":
                    issues.append(CodeIssue(
                        code="EXEC_USAGE",
                        severity="warning",
                        message="exec() usage is dangerous",
                        location=file_path,
                        line=node.lineno,
                        suggestion="Avoid exec() in production code",
                    ))

            # Check for missing docstrings in functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    issues.append(CodeIssue(
                        code="MISSING_DOCSTRING",
                        severity="info",
                        message=f"Function '{node.name}' missing docstring",
                        location=f"{file_path}:{node.lineno}",
                        line=node.lineno,
                        suggestion="Add docstring for documentation",
                    ))

        return issues

    def _collect_stats(self, code: str) -> dict[str, Any]:
        """Collect code statistics."""
        # Handle empty code case
        if not code:
            return {
                "line_count": 0,
                "non_empty_lines": 0,
                "function_count": 0,
                "class_count": 0,
                "import_count": 0,
            }

        lines = code.split("\n")

        try:
            tree = ast.parse(code)
            function_count = sum(
                1 for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            class_count = sum(
                1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            )
            import_count = sum(
                1 for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            )
        except SyntaxError:
            function_count = 0
            class_count = 0
            import_count = 0

        return {
            "line_count": len(lines),
            "non_empty_lines": sum(1 for line in lines if line.strip()),
            "function_count": function_count,
            "class_count": class_count,
            "import_count": import_count,
        }

    def add_rule(
        self,
        code: str,
        pattern: str,
        severity: str = "warning",
        message: str = "",
        suggestion: str | None = None,
    ) -> None:
        """
        Add a custom rule to the analyzer.

        Args:
            code: Unique rule code
            pattern: Regex pattern to match
            severity: Issue severity (error, warning, info)
            message: Description of the issue
            suggestion: Remediation suggestion
        """
        self.rules.append({
            "code": code,
            "pattern": pattern,
            "severity": severity,
            "message": message,
            "suggestion": suggestion,
        })


# ============================================================================
# Historical Analyzer (Task 2.6.3)
# ============================================================================

@dataclass
class FailurePattern:
    """A detected failure pattern."""

    skill_name: str
    pattern_type: str  # recurring, correlated, trending
    description: str
    occurrences: int
    first_seen: str
    last_seen: str
    affected_tests: list[str] = field(default_factory=list)
    suggested_action: str | None = None


@dataclass
class HistoricalReport:
    """Report of historical analysis results."""

    analyzed_at: str
    skills_analyzed: int
    total_test_runs: int
    patterns: list[FailurePattern] = field(default_factory=list)
    skills_with_issues: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def has_recurring_issues(self) -> bool:
        return any(p.pattern_type == "recurring" for p in self.patterns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzedAt": self.analyzed_at,
            "skillsAnalyzed": self.skills_analyzed,
            "totalTestRuns": self.total_test_runs,
            "patternCount": len(self.patterns),
            "hasRecurringIssues": self.has_recurring_issues,
            "skillsWithIssues": self.skills_with_issues,
            "patterns": [
                {
                    "skillName": p.skill_name,
                    "patternType": p.pattern_type,
                    "description": p.description,
                    "occurrences": p.occurrences,
                    "firstSeen": p.first_seen,
                    "lastSeen": p.last_seen,
                    "affectedTests": p.affected_tests,
                    "suggestedAction": p.suggested_action,
                }
                for p in self.patterns
            ],
            "summary": self.summary,
        }


@dataclass
class RunRecord:
    """
    Record of a single test run.
    """

    skill_name: str
    test_id: str
    timestamp: str
    passed: bool
    duration_ms: float
    error_message: str | None = None


# Backward compatibility alias
TestRunRecord = RunRecord


class HistoricalAnalyzer:
    """
    Analyzes historical test results for failure patterns.

    Identifies skills with recurring issues and correlates failures
    across multiple test runs.

    Example:
        >>> analyzer = HistoricalAnalyzer()
        >>> analyzer.record_test_run("skill-1", "test-1", False)
        >>> report = analyzer.analyze()
        >>> report.has_recurring_issues
        True
    """

    def __init__(
        self,
        *,
        history_path: Path | str | None = None,
        max_history: int = 10000,
        recurrence_threshold: int = 3,
    ) -> None:
        """
        Initialize the historical analyzer.

        Args:
            history_path: Optional path to persist history
            max_history: Maximum records to keep in memory
            recurrence_threshold: Minimum failures to flag as recurring
        """
        self.history_path = Path(history_path) if history_path else None
        self.max_history = max_history
        self.recurrence_threshold = recurrence_threshold
        self._history: list[TestRunRecord] = []

    def record_test_run(
        self,
        skill_name: str,
        test_id: str,
        passed: bool,
        *,
        duration_ms: float = 0.0,
        error_message: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """
        Record a test run result.

        Args:
            skill_name: Name of the skill tested
            test_id: Identifier for the test
            passed: Whether the test passed
            duration_ms: Test execution duration
            error_message: Error message if test failed
            timestamp: Optional timestamp (defaults to now)
        """
        record = TestRunRecord(
            skill_name=skill_name,
            test_id=test_id,
            timestamp=timestamp or datetime.utcnow().isoformat(),
            passed=passed,
            duration_ms=duration_ms,
            error_message=error_message,
        )

        self._history.append(record)
        self._enforce_limit()

    def load_history(self, path: Path | str | None = None) -> bool:
        """
        Load history from a JSON file.

        Args:
            path: Override path for loading

        Returns:
            True if load succeeded, False otherwise
        """
        target_path = Path(path) if path else self.history_path

        if target_path is None or not target_path.exists():
            return False

        try:
            data = json.loads(target_path.read_text())
            records = data.get("records", [])

            self._history = []
            for r in records:
                self._history.append(TestRunRecord(
                    skill_name=r.get("skill_name", ""),
                    test_id=r.get("test_id", ""),
                    timestamp=r.get("timestamp", ""),
                    passed=r.get("passed", False),
                    duration_ms=r.get("duration_ms", 0.0),
                    error_message=r.get("error_message"),
                ))

            return True
        except Exception:
            return False

    def save_history(self, path: Path | str | None = None) -> bool:
        """
        Save history to a JSON file.

        Args:
            path: Override path for saving

        Returns:
            True if save succeeded, False otherwise
        """
        target_path = Path(path) if path else self.history_path

        if target_path is None:
            return False

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "record_count": len(self._history),
                "records": [
                    {
                        "skill_name": r.skill_name,
                        "test_id": r.test_id,
                        "timestamp": r.timestamp,
                        "passed": r.passed,
                        "duration_ms": r.duration_ms,
                        "error_message": r.error_message,
                    }
                    for r in self._history
                ],
            }
            target_path.write_text(json.dumps(data, indent=2))
            return True
        except Exception:
            return False

    def analyze(self) -> HistoricalReport:
        """
        Analyze historical test results for failure patterns.

        Returns:
            HistoricalReport with detected patterns
        """
        patterns: list[FailurePattern] = []
        skills_with_issues: list[str] = []

        # Group records by skill
        skill_failures: dict[str, list[TestRunRecord]] = {}
        for record in self._history:
            if not record.passed:
                if record.skill_name not in skill_failures:
                    skill_failures[record.skill_name] = []
                skill_failures[record.skill_name].append(record)

        # Identify recurring patterns
        for skill_name, failures in skill_failures.items():
            if len(failures) >= self.recurrence_threshold:
                # Find affected tests
                affected_tests = list(set(f.test_id for f in failures))
                first_seen = min(f.timestamp for f in failures)
                last_seen = max(f.timestamp for f in failures)

                patterns.append(FailurePattern(
                    skill_name=skill_name,
                    pattern_type="recurring",
                    description=f"Skill has {len(failures)} recurring failures",
                    occurrences=len(failures),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    affected_tests=affected_tests,
                    suggested_action="Review skill implementation for stability issues",
                ))
                skills_with_issues.append(skill_name)

        # Identify correlated failures
        correlated = self._find_correlated_failures()
        for skill1, skill2, count in correlated:
            patterns.append(FailurePattern(
                skill_name=f"{skill1} + {skill2}",
                pattern_type="correlated",
                description=f"Failures in {skill1} correlate with {skill2}",
                occurrences=count,
                first_seen="",
                last_seen="",
                suggested_action="Investigate shared dependencies or common causes",
            ))

        # Identify trending failures
        trending = self._find_trending_failures()
        for skill_name, trend_count in trending.items():
            patterns.append(FailurePattern(
                skill_name=skill_name,
                pattern_type="trending",
                description=f"Failure rate increasing for {skill_name}",
                occurrences=trend_count,
                first_seen="",
                last_seen="",
                suggested_action="Review recent changes to skill or dependencies",
            ))

        report = HistoricalReport(
            analyzed_at=datetime.utcnow().isoformat(),
            skills_analyzed=len(set(r.skill_name for r in self._history)),
            total_test_runs=len(self._history),
            patterns=patterns,
            skills_with_issues=list(set(skills_with_issues)),
        )
        report.summary = self._generate_summary(report)

        return report

    def get_skill_history(self, skill_name: str) -> list[TestRunRecord]:
        """
        Get all test run records for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of TestRunRecords for the skill
        """
        return [r for r in self._history if r.skill_name == skill_name]

    def get_failure_rate(self, skill_name: str) -> float:
        """
        Calculate the failure rate for a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Failure rate as a percentage (0-100)
        """
        skill_records = [r for r in self._history if r.skill_name == skill_name]
        if not skill_records:
            return 0.0

        failures = sum(1 for r in skill_records if not r.passed)
        return (failures / len(skill_records)) * 100

    def clear_history(self) -> None:
        """Clear all stored history."""
        self._history = []

    def _enforce_limit(self) -> None:
        """Enforce maximum history limit."""
        if len(self._history) > self.max_history:
            excess = len(self._history) - self.max_history
            self._history = self._history[excess:]

    def _find_correlated_failures(self) -> list[tuple[str, str, int]]:
        """Find skills that tend to fail together."""
        # Group failures by timestamp (within same minute)
        from collections import defaultdict

        time_groups: dict[str, set[str]] = defaultdict(set)

        for record in self._history:
            if not record.passed:
                # Truncate timestamp to minute
                time_key = record.timestamp[:16] if len(record.timestamp) >= 16 else record.timestamp
                time_groups[time_key].add(record.skill_name)

        # Count co-occurrences
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        for skills in time_groups.values():
            skill_list = sorted(skills)
            for i, s1 in enumerate(skill_list):
                for s2 in skill_list[i + 1:]:
                    pair_counts[(s1, s2)] += 1

        # Return pairs with multiple co-occurrences
        return [
            (s1, s2, count)
            for (s1, s2), count in pair_counts.items()
            if count >= 2
        ]

    def _find_trending_failures(self) -> dict[str, int]:
        """Find skills with increasing failure rates."""
        # Simple approach: count failures in recent vs older history
        if len(self._history) < 10:
            return {}

        midpoint = len(self._history) // 2
        older = self._history[:midpoint]
        recent = self._history[midpoint:]

        trending: dict[str, int] = {}

        # Calculate failure counts
        older_failures: dict[str, int] = {}
        for r in older:
            if not r.passed:
                older_failures[r.skill_name] = older_failures.get(r.skill_name, 0) + 1

        recent_failures: dict[str, int] = {}
        for r in recent:
            if not r.passed:
                recent_failures[r.skill_name] = recent_failures.get(r.skill_name, 0) + 1

        # Find skills with increasing failure count
        for skill_name, recent_count in recent_failures.items():
            older_count = older_failures.get(skill_name, 0)
            if recent_count > older_count * 2:  # More than doubled
                trending[skill_name] = recent_count

        return trending

    def _generate_summary(self, report: HistoricalReport) -> str:
        """Generate a human-readable summary."""
        if not report.patterns:
            return f"Analyzed {report.total_test_runs} test runs across {report.skills_analyzed} skills with no significant patterns detected"

        recurring_count = sum(1 for p in report.patterns if p.pattern_type == "recurring")
        correlated_count = sum(1 for p in report.patterns if p.pattern_type == "correlated")
        trending_count = sum(1 for p in report.patterns if p.pattern_type == "trending")

        parts: list[str] = []
        if recurring_count > 0:
            parts.append(f"{recurring_count} recurring")
        if correlated_count > 0:
            parts.append(f"{correlated_count} correlated")
        if trending_count > 0:
            parts.append(f"{trending_count} trending")

        return f"Found {', '.join(parts)} failure pattern(s) across {len(report.skills_with_issues)} skill(s)"
