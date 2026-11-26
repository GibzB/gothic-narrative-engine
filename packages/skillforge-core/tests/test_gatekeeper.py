"""
Tests for Adversarial Gatekeeper module.

Tests for:
- Task 2.9.1: Malicious Input Generator
- Task 2.9.2: Exploit Monitor
- Task 2.9.3: Vulnerability Recorder
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    GatekeeperConfig,
    MonitoringConfig,
    ExploitPath,
)


# ============================================================================
# Malicious Input Generator Tests (Task 2.9.1)
# ============================================================================

class TestMaliciousInputGenerator:
    """Tests for MaliciousInputGenerator."""

    def test_generate_sql_injection(self):
        """Test SQL injection payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_sql_injection())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.SQL_INJECTION
            assert payload.payload != ""
            assert payload.severity in (VulnerabilitySeverity.HIGH, VulnerabilitySeverity.CRITICAL)

    def test_generate_xss(self):
        """Test XSS payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_xss())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.XSS
            # XSS payloads can be HTML tags, javascript:, or encoded variants
            assert payload.payload != ""

    def test_generate_command_injection(self):
        """Test command injection payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_command_injection())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.COMMAND_INJECTION
            assert payload.severity == VulnerabilitySeverity.CRITICAL

    def test_generate_path_traversal(self):
        """Test path traversal payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_path_traversal())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.PATH_TRAVERSAL
            # Path traversal payloads can be ../, ..\, or encoded variants
            assert payload.payload != ""

    def test_generate_ldap_injection(self):
        """Test LDAP injection payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_ldap_injection())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.LDAP_INJECTION

    def test_generate_xxe(self):
        """Test XXE payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_xxe())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.XXE
            assert "<!DOCTYPE" in payload.payload or "<!ENTITY" in payload.payload

    def test_generate_ssrf(self):
        """Test SSRF payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_ssrf())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.SSRF
            # SSRF payloads can be http://, file://, gopher://, dict://, etc.
            assert payload.payload != ""

    def test_generate_template_injection(self):
        """Test template injection payload generation."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_template_injection())
        
        assert len(payloads) > 0
        for payload in payloads:
            assert payload.vulnerability_type == VulnerabilityType.TEMPLATE_INJECTION
            # Template injection payloads can be {{, ${, #{, <%=, etc.
            assert payload.payload != ""

    def test_generate_all(self):
        """Test generating all payloads."""
        generator = MaliciousInputGenerator()
        
        payloads = list(generator.generate_all())
        
        # Should have payloads from all categories
        vuln_types = set(p.vulnerability_type for p in payloads)
        
        assert VulnerabilityType.SQL_INJECTION in vuln_types
        assert VulnerabilityType.XSS in vuln_types
        assert VulnerabilityType.COMMAND_INJECTION in vuln_types
        assert VulnerabilityType.PATH_TRAVERSAL in vuln_types

    def test_obfuscated_payloads(self):
        """Test that obfuscated payloads are included when enabled."""
        generator = MaliciousInputGenerator(include_obfuscated=True)
        
        sql_payloads = list(generator.generate_sql_injection())
        
        # Should include obfuscated payloads
        obfuscated = [p for p in sql_payloads if "obfuscated" in p.category]
        assert len(obfuscated) > 0

    def test_no_obfuscated_payloads_when_disabled(self):
        """Test that obfuscated payloads are excluded when disabled."""
        generator = MaliciousInputGenerator(include_obfuscated=False)
        
        sql_payloads = list(generator.generate_sql_injection())
        
        obfuscated = [p for p in sql_payloads if "obfuscated" in p.category]
        assert len(obfuscated) == 0

    def test_malicious_input_dataclass(self):
        """Test MaliciousInput dataclass."""
        payload = MaliciousInput(
            vulnerability_type=VulnerabilityType.SQL_INJECTION,
            payload="' OR '1'='1",
            description="Basic SQL injection",
            severity=VulnerabilitySeverity.HIGH,
            category="sql_injection",
        )
        
        assert payload.vulnerability_type == VulnerabilityType.SQL_INJECTION
        assert payload.context == "general"
        assert payload.encoding == "plain"


# ============================================================================
# Exploit Monitor Tests (Task 2.9.2)
# ============================================================================

class TestExploitMonitor:
    """Tests for ExploitMonitor."""

    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        monitor = ExploitMonitor()
        
        monitor.start_monitoring()
        assert monitor._monitoring is True
        
        anomalies = monitor.stop_monitoring()
        assert monitor._monitoring is False
        assert isinstance(anomalies, list)

    def test_check_memory_usage_exceeded(self):
        """Test memory usage limit exceeded."""
        config = MonitoringConfig(memory_limit_mb=100.0)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_memory_usage(150.0)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.MEMORY_EXHAUSTION
        assert anomaly.severity == VulnerabilitySeverity.HIGH

    def test_check_memory_usage_ok(self):
        """Test memory usage within limits."""
        config = MonitoringConfig(memory_limit_mb=100.0)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_memory_usage(50.0)
        
        assert anomaly is None

    def test_check_cpu_usage_exceeded(self):
        """Test CPU usage limit exceeded."""
        config = MonitoringConfig(cpu_limit_percent=50.0)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_cpu_usage(80.0)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.CPU_SPIKE

    def test_check_file_operations_exceeded(self):
        """Test file operations limit exceeded."""
        config = MonitoringConfig(max_file_operations=10)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_file_operations(50)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.FILE_SYSTEM_ABUSE

    def test_check_network_requests_exceeded(self):
        """Test network requests limit exceeded."""
        config = MonitoringConfig(max_network_requests=5)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_network_requests(10)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.NETWORK_ABUSE

    def test_check_process_spawn_exceeded(self):
        """Test process spawn limit exceeded."""
        config = MonitoringConfig(max_process_spawns=0)
        monitor = ExploitMonitor(config)
        
        anomaly = monitor.check_process_spawn(1)
        
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.PROCESS_SPAWN
        assert anomaly.severity == VulnerabilitySeverity.CRITICAL

    def test_detect_unauthorized_access(self):
        """Test unauthorized access detection."""
        monitor = ExploitMonitor()
        
        anomaly = monitor.detect_unauthorized_access("/etc/shadow", "read")
        
        assert anomaly.anomaly_type == AnomalyType.UNAUTHORIZED_ACCESS
        assert "/etc/shadow" in anomaly.description
        assert anomaly.severity == VulnerabilitySeverity.HIGH

    def test_detect_sensitive_data_exfiltration(self):
        """Test sensitive data exfiltration detection."""
        monitor = ExploitMonitor()
        
        anomaly = monitor.detect_sensitive_data_exfiltration("passwords", "external-api.com")
        
        assert anomaly.anomaly_type == AnomalyType.SENSITIVE_DATA_EXFILTRATION
        assert anomaly.severity == VulnerabilitySeverity.CRITICAL

    def test_timeout_detection(self):
        """Test execution timeout detection."""
        config = MonitoringConfig(execution_timeout_seconds=0.1)
        monitor = ExploitMonitor(config)
        
        monitor.start_monitoring()
        import time
        time.sleep(0.2)
        anomalies = monitor.stop_monitoring()
        
        # Should detect timeout
        timeout_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.INFINITE_LOOP]
        assert len(timeout_anomalies) == 1

    def test_anomaly_dataclass(self):
        """Test Anomaly dataclass."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.MEMORY_EXHAUSTION,
            severity=VulnerabilitySeverity.HIGH,
            description="Memory exceeded",
            detected_at="2024-01-01T00:00:00",
        )
        
        assert anomaly.details == {}
        assert anomaly.remediation is None


