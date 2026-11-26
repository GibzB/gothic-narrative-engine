"""
Regression & Hypothesis PBT Runner for Skills.

Runs property-based tests using Hypothesis to validate skill parameter schemas
against randomized boundary inputs. Ensures skills handle edge cases correctly.

Adapted from tripleyak/SkillForge run_skill_evals.py patterns.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase
from hypothesis.stateful import RuleBasedStateMachine

from skillforge.frontmatter import parse_frontmatter_file, FrontmatterResult


@dataclass
class EvalResult:
    """Result of running an evaluation."""

    passed: bool = True
    property_name: str = ""
    test_count: int = 0
    failure_count: int = 0
    errors: list[str] = field(default_factory=list)
    failing_examples: list[dict[str, Any]] = field(default_factory=list)
    performance_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.test_count == 0:
            return 1.0
        return 1.0 - (self.failure_count / self.test_count)


@dataclass
class RegressionSuite:
    """A suite of regression tests for a skill."""

    skill_name: str
    skill_path: Path
    baseline_results: dict[str, Any] = field(default_factory=dict)
    current_results: dict[str, Any] = field(default_factory=dict)

    def compare(self) -> list[str]:
        """Compare current vs baseline results."""
        regressions: list[str] = []
        for key in self.baseline_results:
            if key not in self.current_results:
                regressions.append(f"Missing result: {key}")
            elif self.current_results[key] != self.baseline_results[key]:
                regressions.append(f"Regression in {key}: expected {self.baseline_results[key]}, got {self.current_results[key]}")
        return regressions


class PBTRunner:
    """
    Runs property-based tests against skill parameter schemas.

    Uses Hypothesis to generate randomized boundary inputs and test
    that skills handle them correctly without crashing or producing
    invalid outputs.

    Example:
        >>> runner = PBTRunner()
        >>> result = runner.run_schema_tests({"type": "object", "properties": {"count": {"type": "integer"}}})
        >>> result.passed
        True
    """

    def __init__(
        self,
        *,
        max_examples: int = 50,
        timeout_seconds: int = 30,
    ) -> None:
        """
        Initialize the PBT runner.

        Args:
            max_examples: Maximum number of test examples per property
            timeout_seconds: Timeout for each test run
        """
        self.max_examples = max_examples
        self.timeout_seconds = timeout_seconds
        self.results: list[EvalResult] = []

    def run_schema_tests(
        self,
        schema: dict[str, Any],
        *,
        validator: Callable[[dict[str, Any]], bool] | None = None,
    ) -> EvalResult:
        """
        Run property-based tests against a JSON Schema.

        Args:
            schema: Draft-07 JSON Schema to test
            validator: Optional custom validator function

        Returns:
            EvalResult with test outcomes
        """
        result = EvalResult(property_name="schema_validation")
        result.test_count = self.max_examples

        try:
            # Generate strategy from schema
            strategy = self._schema_to_strategy(schema)

            @given(data=strategy)
            @settings(max_examples=self.max_examples, database=InMemoryExampleDatabase())
            def test_schema(data: dict[str, Any]) -> None:
                if validator:
                    assert validator(data), f"Custom validator failed for {data}"

            test_schema()

        except Exception as e:
            result.passed = False
            result.failure_count = 1
            result.errors.append(f"PBT failed: {e}")
            result.failing_examples.append({
                "exception": str(e),
                "traceback": traceback.format_exc(),
            })

        self.results.append(result)
        return result

    def run_skill_tests(
        self,
        skill_path: Path | str,
        *,
        test_handler: Callable[[dict[str, Any]], Any] | None = None,
    ) -> list[EvalResult]:
        """
        Run all property tests for a skill.

        Args:
            skill_path: Path to SKILL.md file
            test_handler: Optional handler function to test

        Returns:
            List of EvalResults for each property tested
        """
        path = Path(skill_path)
        fm = parse_frontmatter_file(path)

        if not fm.is_valid:
            return [EvalResult(
                passed=False,
                property_name="parse",
                errors=[f"Failed to parse skill: {e}" for e in fm.errors],
            )]

        results: list[EvalResult] = []

        # Test parameter schema
        params = fm.parameters
        if params:
            schema_result = self.run_schema_tests(params)
            schema_result.property_name = f"{fm.name}.parameters"
            results.append(schema_result)

        # Test triggers are valid strings
        triggers = fm.triggers
        if triggers:
            trigger_result = self._test_triggers(triggers, fm.name or "unknown")
            results.append(trigger_result)

        # Run custom handler tests if provided
        if test_handler:
            handler_result = self._test_handler(test_handler, fm)
            results.append(handler_result)

        return results

    def _schema_to_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[Any]:
        """Convert a JSON Schema to a Hypothesis strategy."""
        schema_type = schema.get("type", "object")

        if schema_type == "string":
            return self._string_strategy(schema)
        elif schema_type == "integer":
            return self._integer_strategy(schema)
        elif schema_type == "number":
            return self._number_strategy(schema)
        elif schema_type == "boolean":
            return st.booleans()
        elif schema_type == "array":
            return self._array_strategy(schema)
        elif schema_type == "object":
            return self._object_strategy(schema)
        else:
            return st.none()

    def _string_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[str]:
        """Create string strategy from schema."""
        min_len = schema.get("minLength", 0)
        max_len = schema.get("maxLength", 100)
        pattern = schema.get("pattern")
        format_type = schema.get("format")

        if format_type == "email":
            return st.emails()  # type: ignore
        elif format_type == "uri":
            return st.urls()  # type: ignore
        elif pattern:
            return st.from_regex(pattern)
        else:
            return st.text(min_size=min_len, max_size=max_len)

    def _integer_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[int]:
        """Create integer strategy from schema."""
        min_val = schema.get("minimum", -(2**31))
        max_val = schema.get("maximum", 2**31 - 1)
        return st.integers(min_value=min_val, max_value=max_val)

    def _number_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[float]:
        """Create number strategy from schema."""
        min_val = schema.get("minimum", -1e10)
        max_val = schema.get("maximum", 1e10)
        return st.floats(min_value=min_val, max_value=max_val, allow_nan=False, allow_infinity=False)

    def _array_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[list[Any]]:
        """Create array strategy from schema."""
        items = schema.get("items", {})
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems", 10)

        item_strategy = self._schema_to_strategy(items) if items else st.none()
        return st.lists(item_strategy, min_size=min_items, max_size=max_items)

    def _object_strategy(self, schema: dict[str, Any]) -> st.SearchStrategy[dict[str, Any]]:
        """Create object strategy from schema."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not properties:
            return st.dictionaries(st.text(), st.none())

        # Build strategies for required properties only
        # Optional properties are handled separately
        required_strategies: dict[str, st.SearchStrategy[Any]] = {}
        optional_strategies: dict[str, st.SearchStrategy[Any]] = {}
        
        for prop_name, prop_schema in properties.items():
            strategy = self._schema_to_strategy(prop_schema)
            if prop_name in required:
                required_strategies[prop_name] = strategy
            else:
                optional_strategies[prop_name] = strategy

        # Start with required properties
        if required_strategies:
            base_strategy = st.fixed_dictionaries(required_strategies)
        else:
            base_strategy = st.just({})

        # Add optional properties one at a time
        for prop_name, strategy in optional_strategies.items():
            base_strategy = st.builds(
                lambda d, v: {**d, prop_name: v} if v is not None else d,
                base_strategy,
                st.one_of(st.none(), strategy)
            )

        return base_strategy

    def _test_triggers(self, triggers: list[str], skill_name: str) -> EvalResult:
        """Test that triggers are valid strings."""
        result = EvalResult(property_name=f"{skill_name}.triggers", test_count=len(triggers))

        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, str):
                result.passed = False
                result.failure_count += 1
                result.errors.append(f"Trigger {i} is not a string: {type(trigger)}")
            elif not trigger.strip():
                result.passed = False
                result.failure_count += 1
                result.errors.append(f"Trigger {i} is empty")
            elif len(trigger) > 500:
                result.warnings.append(f"Trigger {i} is very long ({len(trigger)} chars)")

        return result

    def _test_handler(
        self, handler: Callable[[dict[str, Any]], Any], fm: FrontmatterResult
    ) -> EvalResult:
        """Test a custom handler function with PBT."""
        result = EvalResult(property_name=f"{fm.name}.handler")

        # Test with null input
        try:
            handler(None)  # type: ignore
            result.test_count += 1
        except TypeError:
            result.test_count += 1
        except Exception as e:
            result.errors.append(f"Handler crashed with None: {e}")
            result.failure_count += 1

        # Test with empty input
        try:
            handler({})
            result.test_count += 1
        except Exception as e:
            result.errors.append(f"Handler crashed with empty input: {e}")
            result.failure_count += 1

        result.passed = result.failure_count == 0
        return result


