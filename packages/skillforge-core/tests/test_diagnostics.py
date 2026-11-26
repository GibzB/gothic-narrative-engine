"""
Tests for Performance & Correctness Diagnostics.

Run with: pytest tests/test_diagnostics.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase

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
from skillforge.evals import (
    RegressionChecker,
    RegressionBaseline,
    EvidenceRecorder,
    EvidenceRecord,
    EvalResult,
)


# ============================================================================
# Performance Analyzer Tests
# ============================================================================

class TestPerformanceAnalyzer:
    """Tests for the performance analyzer."""

    def test_analyze_with_no_issues(self) -> None:
        """Test analysis with metrics within thresholds."""
        analyzer = PerformanceAnalyzer()
        metrics = {
            "execution_time_ms": 500.0,
            "memory_peak_mb": 100.0,
        }
        report = analyzer.analyze("test-skill", metrics)

        assert report.skill_name == "test-skill"
        assert report.total_metrics == 2
        assert len(report.issues) == 0
        assert not report.has_critical_issues
        assert "No performance issues" in report.summary

    def test_analyze_with_warning_threshold_exceeded(self) -> None:
        """Test analysis with warning threshold exceeded."""
        analyzer = PerformanceAnalyzer()
        metrics = {
            "execution_time_ms": 1500.0,  # Warning threshold is 1000
        }
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 1
        assert report.issues[0].severity == "warning"
        assert not report.has_critical_issues

    def test_analyze_with_critical_threshold_exceeded(self) -> None:
        """Test analysis with critical threshold exceeded."""
        analyzer = PerformanceAnalyzer()
        metrics = {
            "execution_time_ms": 6000.0,  # Critical threshold is 5000
        }
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 1
        assert report.issues[0].severity == "critical"
        assert report.has_critical_issues

    def test_analyze_with_multiple_issues(self) -> None:
        """Test analysis with multiple metrics exceeding thresholds."""
        analyzer = PerformanceAnalyzer()
        metrics = {
            "execution_time_ms": 6000.0,
            "memory_peak_mb": 1500.0,
            "cpu_time_ms": 500.0,  # Within threshold
        }
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 2
        assert report.has_critical_issues

    def test_custom_thresholds(self) -> None:
        """Test analyzer with custom thresholds."""
        analyzer = PerformanceAnalyzer(
            custom_thresholds={"execution_time_ms": (100.0, 500.0)}
        )
        metrics = {"execution_time_ms": 150.0}
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 1
        assert report.issues[0].severity == "warning"

    def test_set_threshold(self) -> None:
        """Test setting a threshold dynamically."""
        analyzer = PerformanceAnalyzer()
        analyzer.set_threshold("custom_metric", 50.0, 100.0)

        threshold = analyzer.get_threshold("custom_metric")
        assert threshold == (50.0, 100.0)

        metrics = {"custom_metric": 75.0}
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 1
        assert report.issues[0].severity == "warning"

    def test_analyze_batch(self) -> None:
        """Test batch analysis of multiple skills."""
        analyzer = PerformanceAnalyzer()
        skills_metrics = {
            "skill-1": {"execution_time_ms": 500.0},
            "skill-2": {"execution_time_ms": 6000.0},
        }
        reports = analyzer.analyze_batch(skills_metrics)

        assert len(reports) == 2
        assert not reports[0].has_critical_issues
        assert reports[1].has_critical_issues

    def test_report_to_dict(self) -> None:
        """Test report serialization to dictionary."""
        analyzer = PerformanceAnalyzer()
        metrics = {"execution_time_ms": 6000.0}
        report = analyzer.analyze("test-skill", metrics)
        data = report.to_dict()

        assert data["skillName"] == "test-skill"
        assert data["hasCriticalIssues"] is True
        assert len(data["issues"]) == 1
        assert data["metrics"] == metrics

    def test_unknown_metric_no_issue(self) -> None:
        """Test that unknown metrics don't generate issues."""
        analyzer = PerformanceAnalyzer()
        metrics = {"unknown_metric": 999999.0}
        report = analyzer.analyze("test-skill", metrics)

        assert len(report.issues) == 0

    def test_suggestions_generated(self) -> None:
        """Test that suggestions are generated for issues."""
        analyzer = PerformanceAnalyzer()
        metrics = {"execution_time_ms": 6000.0}
        report = analyzer.analyze("test-skill", metrics)

        assert report.issues[0].suggestion is not None
        assert "optimization" in report.issues[0].suggestion.lower()


# ============================================================================
# Code Analyzer Tests
# ============================================================================

