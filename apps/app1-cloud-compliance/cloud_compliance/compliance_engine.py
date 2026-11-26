"""
Compliance Engine - Load and execute compliance skills.

Provides a skill-based approach to compliance checking where
compliance rules are defined as skill definitions that can be
compiled, validated, and executed against IaC templates.

Task 3.3: Implement Compliance Engine
Validates: Requirements 3.1, 3.2, 3.3
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from cloud_compliance.iac_parser import ParsedResource, ParseResult


class Severity(str, Enum):
    """Compliance finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ComplianceFinding:
    """A single compliance finding."""

    rule_id: str
    rule_name: str
    severity: Severity
    status: ComplianceStatus
    resource_type: str
    resource_name: str
    message: str
    remediation: str = ""
    source_file: str = ""
    line_number: int = 0
    framework: str = ""  # CIS, NIST, SOC2, etc.
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "ruleId": self.rule_id,
            "ruleName": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "resourceType": self.resource_type,
            "resourceName": self.resource_name,
            "message": self.message,
            "remediation": self.remediation,
            "sourceFile": self.source_file,
            "lineNumber": self.line_number,
            "framework": self.framework,
            "references": self.references,
            "metadata": self.metadata,
        }


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""

    scan_timestamp: str
    files_scanned: int
    resources_scanned: int
    findings: list[ComplianceFinding] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0
    errors: int = 0
    frameworks: list[str] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def is_compliant(self) -> bool:
        return self.failed == 0 and self.errors == 0

    def get_findings_by_severity(self, severity: Severity) -> list[ComplianceFinding]:
        """Filter findings by severity."""
        return [f for f in self.findings if f.severity == severity]

    def get_findings_by_resource(self, resource_name: str) -> list[ComplianceFinding]:
        """Filter findings by resource name."""
        return [f for f in self.findings if f.resource_name == resource_name]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "scanTimestamp": self.scan_timestamp,
            "filesScanned": self.files_scanned,
            "resourcesScanned": self.resources_scanned,
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "total": self.total_findings,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "skipped": self.skipped,
                "errors": self.errors,
            },
            "isCompliant": self.is_compliant,
            "frameworks": self.frameworks,
        }


@dataclass
class ComplianceRule:
    """A compliance rule definition."""

    rule_id: str
    name: str
    description: str
    severity: Severity
    frameworks: list[str]
    resource_types: list[str]
    check_function: Callable[[ParsedResource], ComplianceFinding | None]
    remediation: str = ""
    references: list[str] = field(default_factory=list)

    def check(self, resource: ParsedResource) -> ComplianceFinding | None:
        """
        Check a resource against this rule.

        Args:
            resource: Parsed resource to check

        Returns:
            ComplianceFinding if rule is violated, None otherwise
        """
        if resource.resource_type not in self.resource_types:
            return None

        return self.check_function(resource)