def run_regression_check(
    skill_path: Path,
    baseline_path: Path | None = None,
) -> tuple[bool, list[str]]:
    """
    Run regression check comparing current vs baseline results.

    Args:
        skill_path: Path to skill being tested
        baseline_path: Path to baseline results file

    Returns:
        Tuple of (passed, regressions)
    """
    baseline = baseline_path or skill_path.with_suffix(".baseline.json")

    if not baseline.exists():
        return True, ["No baseline found - first run"]

    try:
        baseline_data = json.loads(baseline.read_text())
        current_data: dict[str, Any] = {}

        # Run current evaluation
        runner = PBTRunner()
        results = runner.run_skill_tests(skill_path)
        current_data["test_results"] = [
            {"name": r.property_name, "passed": r.passed}
            for r in results
        ]

        # Compare
        suite = RegressionSuite(
            skill_name=skill_path.stem,
            skill_path=skill_path,
            baseline_results=baseline_data.get("test_results", {}),
            current_results={r["name"]: r["passed"] for r in current_data["test_results"]},
        )

        regressions = suite.compare()
        return len(regressions) == 0, regressions

    except Exception as e:
        return False, [f"Regression check failed: {e}"]


# ============================================================================
# Regression Checker (Task 2.5.2)
# ============================================================================