class TestCodeAnalyzer:
    """Tests for the code analyzer."""

    def test_analyze_clean_code(self) -> None:
        """Test analysis of clean code with no issues."""
        analyzer = CodeAnalyzer()
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        # Should only have missing docstring info for the module
        # (function has docstring)
        assert not report.has_errors
        assert not report.has_security_issues

    def test_detect_hardcoded_secret(self) -> None:
        """Test detection of hard-coded secrets."""
        analyzer = CodeAnalyzer()
        code = '''
password = "secret123"
api_key = "sk-12345"
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.has_security_issues
        assert any(i.code == "HARD_CODED_SECRET" for i in report.issues)

    def test_detect_sql_injection_risk(self) -> None:
        """Test detection of SQL injection risks."""
        analyzer = CodeAnalyzer()
        # Match pattern: execute(... + ...
        code = '''
import sqlite3
conn.execute("SELECT * FROM users WHERE id = " + user_id)
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.has_security_issues
        assert any(i.code == "SQL_INJECTION_RISK" for i in report.issues)

    def test_detect_command_injection_risk(self) -> None:
        """Test detection of command injection risks."""
        analyzer = CodeAnalyzer()
        code = '''
import subprocess
subprocess.call("ls " + user_input, shell=True)
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.has_security_issues

    def test_detect_unsafe_deserialize(self) -> None:
        """Test detection of unsafe deserialization."""
        analyzer = CodeAnalyzer()
        code = '''
import pickle
data = pickle.loads(user_data)
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.has_security_issues
        assert any(i.code == "UNSAFE_DESERIALIZE" for i in report.issues)

    def test_detect_bare_except(self) -> None:
        """Test detection of bare except clauses."""
        analyzer = CodeAnalyzer()
        code = '''
try:
    risky_operation()
except:
    pass
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert any(i.code == "BARE_EXCEPT" for i in report.issues)

    def test_detect_eval_usage(self) -> None:
        """Test detection of eval() usage."""
        analyzer = CodeAnalyzer()
        code = '''
result = eval(user_expression)
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert any(i.code == "EVAL_USAGE" for i in report.issues)

    def test_syntax_error_detection(self) -> None:
        """Test detection of syntax errors."""
        analyzer = CodeAnalyzer()
        code = '''
def broken(
    # Missing closing paren
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.has_errors
        assert any(i.code == "SYNTAX_ERROR" for i in report.issues)

    def test_exclude_rules(self) -> None:
        """Test excluding specific rules."""
        analyzer = CodeAnalyzer(exclude_rules={"PRINT_IN_PRODUCTION"})
        code = '''
print("Debug output")
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert not any(i.code == "PRINT_IN_PRODUCTION" for i in report.issues)

    def test_custom_rules(self) -> None:
        """Test adding custom rules."""
        analyzer = CodeAnalyzer(
            custom_rules=[
                {
                    "code": "CUSTOM_RULE",
                    "pattern": r"forbidden_function",
                    "severity": "error",
                    "message": "Forbidden function used",
                }
            ]
        )
        code = '''
result = forbidden_function()
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert any(i.code == "CUSTOM_RULE" for i in report.issues)

    def test_analyze_file(self) -> None:
        """Test analyzing a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('password = "secret"\n')
            f.flush()

            analyzer = CodeAnalyzer()
            report = analyzer.analyze_file("test-skill", Path(f.name))

            assert report.has_security_issues

            Path(f.name).unlink()

    def test_analyze_nonexistent_file(self) -> None:
        """Test analyzing a nonexistent file."""
        analyzer = CodeAnalyzer()
        report = analyzer.analyze_file("test-skill", "/nonexistent/file.py")

        assert report.has_errors
        assert any(i.code == "FILE_NOT_FOUND" for i in report.issues)

    def test_code_stats_collection(self) -> None:
        """Test code statistics collection."""
        analyzer = CodeAnalyzer()
        code = '''
import os
from typing import List

def func1():
    pass

def func2():
    pass

class MyClass:
    pass
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.stats["function_count"] == 2
        assert report.stats["class_count"] == 1
        assert report.stats["import_count"] == 2

    def test_report_to_dict(self) -> None:
        """Test report serialization."""
        analyzer = CodeAnalyzer()
        code = 'password = "secret"'
        report = analyzer.analyze_code("test-skill", code, "skill.py")
        data = report.to_dict()

        assert data["skillName"] == "test-skill"
        assert data["hasSecurityIssues"] is True
        assert "issues" in data
        assert "stats" in data

    def test_add_rule_method(self) -> None:
        """Test adding rule via method."""
        analyzer = CodeAnalyzer()
        analyzer.add_rule(
            code="NO_SLEEP",
            pattern=r"time\.sleep",
            severity="warning",
            message="Sleep detected",
        )

        code = '''
import time
time.sleep(1)
'''
        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert any(i.code == "NO_SLEEP" for i in report.issues)