# ============================================================================
# Vulnerability Recorder Tests (Task 2.9.3)
# ============================================================================

class TestVulnerabilityRecorder:
    """Tests for VulnerabilityRecorder."""

    def test_record_vulnerability_basic(self):
        """Test basic vulnerability recording."""
        recorder = VulnerabilityRecorder()
        
        report = recorder.record_vulnerability(
            skill_name="test-skill",
            vuln_type=VulnerabilityType.SQL_INJECTION,
        )
        
        assert report.vulnerability_id.startswith("VULN-")
        assert report.vulnerability_type == VulnerabilityType.SQL_INJECTION
        assert report.skill_name == "test-skill"

    def test_record_vulnerability_with_input(self):
        """Test recording vulnerability with malicious input."""
        recorder = VulnerabilityRecorder()
        
        malicious_input = MaliciousInput(
            vulnerability_type=VulnerabilityType.XSS,
            payload="<script>alert(1)</script>",
            description="XSS test",
            severity=VulnerabilitySeverity.HIGH,
            category="xss",
        )
        
        report = recorder.record_vulnerability(
            skill_name="test-skill",
            vuln_type=VulnerabilityType.XSS,
            malicious_input=malicious_input,
        )
        
        assert report.malicious_input is not None
        assert report.malicious_input.payload == "<script>alert(1)</script>"

    def test_record_vulnerability_with_anomaly(self):
        """Test recording vulnerability with anomaly."""
        recorder = VulnerabilityRecorder()
        
        anomaly = Anomaly(
            anomaly_type=AnomalyType.INFINITE_LOOP,
            severity=VulnerabilitySeverity.HIGH,
            description="Execution timeout",
            detected_at="2024-01-01T00:00:00",
        )
        
        report = recorder.record_vulnerability(
            skill_name="test-skill",
            vuln_type=VulnerabilityType.INFINITE_LOOP,
            anomaly=anomaly,
        )
        
        assert report.anomaly is not None

    def test_get_reports(self):
        """Test getting recorded reports."""
        recorder = VulnerabilityRecorder()
        
        recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        recorder.record_vulnerability("skill-2", VulnerabilityType.XSS)
        recorder.record_vulnerability("skill-1", VulnerabilityType.COMMAND_INJECTION)
        
        all_reports = recorder.get_reports()
        assert len(all_reports) == 3
        
        skill1_reports = recorder.get_reports(skill_name="skill-1")
        assert len(skill1_reports) == 2
        
        sql_reports = recorder.get_reports(vuln_type=VulnerabilityType.SQL_INJECTION)
        assert len(sql_reports) == 1

    def test_get_critical_vulnerabilities(self):
        """Test getting critical vulnerabilities."""
        recorder = VulnerabilityRecorder()
        
        recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        recorder.record_vulnerability("skill-1", VulnerabilityType.COMMAND_INJECTION)  # Critical
        
        critical = recorder.get_critical_vulnerabilities()
        
        assert len(critical) == 1
        assert critical[0].vulnerability_type == VulnerabilityType.COMMAND_INJECTION

    def test_get_report_summary(self):
        """Test getting report summary."""
        recorder = VulnerabilityRecorder()
        
        recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        recorder.record_vulnerability("skill-1", VulnerabilityType.XSS)
        recorder.record_vulnerability("skill-2", VulnerabilityType.SQL_INJECTION)
        
        summary = recorder.get_report_summary()
        
        assert summary["total_vulnerabilities"] == 3
        assert summary["by_type"]["sql_injection"] == 2
        assert summary["by_type"]["xss"] == 1
        assert summary["by_skill"]["skill-1"] == 2

    def test_clear_reports(self):
        """Test clearing reports."""
        recorder = VulnerabilityRecorder()
        
        recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        count = recorder.clear_reports()
        
        assert count == 1
        assert len(recorder.get_reports()) == 0

    def test_export_reports(self, tmp_path):
        """Test exporting reports to file."""
        export_file = tmp_path / "vulnerabilities.json"
        recorder = VulnerabilityRecorder(output_path=export_file)
        
        recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        
        result = recorder.export_reports()
        
        assert result is True
        assert export_file.exists()
        
        data = json.loads(export_file.read_text())
        assert data["total_reports"] == 1

    def test_cwe_mapping(self):
        """Test CWE ID mapping."""
        recorder = VulnerabilityRecorder()
        
        report = recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        assert report.cwe_id == "CWE-89"
        
        report = recorder.record_vulnerability("skill-1", VulnerabilityType.XSS)
        assert report.cwe_id == "CWE-79"

    def test_severity_derivation(self):
        """Test automatic severity derivation."""
        recorder = VulnerabilityRecorder()
        
        # Command injection should be critical
        report = recorder.record_vulnerability("skill-1", VulnerabilityType.COMMAND_INJECTION)
        assert report.severity == VulnerabilitySeverity.CRITICAL
        
        # SQL injection should be high
        report = recorder.record_vulnerability("skill-1", VulnerabilityType.SQL_INJECTION)
        assert report.severity == VulnerabilitySeverity.HIGH

    def test_report_to_dict(self):
        """Test VulnerabilityReport.to_dict()."""
        recorder = VulnerabilityRecorder()
        
        report = recorder.record_vulnerability(
            skill_name="test-skill",
            vuln_type=VulnerabilityType.SQL_INJECTION,
            description="Test vulnerability",
        )
        
        d = report.to_dict()
        
        assert d["skillName"] == "test-skill"
        assert d["vulnerabilityType"] == "sql_injection"
        assert d["description"] == "Test vulnerability"
        assert "vulnerabilityId" in d
        assert "detectedAt" in d

    def test_exploit_path_recording(self):
        """Test recording exploit path."""
        recorder = VulnerabilityRecorder()
        
        exploit_path = [
            ExploitPath(
                step_number=1,
                action="input_received",
                input_value="' OR '1'='1",
                output_value=None,
            ),
            ExploitPath(
                step_number=2,
                action="query_executed",
                input_value="SELECT * FROM users WHERE id = '' OR '1'='1'",
                output_value="All user records",
            ),
        ]
        
        report = recorder.record_vulnerability(
            skill_name="test-skill",
            vuln_type=VulnerabilityType.SQL_INJECTION,
            exploit_path=exploit_path,
        )
        
        assert len(report.exploit_path) == 2
        assert report.exploit_path[0].action == "input_received"