@dataclass
class RegressionBaseline:
    """Stores baseline test results for regression checking."""

    skill_name: str
    skill_version: str | None = None
    created_at: str = ""
    test_results: dict[str, bool] = field(default_factory=dict)
    performance_metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceDrift:
    """Represents detected performance drift."""

    metric_name: str
    baseline_value: float
    current_value: float
    drift_percentage: float
    threshold_percentage: float
    is_significant: bool


class RegressionChecker:
    """
    Compares current test results against stored baselines.

    Identifies performance drift and test result regressions across test runs.
    Stores and loads baselines from JSON files.

    Example:
        >>> checker = RegressionChecker()
        >>> checker.save_baseline("my-skill", results, metrics)
        >>> drift = checker.check_performance_drift("my-skill", current_metrics)
    """

    def __init__(
        self,
        *,
        baseline_dir: Path | str | None = None,
        performance_threshold: float = 20.0,
    ) -> None:
        """
        Initialize the regression checker.

        Args:
            baseline_dir: Directory to store baseline files
            performance_threshold: Percentage threshold for flagging drift
        """
        self.baseline_dir = Path(baseline_dir) if baseline_dir else Path(".baselines")
        self.performance_threshold = performance_threshold

    def save_baseline(
        self,
        skill_name: str,
        test_results: list[EvalResult],
        performance_metrics: dict[str, float] | None = None,
        *,
        skill_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Save baseline test results to a JSON file.

        Args:
            skill_name: Name of the skill
            test_results: List of evaluation results
            performance_metrics: Optional performance timing metrics
            skill_version: Optional skill version
            metadata: Optional additional metadata

        Returns:
            Path to the saved baseline file
        """
        from datetime import datetime, timezone

        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        baseline = RegressionBaseline(
            skill_name=skill_name,
            skill_version=skill_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            test_results={r.property_name: r.passed for r in test_results},
            performance_metrics=performance_metrics or {},
            metadata=metadata or {},
        )

        baseline_file = self.baseline_dir / f"{skill_name}.baseline.json"
        baseline_file.write_text(json.dumps(baseline.__dict__, indent=2, default=str))

        return baseline_file

    def load_baseline(self, skill_name: str) -> RegressionBaseline | None:
        """
        Load baseline test results from a JSON file.

        Args:
            skill_name: Name of the skill

        Returns:
            RegressionBaseline if found, None otherwise
        """
        baseline_file = self.baseline_dir / f"{skill_name}.baseline.json"

        if not baseline_file.exists():
            return None

        try:
            data = json.loads(baseline_file.read_text())
            return RegressionBaseline(
                skill_name=data.get("skill_name", skill_name),
                skill_version=data.get("skill_version"),
                created_at=data.get("created_at", ""),
                test_results=data.get("test_results", {}),
                performance_metrics=data.get("performance_metrics", {}),
                metadata=data.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def compare_results(
        self,
        skill_name: str,
        current_results: list[EvalResult],
    ) -> tuple[bool, list[str]]:
        """
        Compare current test results against stored baseline.

        Args:
            skill_name: Name of the skill
            current_results: Current evaluation results

        Returns:
            Tuple of (has_regressions, list_of_regression_descriptions)
        """
        baseline = self.load_baseline(skill_name)

        if baseline is None:
            return True, ["No baseline found - first run"]

        regressions: list[str] = []
        current_map = {r.property_name: r.passed for r in current_results}

        # Check for regressions (previously passing, now failing)
        for prop_name, was_passing in baseline.test_results.items():
            if was_passing:
                is_passing = current_map.get(prop_name, False)
                if not is_passing:
                    regressions.append(f"Regression in {prop_name}: was passing, now failing")

        # Check for removed properties
        for prop_name in baseline.test_results:
            if prop_name not in current_map:
                regressions.append(f"Property {prop_name} was removed from test suite")

        return len(regressions) == 0, regressions

    def check_performance_drift(
        self,
        skill_name: str,
        current_metrics: dict[str, float],
        *,
        threshold_percentage: float | None = None,
    ) -> list[PerformanceDrift]:
        """
        Identify performance drift between current and baseline metrics.

        Args:
            skill_name: Name of the skill
            current_metrics: Current performance metrics
            threshold_percentage: Override threshold for this check

        Returns:
            List of detected performance drifts
        """
        baseline = self.load_baseline(skill_name)

        if baseline is None:
            return []

        threshold = threshold_percentage or self.performance_threshold
        drifts: list[PerformanceDrift] = []

        for metric_name, current_value in current_metrics.items():
            baseline_value = baseline.performance_metrics.get(metric_name)

            if baseline_value is None or baseline_value == 0:
                continue

            drift_pct = ((current_value - baseline_value) / baseline_value) * 100
            is_significant = abs(drift_pct) > threshold

            drifts.append(PerformanceDrift(
                metric_name=metric_name,
                baseline_value=baseline_value,
                current_value=current_value,
                drift_percentage=drift_pct,
                threshold_percentage=threshold,
                is_significant=is_significant,
            ))

        return drifts

    def get_drift_report(
        self,
        skill_name: str,
        current_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """
        Generate a detailed performance drift report.

        Args:
            skill_name: Name of the skill
            current_metrics: Current performance metrics

        Returns:
            Dictionary with drift analysis details
        """
        drifts = self.check_performance_drift(skill_name, current_metrics)
        significant_drifts = [d for d in drifts if d.is_significant]

        return {
            "skill_name": skill_name,
            "total_metrics_checked": len(drifts),
            "significant_drifts": len(significant_drifts),
            "drifts": [
                {
                    "metric": d.metric_name,
                    "baseline": d.baseline_value,
                    "current": d.current_value,
                    "drift_percentage": round(d.drift_percentage, 2),
                    "is_significant": d.is_significant,
                }
                for d in drifts
            ],
            "summary": self._generate_drift_summary(significant_drifts),
        }

    def _generate_drift_summary(self, drifts: list[PerformanceDrift]) -> str:
        """Generate a human-readable drift summary."""
        if not drifts:
            return "No significant performance drift detected"

        summaries: list[str] = []
        for d in drifts:
            direction = "slower" if d.drift_percentage > 0 else "faster"
            summaries.append(
                f"{d.metric_name} is {abs(d.drift_percentage):.1f}% {direction} "
                f"(threshold: {d.threshold_percentage}%)"
            )

        return "; ".join(summaries)


# ============================================================================
# Evidence Recorder (Task 2.5.3)
# ============================================================================

@dataclass
class EvidenceRecord:
    """Captures test evidence for a single test execution."""

    record_id: str
    test_id: str
    timestamp: str
    test_case: dict[str, Any]
    output: Any
    expected: Any | None
    status: str  # pass, fail, error
    evidence_type: str  # correctness, violation, baseline
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "recordId": self.record_id,
            "testId": self.test_id,
            "timestamp": self.timestamp,
            "testCase": self.test_case,
            "output": self.output,
            "expected": self.expected,
            "status": self.status,
            "evidenceType": self.evidence_type,
            "durationMs": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceStore:
    """In-memory store for evidence records."""

    records: list[EvidenceRecord] = field(default_factory=list)

    def add(self, record: EvidenceRecord) -> None:
        """Add a record to the store."""
        self.records.append(record)

    def get_by_test_id(self, test_id: str) -> list[EvidenceRecord]:
        """Get all records for a specific test."""
        return [r for r in self.records if r.test_id == test_id]

    def get_by_status(self, status: str) -> list[EvidenceRecord]:
        """Get all records with a specific status."""
        return [r for r in self.records if r.status == status]

    def get_history(self) -> list[dict[str, Any]]:
        """Get complete evidence history as dictionaries."""
        return [r.to_dict() for r in self.records]


class EvidenceRecorder:
    """
    Captures test inputs and outputs for evidence-driven testing.

    Stores evidence of correctness for passing tests and failing inputs
    with expected outputs for test failures.

    Example:
        >>> recorder = EvidenceRecorder()
        >>> recorder.record_pass("test-1", {"input": 1}, {"output": 2})
        >>> recorder.record_fail("test-2", {"input": -1}, None, 1)
    """

    def __init__(
        self,
        *,
        store_path: Path | str | None = None,
        max_records: int = 10000,
    ) -> None:
        """
        Initialize the evidence recorder.

        Args:
            store_path: Optional path to persist evidence
            max_records: Maximum records to keep in memory
        """
        self.store_path = Path(store_path) if store_path else None
        self.max_records = max_records
        self._store = EvidenceStore()

    def record_pass(
        self,
        test_id: str,
        test_case: dict[str, Any],
        output: Any,
        *,
        expected: Any | None = None,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        """
        Record evidence for a passing test.

        Args:
            test_id: Identifier for the test
            test_case: The test input and parameters
            output: The observed output
            expected: Optional expected output
            duration_ms: Test execution duration in milliseconds
            metadata: Optional additional metadata

        Returns:
            The created EvidenceRecord
        """
        record = self._create_record(
            test_id=test_id,
            test_case=test_case,
            output=output,
            expected=expected,
            status="pass",
            evidence_type="correctness",
            duration_ms=duration_ms,
            metadata=metadata,
        )

        self._store.add(record)
        self._enforce_limit()

        return record

    def record_fail(
        self,
        test_id: str,
        test_case: dict[str, Any],
        output: Any,
        expected: Any,
        *,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        """
        Record evidence for a failing test.

        Args:
            test_id: Identifier for the test
            test_case: The test input and parameters
            output: The observed output
            expected: The expected output
            duration_ms: Test execution duration in milliseconds
            metadata: Optional additional metadata

        Returns:
            The created EvidenceRecord
        """
        record = self._create_record(
            test_id=test_id,
            test_case=test_case,
            output=output,
            expected=expected,
            status="fail",
            evidence_type="violation",
            duration_ms=duration_ms,
            metadata=metadata,
        )

        self._store.add(record)
        self._enforce_limit()

        return record

    def record_error(
        self,
        test_id: str,
        test_case: dict[str, Any],
        error: str,
        *,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        """
        Record evidence for a test that encountered an error.

        Args:
            test_id: Identifier for the test
            test_case: The test input and parameters
            error: The error message or exception
            duration_ms: Test execution duration in milliseconds
            metadata: Optional additional metadata

        Returns:
            The created EvidenceRecord
        """
        record = self._create_record(
            test_id=test_id,
            test_case=test_case,
            output={"error": error},
            expected=None,
            status="error",
            evidence_type="violation",
            duration_ms=duration_ms,
            metadata=metadata,
        )

        self._store.add(record)
        self._enforce_limit()

        return record

    def get_evidence(self, test_id: str) -> list[EvidenceRecord]:
        """
        Get all evidence for a specific test.

        Args:
            test_id: Identifier for the test

        Returns:
            List of EvidenceRecords for the test
        """
        return self._store.get_by_test_id(test_id)

    def get_history(self) -> list[dict[str, Any]]:
        """
        Get complete test evidence history.

        Returns:
            List of evidence records as dictionaries
        """
        return self._store.get_history()

    def get_passing_evidence(self) -> list[EvidenceRecord]:
        """Get all passing test evidence."""
        return self._store.get_by_status("pass")

    def get_failing_evidence(self) -> list[EvidenceRecord]:
        """Get all failing test evidence."""
        return self._store.get_by_status("fail")

    def save_to_file(self, path: Path | str | None = None) -> bool:
        """
        Save evidence store to a JSON file.

        Logs failures without halting execution.

        Args:
            path: Override path for saving

        Returns:
            True if save succeeded, False otherwise
        """
        target_path = Path(path) if path else self.store_path

        if target_path is None:
            return False

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "record_count": len(self._store.records),
                "records": self.get_history(),
            }
            target_path.write_text(json.dumps(data, indent=2, default=str))
            return True
        except Exception:
            # Log failure without halting (per Requirements 6.5)
            return False

    def load_from_file(self, path: Path | str | None = None) -> bool:
        """
        Load evidence store from a JSON file.

        Args:
            path: Override path for loading

        Returns:
            True if load succeeded, False otherwise
        """
        target_path = Path(path) if path else self.store_path

        if target_path is None or not target_path.exists():
            return False

        try:
            data = json.loads(target_path.read_text())
            records = data.get("records", [])

            self._store = EvidenceStore()
            for r in records:
                record = EvidenceRecord(
                    record_id=r.get("recordId", ""),
                    test_id=r.get("testId", ""),
                    timestamp=r.get("timestamp", ""),
                    test_case=r.get("testCase", {}),
                    output=r.get("output"),
                    expected=r.get("expected"),
                    status=r.get("status", "pass"),
                    evidence_type=r.get("evidenceType", "correctness"),
                    duration_ms=r.get("durationMs", 0.0),
                    metadata=r.get("metadata", {}),
                )
                self._store.add(record)

            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all stored evidence."""
        self._store = EvidenceStore()

    def _create_record(
        self,
        test_id: str,
        test_case: dict[str, Any],
        output: Any,
        expected: Any | None,
        status: str,
        evidence_type: str,
        duration_ms: float,
        metadata: dict[str, Any] | None,
    ) -> EvidenceRecord:
        """Create a new evidence record with generated ID and timestamp."""
        from datetime import datetime, timezone
        import uuid

        return EvidenceRecord(
            record_id=str(uuid.uuid4()),
            test_id=test_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            test_case=test_case,
            output=output,
            expected=expected,
            status=status,
            evidence_type=evidence_type,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

    def _enforce_limit(self) -> None:
        """Enforce maximum record limit by removing oldest records."""
        if len(self._store.records) > self.max_records:
            # Remove oldest records
            excess = len(self._store.records) - self.max_records
            self._store.records = self._store.records[excess:]