# ============================================================================
# Historical Analyzer Tests
# ============================================================================

class TestHistoricalAnalyzer:
    """Tests for the historical analyzer."""

    def test_record_and_analyze(self) -> None:
        """Test recording test runs and analyzing."""
        analyzer = HistoricalAnalyzer()

        # Record some test runs
        for i in range(5):
            analyzer.record_test_run(
                skill_name="test-skill",
                test_id="test-1",
                passed=i < 3,  # 2 failures
            )

        report = analyzer.analyze()

        assert report.skills_analyzed == 1
        assert report.total_test_runs == 5
        # Not enough failures for recurring pattern (threshold is 3)

    def test_detect_recurring_failures(self) -> None:
        """Test detection of recurring failure patterns."""
        analyzer = HistoricalAnalyzer(recurrence_threshold=3)

        # Record recurring failures
        for i in range(5):
            analyzer.record_test_run(
                skill_name="flaky-skill",
                test_id="test-1",
                passed=False,
            )

        report = analyzer.analyze()

        assert report.has_recurring_issues
        assert len(report.patterns) == 1
        assert report.patterns[0].pattern_type == "recurring"
        assert "flaky-skill" in report.skills_with_issues

    def test_failure_rate_calculation(self) -> None:
        """Test failure rate calculation."""
        analyzer = HistoricalAnalyzer()

        # 3 passes, 2 failures = 40% failure rate
        for passed in [True, True, True, False, False]:
            analyzer.record_test_run(
                skill_name="test-skill",
                test_id="test-1",
                passed=passed,
            )

        rate = analyzer.get_failure_rate("test-skill")

        assert rate == 40.0

    def test_get_skill_history(self) -> None:
        """Test retrieving history for a specific skill."""
        analyzer = HistoricalAnalyzer()

        analyzer.record_test_run("skill-1", "test-1", True)
        analyzer.record_test_run("skill-2", "test-2", False)
        analyzer.record_test_run("skill-1", "test-3", True)

        history = analyzer.get_skill_history("skill-1")

        assert len(history) == 2
        assert all(r.skill_name == "skill-1" for r in history)

    def test_save_and_load_history(self) -> None:
        """Test saving and loading history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"

            analyzer = HistoricalAnalyzer(history_path=history_path)

            for i in range(3):
                analyzer.record_test_run(
                    skill_name="test-skill",
                    test_id=f"test-{i}",
                    passed=i % 2 == 0,
                )

            # Save
            assert analyzer.save_history()

            # Load in new analyzer
            analyzer2 = HistoricalAnalyzer(history_path=history_path)
            assert analyzer2.load_history()

            assert len(analyzer2._history) == 3

    def test_clear_history(self) -> None:
        """Test clearing history."""
        analyzer = HistoricalAnalyzer()

        analyzer.record_test_run("skill-1", "test-1", True)
        analyzer.clear_history()

        assert len(analyzer._history) == 0

    def test_max_history_limit(self) -> None:
        """Test maximum history limit."""
        analyzer = HistoricalAnalyzer(max_history=5)

        for i in range(10):
            analyzer.record_test_run("skill-1", f"test-{i}", True)

        assert len(analyzer._history) == 5

    def test_report_to_dict(self) -> None:
        """Test report serialization."""
        analyzer = HistoricalAnalyzer(recurrence_threshold=2)

        for _ in range(3):
            analyzer.record_test_run("skill-1", "test-1", False)

        report = analyzer.analyze()
        data = report.to_dict()

        assert "patterns" in data
        assert "skillsWithIssues" in data
        assert data["hasRecurringIssues"] is True

    def test_correlated_failure_detection(self) -> None:
        """Test detection of correlated failures."""
        analyzer = HistoricalAnalyzer()

        # Create correlated failures at multiple distinct timestamps
        # The analyzer groups by minute, so use different minutes
        timestamps = [
            "2024-01-01T12:00:00",
            "2024-01-01T12:01:00",
            "2024-01-01T12:02:00",
        ]
        for ts in timestamps:
            analyzer.record_test_run(
                skill_name="skill-1",
                test_id="test-1",
                passed=False,
                timestamp=ts,
            )
            analyzer.record_test_run(
                skill_name="skill-2",
                test_id="test-2",
                passed=False,
                timestamp=ts,
            )

        report = analyzer.analyze()

        # Should detect correlation (3 co-occurrences >= 2 threshold)
        correlated_patterns = [
            p for p in report.patterns if p.pattern_type == "correlated"
        ]
        assert len(correlated_patterns) > 0


# ============================================================================
# Regression Checker Tests
# ============================================================================

class TestRegressionChecker:
    """Tests for the regression checker."""

    def test_save_and_load_baseline(self) -> None:
        """Test saving and loading baselines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = RegressionChecker(baseline_dir=tmpdir)

            results = [
                EvalResult(property_name="prop-1", passed=True),
                EvalResult(property_name="prop-2", passed=True),
            ]

            # Save baseline
            path = checker.save_baseline("test-skill", results)
            assert path.exists()

            # Load baseline
            baseline = checker.load_baseline("test-skill")
            assert baseline is not None
            assert baseline.skill_name == "test-skill"
            assert baseline.test_results == {"prop-1": True, "prop-2": True}

    def test_compare_results_no_regression(self) -> None:
        """Test comparison with no regressions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = RegressionChecker(baseline_dir=tmpdir)

            # Save baseline
            baseline_results = [
                EvalResult(property_name="prop-1", passed=True),
            ]
            checker.save_baseline("test-skill", baseline_results)

            # Compare with same results
            current_results = [
                EvalResult(property_name="prop-1", passed=True),
            ]
            passed, regressions = checker.compare_results("test-skill", current_results)

            assert passed
            assert len(regressions) == 0

    def test_compare_results_with_regression(self) -> None:
        """Test comparison with regression detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = RegressionChecker(baseline_dir=tmpdir)

            # Save baseline with passing test
            baseline_results = [
                EvalResult(property_name="prop-1", passed=True),
            ]
            checker.save_baseline("test-skill", baseline_results)

            # Compare with failing result
            current_results = [
                EvalResult(property_name="prop-1", passed=False),
            ]
            passed, regressions = checker.compare_results("test-skill", current_results)

            assert not passed
            assert len(regressions) == 1
            assert "Regression" in regressions[0]

    def test_performance_drift_detection(self) -> None:
        """Test performance drift detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = RegressionChecker(
                baseline_dir=tmpdir,
                performance_threshold=10.0,
            )

            # Save baseline with performance metrics
            results = [EvalResult(property_name="prop-1", passed=True)]
            checker.save_baseline(
                "test-skill",
                results,
                performance_metrics={"execution_time_ms": 100.0},
            )

            # Check for drift with slower performance
            drifts = checker.check_performance_drift(
                "test-skill",
                {"execution_time_ms": 150.0},  # 50% slower
            )

            assert len(drifts) == 1
            assert drifts[0].is_significant
            assert drifts[0].drift_percentage == 50.0

    def test_drift_report_generation(self) -> None:
        """Test drift report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checker = RegressionChecker(baseline_dir=tmpdir)

            results = [EvalResult(property_name="prop-1", passed=True)]
            checker.save_baseline(
                "test-skill",
                results,
                performance_metrics={"execution_time_ms": 100.0},
            )

            report = checker.get_drift_report(
                "test-skill",
                {"execution_time_ms": 120.0},
            )

            assert "skill_name" in report
            assert "drifts" in report
            assert "summary" in report

    def test_no_baseline_returns_none(self) -> None:
        """Test that missing baseline returns None."""
        checker = RegressionChecker(baseline_dir="/nonexistent")
        baseline = checker.load_baseline("nonexistent-skill")

        assert baseline is None