class ComplianceEngine:
    """
    Engine for executing compliance checks against IaC templates.

    Loads compliance rules from skill definitions and executes them
    against parsed infrastructure resources.

    Task 3.3: Compliance Engine
    Validates: Requirements 3.1, 3.2, 3.3

    Example:
        >>> engine = ComplianceEngine()
        >>> engine.load_default_rules()
        >>> report = engine.scan(parse_results)
        >>> report.is_compliant
        False
    """

    def __init__(
        self,
        *,
        include_passed: bool = True,
        fail_on_error: bool = False,
    ) -> None:
        """
        Initialize the compliance engine.

        Args:
            include_passed: Include passed checks in report
            fail_on_error: Treat check errors as failures
        """
        self.include_passed = include_passed
        self.fail_on_error = fail_on_error
        self._rules: dict[str, ComplianceRule] = {}

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def register_rule(self, rule: ComplianceRule) -> None:
        """
        Register a compliance rule.

        Args:
            rule: Compliance rule to register
        """
        self._rules[rule.rule_id] = rule

    def load_default_rules(self) -> None:
        """Load default AWS security compliance rules."""
        # S3 Rules
        self.register_rule(self._create_s3_public_access_rule())
        self.register_rule(self._create_s3_encryption_rule())
        self.register_rule(self._create_s3_versioning_rule())
        self.register_rule(self._create_s3_logging_rule())

        # IAM Rules
        self.register_rule(self._create_iam_wildcard_actions_rule())
        self.register_rule(self._create_iam_wildcard_resources_rule())
        self.register_rule(self._create_iam_admin_policy_rule())

        # Security Group Rules
        self.register_rule(self._create_sg_ssh_open_rule())
        self.register_rule(self._create_sg_rdp_open_rule())
        self.register_rule(self._create_sg_all_ports_open_rule())

        # EC2 Rules
        self.register_rule(self._create_ec2_public_ip_rule())
        self.register_rule(self._create_ec2_imdsv2_rule())

        # Lambda Rules
        self.register_rule(self._create_lambda_permission_rule())

        # RDS Rules
        self.register_rule(self._create_rds_public_access_rule())
        self.register_rule(self._create_rds_encryption_rule())

    def load_rules_from_directory(self, skills_dir: Path | str) -> int:
        """
        Load compliance rules from a skills directory.

        Reads SKILL.md files and compiles them into compliance rules.

        Args:
            skills_dir: Path to skills directory

        Returns:
            Number of rules loaded
        """
        path = Path(skills_dir)
        loaded = 0

        if not path.exists():
            return 0

        for skill_file in path.rglob("SKILL.md"):
            try:
                rule = self._compile_skill_to_rule(skill_file)
                if rule:
                    self.register_rule(rule)
                    loaded += 1
            except Exception:
                continue

        return loaded

    def scan(
        self,
        parse_results: list[ParseResult] | ParseResult,
    ) -> ComplianceReport:
        """
        Scan parsed IaC resources for compliance issues.

        Args:
            parse_results: Single or list of parse results

        Returns:
            ComplianceReport with findings
        """
        results = (
            [parse_results]
            if isinstance(parse_results, ParseResult)
            else parse_results
        )

        report = ComplianceReport(
            scan_timestamp=datetime.utcnow().isoformat(),
            files_scanned=len(results),
            resources_scanned=sum(r.resource_count for r in results),
        )

        # Track frameworks
        frameworks: set[str] = set()

        for parse_result in results:
            for resource in parse_result.resources:
                for rule in self._rules.values():
                    try:
                        finding = rule.check(resource)
                        if finding:
                            report.findings.append(finding)
                            frameworks.update(rule.frameworks)

                            if finding.status == ComplianceStatus.FAIL:
                                report.failed += 1
                            elif finding.status == ComplianceStatus.WARNING:
                                report.warnings += 1
                            elif finding.status == ComplianceStatus.ERROR:
                                report.errors += 1
                        elif self.include_passed:
                            # Create a passed finding
                            report.findings.append(
                                ComplianceFinding(
                                    rule_id=rule.rule_id,
                                    rule_name=rule.name,
                                    severity=rule.severity,
                                    status=ComplianceStatus.PASS,
                                    resource_type=resource.resource_type,
                                    resource_name=resource.resource_name,
                                    message=f"Resource passes {rule.name}",
                                    source_file=resource.source_file,
                                    line_number=resource.line_number,
                                    framework=rule.frameworks[0] if rule.frameworks else "",
                                )
                            )
                            report.passed += 1
                    except Exception as e:
                        if self.fail_on_error:
                            report.findings.append(
                                ComplianceFinding(
                                    rule_id=rule.rule_id,
                                    rule_name=rule.name,
                                    severity=Severity.INFO,
                                    status=ComplianceStatus.ERROR,
                                    resource_type=resource.resource_type,
                                    resource_name=resource.resource_name,
                                    message=f"Check failed: {e}",
                                    source_file=resource.source_file,
                                    framework="",
                                )
                            )
                            report.errors += 1

        report.frameworks = sorted(frameworks)
        return report

    def _compile_skill_to_rule(self, skill_path: Path) -> ComplianceRule | None:
        """
        Compile a SKILL.md file into a ComplianceRule.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            ComplianceRule if valid, None otherwise
        """
        try:
            content = skill_path.read_text(encoding="utf-8")

            # Extract frontmatter
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            frontmatter = parts[1]
            body = parts[2]

            # Parse YAML frontmatter
            import yaml
            metadata = yaml.safe_load(frontmatter)

            if not metadata:
                return None

            rule_id = metadata.get("ruleId", metadata.get("id", "unknown"))
            name = metadata.get("name", "Unknown Rule")
            description = metadata.get("description", "")
            severity_str = metadata.get("severity", "medium").lower()
            frameworks = metadata.get("frameworks", ["custom"])
            resource_types = metadata.get("resourceTypes", [])
            remediation = metadata.get("remediation", "")

            severity = Severity(severity_str) if severity_str in [s.value for s in Severity] else Severity.MEDIUM

            # Create check function from body
            check_function = self._create_check_function(body, metadata)

            return ComplianceRule(
                rule_id=rule_id,
                name=name,
                description=description,
                severity=severity,
                frameworks=frameworks if isinstance(frameworks, list) else [frameworks],
                resource_types=resource_types if isinstance(resource_types, list) else [resource_types],
                check_function=check_function,
                remediation=remediation,
                references=metadata.get("references", []),
            )

        except Exception:
            return None

    def _create_check_function(
        self,
        body: str,
        metadata: dict[str, Any],
    ) -> Callable[[ParsedResource], ComplianceFinding | None]:
        """
        Create a check function from skill body and metadata.

        Args:
            body: Skill body content
            metadata: Skill metadata

        Returns:
            Check function
        """
        # Extract check patterns from metadata
        check_patterns = metadata.get("checkPatterns", [])
        fail_conditions = metadata.get("failConditions", [])

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            """Check resource against patterns."""
            # Check fail conditions
            for condition in fail_conditions:
                if self._evaluate_condition(condition, resource):
                    return ComplianceFinding(
                        rule_id=metadata.get("ruleId", "unknown"),
                        rule_name=metadata.get("name", "Unknown"),
                        severity=Severity(
                            metadata.get("severity", "medium").lower()
                        ),
                        status=ComplianceStatus.FAIL,
                        resource_type=resource.resource_type,
                        resource_name=resource.resource_name,
                        message=condition.get("message", "Compliance check failed"),
                        remediation=metadata.get("remediation", ""),
                        source_file=resource.source_file,
                        line_number=resource.line_number,
                        framework=metadata.get("frameworks", [""])[0] if metadata.get("frameworks") else "",
                    )

            return None

        return check

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        resource: ParsedResource,
    ) -> bool:
        """
        Evaluate a condition against a resource.

        Args:
            condition: Condition to evaluate
            resource: Resource to check

        Returns:
            True if condition is met (failure), False otherwise
        """
        property_path = condition.get("property", "")
        operator = condition.get("operator", "equals")
        expected = condition.get("value")

        # Get property value
        value = self._get_nested_property(resource.properties, property_path)

        # Evaluate based on operator
        if operator == "equals":
            return value == expected
        elif operator == "not_equals":
            return value != expected
        elif operator == "contains":
            return expected in str(value) if value else False
        elif operator == "not_contains":
            return expected not in str(value) if value else True
        elif operator == "matches":
            return bool(re.search(expected, str(value))) if value else False
        elif operator == "exists":
            return value is not None
        elif operator == "not_exists":
            return value is None

        return False

    def _get_nested_property(
        self,
        obj: dict[str, Any],
        path: str,
    ) -> Any:
        """
        Get a nested property from a dictionary.

        Args:
            obj: Dictionary to search
            path: Dot-separated path (e.g., "Encryption.ServerSideEncryption")

        Returns:
            Property value or None
        """
        if not path:
            return None

        keys = path.split(".")
        value = obj

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    # =========================================================================
    # Default Rule Factories
    # =========================================================================

    def _create_s3_public_access_rule(self) -> ComplianceRule:
        """Create rule for S3 public access check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type != "aws_s3_bucket":
                return None

            acl = resource.properties.get("acl", "")
            if acl in ["public-read", "public-read-write", "website"]:
                return ComplianceFinding(
                    rule_id="S3-001",
                    rule_name="S3 Public Access",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket has public read ACL",
                    remediation="Use private ACL or bucket policies for controlled access",
                    source_file=resource.source_file,
                    line_number=resource.line_number,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="S3-001",
            name="S3 Public Access",
            description="Ensure S3 buckets are not publicly accessible",
            severity=Severity.HIGH,
            frameworks=["CIS", "NIST"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Use private ACL or bucket policies for controlled access",
            references=["CIS AWS Foundations Benchmark 2.1.1"],
        )

    def _create_s3_encryption_rule(self) -> ComplianceRule:
        """Create rule for S3 encryption check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type != "aws_s3_bucket":
                return None

            # Check if encryption is configured
            has_encryption = resource.properties.get("encryption") is not None

            if not has_encryption:
                return ComplianceFinding(
                    rule_id="S3-002",
                    rule_name="S3 Encryption",
                    severity=Severity.MEDIUM,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket lacks server-side encryption configuration",
                    remediation="Add aws_s3_bucket_server_side_encryption_configuration resource",
                    source_file=resource.source_file,
                    line_number=resource.line_number,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="S3-002",
            name="S3 Encryption",
            description="Ensure S3 buckets have encryption enabled",
            severity=Severity.MEDIUM,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Add server-side encryption configuration",
            references=["CIS AWS Foundations Benchmark 2.1.2"],
        )

    def _create_s3_versioning_rule(self) -> ComplianceRule:
        """Create rule for S3 versioning check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type != "aws_s3_bucket":
                return None

            versioning = resource.properties.get("versioning", {})
            if isinstance(versioning, dict):
                enabled = versioning.get("enabled", False)
            else:
                enabled = versioning == "Enabled"

            if not enabled:
                return ComplianceFinding(
                    rule_id="S3-003",
                    rule_name="S3 Versioning",
                    severity=Severity.LOW,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket versioning is not enabled",
                    remediation="Enable bucket versioning for data protection",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="S3-003",
            name="S3 Versioning",
            description="Ensure S3 bucket versioning is enabled",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Enable bucket versioning",
        )

    def _create_s3_logging_rule(self) -> ComplianceRule:
        """Create rule for S3 access logging check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type != "aws_s3_bucket":
                return None

            logging = resource.properties.get("logging")
            if not logging:
                return ComplianceFinding(
                    rule_id="S3-004",
                    rule_name="S3 Access Logging",
                    severity=Severity.LOW,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket access logging is not enabled",
                    remediation="Enable server access logging for audit trail",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="S3-004",
            name="S3 Access Logging",
            description="Ensure S3 bucket access logging is enabled",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Enable server access logging",
        )

    def _create_iam_wildcard_actions_rule(self) -> ComplianceRule:
        """Create rule for IAM wildcard actions check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"]:
                return None

            policy = resource.properties.get("policy", "")
            if isinstance(policy, str):
                # Check for wildcard actions in JSON string
                if '"Action"' in policy and '"*"' in policy:
                    # More specific check for action wildcard
                    if re.search(r'"Action"\s*:\s*\[\s*"\*"\s*\]', policy):
                        return ComplianceFinding(
                            rule_id="IAM-001",
                            rule_name="IAM Wildcard Actions",
                            severity=Severity.HIGH,
                            status=ComplianceStatus.FAIL,
                            resource_type=resource.resource_type,
                            resource_name=resource.resource_name,
                            message="IAM policy uses wildcard (*) actions",
                            remediation="Scope down to specific actions required by the role",
                            source_file=resource.source_file,
                            line_number=resource.line_number,
                            framework="CIS",
                        )
            return None

        return ComplianceRule(
            rule_id="IAM-001",
            name="IAM Wildcard Actions",
            description="Ensure IAM policies do not use wildcard actions",
            severity=Severity.HIGH,
            frameworks=["CIS", "NIST"],
            resource_types=["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"],
            check_function=check,
            remediation="Scope down to specific actions",
            references=["CIS AWS Foundations Benchmark 1.16"],
        )

    def _create_iam_wildcard_resources_rule(self) -> ComplianceRule:
        """Create rule for IAM wildcard resources check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"]:
                return None

            policy = resource.properties.get("policy", "")
            if isinstance(policy, str):
                # Check for wildcard resources
                if re.search(r'"Resource"\s*:\s*"\*"', policy):
                    return ComplianceFinding(
                        rule_id="IAM-002",
                        rule_name="IAM Wildcard Resources",
                        severity=Severity.MEDIUM,
                        status=ComplianceStatus.WARNING,
                        resource_type=resource.resource_type,
                        resource_name=resource.resource_name,
                        message="IAM policy uses wildcard (*) resource",
                        remediation="Scope down to specific resources",
                        source_file=resource.source_file,
                        framework="CIS",
                    )
            return None

        return ComplianceRule(
            rule_id="IAM-002",
            name="IAM Wildcard Resources",
            description="Ensure IAM policies do not use wildcard resources",
            severity=Severity.MEDIUM,
            frameworks=["CIS"],
            resource_types=["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"],
            check_function=check,
            remediation="Scope down to specific resources",
        )

    def _create_iam_admin_policy_rule(self) -> ComplianceRule:
        """Create rule for IAM AdministratorAccess policy check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"]:
                return None

            policy = resource.properties.get("policy", "")
            if isinstance(policy, str):
                # Check for AdministratorAccess-like patterns
                if "AdministratorAccess" in policy or (
                    '"Action"' in policy and '"*"' in policy and '"Resource"' in policy and '"*"' in policy
                ):
                    return ComplianceFinding(
                        rule_id="IAM-003",
                        rule_name="IAM Administrator Access",
                        severity=Severity.HIGH,
                        status=ComplianceStatus.FAIL,
                        resource_type=resource.resource_type,
                        resource_name=resource.resource_name,
                        message="IAM policy grants administrator-level access",
                        remediation="Implement least-privilege access with specific permissions",
                        source_file=resource.source_file,
                        framework="CIS",
                    )
            return None

        return ComplianceRule(
            rule_id="IAM-003",
            name="IAM Administrator Access",
            description="Ensure IAM policies do not grant administrator access",
            severity=Severity.HIGH,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_iam_role_policy", "aws_iam_policy", "AWS::IAM::Policy"],
            check_function=check,
            remediation="Implement least-privilege access",
        )

    def _create_sg_ssh_open_rule(self) -> ComplianceRule:
        """Create rule for SSH open to world check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"]:
                return None

            port = resource.properties.get("from_port", resource.properties.get("FromPort"))
            cidr = resource.properties.get("cidr_blocks", resource.properties.get("CidrIp"))

            if port in [22, "22"] and cidr in ["0.0.0.0/0", ["0.0.0.0/0"]]:
                return ComplianceFinding(
                    rule_id="SG-001",
                    rule_name="SSH Open to World",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="SSH (port 22) is open to the world (0.0.0.0/0)",
                    remediation="Restrict SSH access to known IP ranges or use AWS Systems Manager",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="SG-001",
            name="SSH Open to World",
            description="Ensure SSH is not open to the world",
            severity=Severity.HIGH,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"],
            check_function=check,
            remediation="Restrict SSH access to known IP ranges",
        )

    def _create_sg_rdp_open_rule(self) -> ComplianceRule:
        """Create rule for RDP open to world check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"]:
                return None

            port = resource.properties.get("from_port", resource.properties.get("FromPort"))
            cidr = resource.properties.get("cidr_blocks", resource.properties.get("CidrIp"))

            if port in [3389, "3389"] and cidr in ["0.0.0.0/0", ["0.0.0.0/0"]]:
                return ComplianceFinding(
                    rule_id="SG-002",
                    rule_name="RDP Open to World",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="RDP (port 3389) is open to the world (0.0.0.0/0)",
                    remediation="Restrict RDP access to known IP ranges",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="SG-002",
            name="RDP Open to World",
            description="Ensure RDP is not open to the world",
            severity=Severity.HIGH,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"],
            check_function=check,
            remediation="Restrict RDP access to known IP ranges",
        )

    def _create_sg_all_ports_open_rule(self) -> ComplianceRule:
        """Create rule for all ports open check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"]:
                return None

            port = resource.properties.get("from_port", resource.properties.get("FromPort"))
            cidr = resource.properties.get("cidr_blocks", resource.properties.get("CidrIp"))

            # All ports (-1 or 0-65535) open to world
            if (port in [-1, 0, "-1", None] or port == "") and cidr in ["0.0.0.0/0", ["0.0.0.0/0"]]:
                return ComplianceFinding(
                    rule_id="SG-003",
                    rule_name="All Ports Open",
                    severity=Severity.CRITICAL,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="All ports are open to the world (0.0.0.0/0)",
                    remediation="Restrict to specific ports required by the application",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="SG-003",
            name="All Ports Open",
            description="Ensure not all ports are open to the world",
            severity=Severity.CRITICAL,
            frameworks=["CIS"],
            resource_types=["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"],
            check_function=check,
            remediation="Restrict to specific ports",
        )

    def _create_ec2_public_ip_rule(self) -> ComplianceRule:
        """Create rule for EC2 public IP check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_instance", "AWS::EC2::Instance"]:
                return None

            associate_public_ip = resource.properties.get("associate_public_ip_address")
            if associate_public_ip is True:
                return ComplianceFinding(
                    rule_id="EC2-001",
                    rule_name="EC2 Public IP",
                    severity=Severity.MEDIUM,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="EC2 instance has a public IP address",
                    remediation="Use private subnets with NAT gateway for production workloads",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="EC2-001",
            name="EC2 Public IP",
            description="Ensure EC2 instances do not have public IPs in production",
            severity=Severity.MEDIUM,
            frameworks=["CIS"],
            resource_types=["aws_instance", "AWS::EC2::Instance"],
            check_function=check,
            remediation="Use private subnets with NAT gateway",
        )

    def _create_ec2_imdsv2_rule(self) -> ComplianceRule:
        """Create rule for EC2 IMDSv2 requirement check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_instance", "AWS::EC2::Instance"]:
                return None

            metadata_options = resource.properties.get("metadata_options", {})
            if isinstance(metadata_options, dict):
                http_tokens = metadata_options.get("http_tokens", "optional")
            else:
                http_tokens = "optional"

            if http_tokens != "required":
                return ComplianceFinding(
                    rule_id="EC2-002",
                    rule_name="EC2 IMDSv2 Required",
                    severity=Severity.MEDIUM,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="EC2 instance does not require IMDSv2",
                    remediation="Set http_tokens to 'required' in metadata_options",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="EC2-002",
            name="EC2 IMDSv2 Required",
            description="Ensure EC2 instances require IMDSv2",
            severity=Severity.MEDIUM,
            frameworks=["CIS"],
            resource_types=["aws_instance", "AWS::EC2::Instance"],
            check_function=check,
            remediation="Configure IMDSv2 requirement",
        )

    def _create_lambda_permission_rule(self) -> ComplianceRule:
        """Create rule for Lambda permission check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_lambda_permission", "AWS::Lambda::Permission"]:
                return None

            principal = resource.properties.get("principal", resource.properties.get("Principal"))
            source_arn = resource.properties.get("source_arn", resource.properties.get("SourceArn"))

            if principal == "*" and not source_arn:
                return ComplianceFinding(
                    rule_id="LAMBDA-001",
                    rule_name="Lambda Public Permission",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="Lambda function has public invoke permission",
                    remediation="Restrict invocation to specific principals or use source ARN condition",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="LAMBDA-001",
            name="Lambda Public Permission",
            description="Ensure Lambda functions are not publicly invocable",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_lambda_permission", "AWS::Lambda::Permission"],
            check_function=check,
            remediation="Restrict invocation to specific principals",
        )

    def _create_rds_public_access_rule(self) -> ComplianceRule:
        """Create rule for RDS public access check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_db_instance", "AWS::RDS::DBInstance"]:
                return None

            publicly_accessible = resource.properties.get("publicly_accessible", False)

            if publicly_accessible:
                return ComplianceFinding(
                    rule_id="RDS-001",
                    rule_name="RDS Public Access",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="RDS instance is publicly accessible",
                    remediation="Set publicly_accessible to false and use private subnets",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="RDS-001",
            name="RDS Public Access",
            description="Ensure RDS instances are not publicly accessible",
            severity=Severity.HIGH,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_db_instance", "AWS::RDS::DBInstance"],
            check_function=check,
            remediation="Disable public accessibility",
        )

    def _create_rds_encryption_rule(self) -> ComplianceRule:
        """Create rule for RDS encryption check."""

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_db_instance", "AWS::RDS::DBInstance"]:
                return None

            storage_encrypted = resource.properties.get("storage_encrypted", False)

            if not storage_encrypted:
                return ComplianceFinding(
                    rule_id="RDS-002",
                    rule_name="RDS Encryption",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="RDS instance storage is not encrypted",
                    remediation="Enable storage encryption using KMS",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="RDS-002",
            name="RDS Encryption",
            description="Ensure RDS instances have encryption at rest",
            severity=Severity.HIGH,
            frameworks=["CIS", "PCI-DSS"],
            resource_types=["aws_db_instance", "AWS::RDS::DBInstance"],
            check_function=check,
            remediation="Enable storage encryption",
        )