# ============================================================================
# Adversarial Gatekeeper Integration Tests
# ============================================================================

class TestAdversarialGatekeeper:
    """Tests for AdversarialGatekeeper orchestrator."""

    def test_disabled_gatekeeping(self):
        """Test that gatekeeping can be disabled."""
        config = GatekeeperConfig(enabled=False)
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            return "result"
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        assert result.tested is False
        assert "disabled" in result.reason.lower()

    def test_enabled_gatekeeping(self):
        """Test enabled gatekeeping."""
        config = GatekeeperConfig(enabled=True)
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            return "safe result"
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        assert result.tested is True
        assert result.inputs_tested > 0

    def test_detect_vulnerability_in_output(self):
        """Test detecting vulnerability indicators in output."""
        config = GatekeeperConfig(enabled=True)
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            # Simulate vulnerable output
            if "'" in data.get("input", ""):
                return "SQL syntax error near '' at line 1"
            return "normal output"
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        assert result.vulnerabilities_found > 0

    def test_fail_on_critical(self):
        """Test failing pipeline on critical vulnerability."""
        config = GatekeeperConfig(
            enabled=True,
            fail_on_critical=True,
        )
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            raise RuntimeError("Command injection: whoami")
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        assert result.should_fail_pipeline is True

    def test_no_fail_on_critical_when_disabled(self):
        """Test not failing pipeline when fail_on_critical is False."""
        config = GatekeeperConfig(
            enabled=True,
            fail_on_critical=False,
        )
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            raise RuntimeError("Command injection")
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        # Should have vulnerabilities but not fail pipeline
        assert result.vulnerabilities_found > 0
        assert result.should_fail_pipeline is False

    def test_custom_vulnerability_categories(self):
        """Test testing specific vulnerability categories."""
        config = GatekeeperConfig(
            enabled=True,
            vulnerability_categories=["sql_injection"],
        )
        gatekeeper = AdversarialGatekeeper(config)
        
        def executor(skill, data):
            return "result"
        
        result = gatekeeper.test_skill("test-skill", executor)
        
        # Should only test SQL injection payloads
        vuln_types = set(v.vulnerability_type for v in result.vulnerabilities)
        # All should be SQL injection related
        assert all(vt == VulnerabilityType.SQL_INJECTION for vt in vuln_types) or len(vuln_types) == 0

    def test_result_to_dict(self):
        """Test GatekeeperResult.to_dict()."""
        config = GatekeeperConfig(enabled=True)
        gatekeeper = AdversarialGatekeeper(config)
        result = gatekeeper.test_skill("test-skill", lambda s, d: "ok")
        
        d = result.to_dict()
        
        assert "skillName" in d
        assert "tested" in d
        assert "vulnerabilitiesFound" in d
        assert "shouldFailPipeline" in d


# ============================================================================
# Vulnerability Type Tests
# ============================================================================

class TestVulnerabilityTypes:
    """Tests for vulnerability type enums."""

    def test_vulnerability_type_values(self):
        """Test all vulnerability type values."""
        expected = [
            "sql_injection",
            "xss",
            "command_injection",
            "path_traversal",
            "ldap_injection",
            "xxe",
            "ssrf",
            "template_injection",
            "deserialization",
            "open_redirect",
            "auth_bypass",
            "memory_exhaustion",
            "infinite_loop",
            "unauthorized_access",
            "information_disclosure",
        ]
        
        for v in expected:
            assert VulnerabilityType(v).value == v

    def test_vulnerability_severity_values(self):
        """Test all severity values."""
        expected = ["critical", "high", "medium", "low", "info"]
        
        for v in expected:
            assert VulnerabilitySeverity(v).value == v

    def test_anomaly_type_values(self):
        """Test all anomaly type values."""
        expected = [
            "memory_exhaustion",
            "cpu_spike",
            "infinite_loop",
            "unauthorized_access",
            "file_system_abuse",
            "network_abuse",
            "process_spawn",
            "sensitive_data_exfiltration",
        ]
        
        for v in expected:
            assert AnomalyType(v).value == v