# ============================================================================
# Evidence Recorder Tests
# ============================================================================

class TestEvidenceRecorder:
    """Tests for the evidence recorder."""

    def test_record_pass(self) -> None:
        """Test recording passing test evidence."""
        recorder = EvidenceRecorder()
        record = recorder.record_pass(
            test_id="test-1",
            test_case={"input": 1},
            output={"result": 2},
        )

        assert record.status == "pass"
        assert record.evidence_type == "correctness"
        assert record.test_id == "test-1"

    def test_record_fail(self) -> None:
        """Test recording failing test evidence."""
        recorder = EvidenceRecorder()
        record = recorder.record_fail(
            test_id="test-1",
            test_case={"input": -1},
            output={"error": "Invalid"},
            expected={"result": "valid"},
        )

        assert record.status == "fail"
        assert record.evidence_type == "violation"
        assert record.expected == {"result": "valid"}

    def test_record_error(self) -> None:
        """Test recording error test evidence."""
        recorder = EvidenceRecorder()
        record = recorder.record_error(
            test_id="test-1",
            test_case={"input": "bad"},
            error="Exception occurred",
        )

        assert record.status == "error"
        assert record.output == {"error": "Exception occurred"}

    def test_get_evidence(self) -> None:
        """Test retrieving evidence by test ID."""
        recorder = EvidenceRecorder()

        recorder.record_pass("test-1", {"input": 1}, {"result": 2})
        recorder.record_pass("test-2", {"input": 2}, {"result": 4})
        recorder.record_fail("test-1", {"input": -1}, None, {"result": "valid"})

        evidence = recorder.get_evidence("test-1")

        assert len(evidence) == 2

    def test_get_history(self) -> None:
        """Test retrieving complete evidence history."""
        recorder = EvidenceRecorder()

        recorder.record_pass("test-1", {"input": 1}, {"result": 2})
        recorder.record_fail("test-2", {"input": -1}, None, {"result": "valid"})

        history = recorder.get_history()

        assert len(history) == 2
        assert all(isinstance(h, dict) for h in history)

    def test_get_passing_and_failing_evidence(self) -> None:
        """Test filtering evidence by status."""
        recorder = EvidenceRecorder()

        recorder.record_pass("test-1", {"input": 1}, {"result": 2})
        recorder.record_fail("test-2", {"input": -1}, None, {"result": "valid"})

        passing = recorder.get_passing_evidence()
        failing = recorder.get_failing_evidence()

        assert len(passing) == 1
        assert len(failing) == 1

    def test_save_and_load_evidence(self) -> None:
        """Test saving and loading evidence from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "evidence.json"

            recorder = EvidenceRecorder(store_path=store_path)

            recorder.record_pass("test-1", {"input": 1}, {"result": 2})
            recorder.record_fail("test-2", {"input": -1}, None, {"result": "valid"})

            # Save
            assert recorder.save_to_file()

            # Load in new recorder
            recorder2 = EvidenceRecorder(store_path=store_path)
            assert recorder2.load_from_file()

            history = recorder2.get_history()
            assert len(history) == 2

    def test_max_records_limit(self) -> None:
        """Test maximum records limit."""
        recorder = EvidenceRecorder(max_records=3)

        for i in range(5):
            recorder.record_pass(f"test-{i}", {"input": i}, {"result": i})

        assert len(recorder.get_history()) == 3

    def test_clear_evidence(self) -> None:
        """Test clearing all evidence."""
        recorder = EvidenceRecorder()

        recorder.record_pass("test-1", {"input": 1}, {"result": 2})
        recorder.clear()

        assert len(recorder.get_history()) == 0


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestDiagnosticsProperties:
    """Property-based tests for diagnostics."""

    @given(
        execution_time=st.floats(min_value=0, max_value=10000),
        memory_mb=st.floats(min_value=0, max_value=2000),
    )
    @settings(max_examples=30, database=InMemoryExampleDatabase())
    def test_performance_analyzer_consistency(
        self, execution_time: float, memory_mb: float
    ) -> None:
        """Property: Performance analysis is consistent for same inputs."""
        analyzer = PerformanceAnalyzer()
        metrics = {
            "execution_time_ms": execution_time,
            "memory_peak_mb": memory_mb,
        }

        report1 = analyzer.analyze("test-skill", metrics)
        report2 = analyzer.analyze("test-skill", metrics)

        assert report1.issue_count == report2.issue_count
        assert report1.has_critical_issues == report2.has_critical_issues

    @given(
        code_length=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_code_analyzer_line_count(self, code_length: int) -> None:
        """Property: Code analyzer correctly counts lines."""
        analyzer = CodeAnalyzer()
        code = "\n".join(["# comment"] * code_length)

        report = analyzer.analyze_code("test-skill", code, "skill.py")

        assert report.stats["line_count"] == code_length

    def test_code_analyzer_empty_code(self) -> None:
        """Test that empty code produces zero stats."""
        analyzer = CodeAnalyzer()
        report = analyzer.analyze_code("test-skill", "", "skill.py")

        assert report.stats["line_count"] == 0
        assert report.stats["non_empty_lines"] == 0

    @given(
        pass_count=st.integers(min_value=0, max_value=10),
        fail_count=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_historical_analyzer_totals(
        self, pass_count: int, fail_count: int
    ) -> None:
        """Property: Historical analyzer correctly counts total runs."""
        analyzer = HistoricalAnalyzer()

        for _ in range(pass_count):
            analyzer.record_test_run("skill-1", "test-1", True)
        for _ in range(fail_count):
            analyzer.record_test_run("skill-1", "test-1", False)

        report = analyzer.analyze()

        assert report.total_test_runs == pass_count + fail_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
