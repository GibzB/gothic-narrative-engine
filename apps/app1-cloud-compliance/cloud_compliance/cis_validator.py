"""
CIS Validator - Validate against CIS AWS Benchmarks.

Implements CIS AWS Foundations Benchmark controls for automated
compliance validation of IaC templates.

Task 3.4: Implement CIS Validator
Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from cloud_compliance.compliance_engine import (
    ComplianceEngine,
    ComplianceFinding,
    ComplianceReport,
    ComplianceStatus,
    Severity,
    ComplianceRule,
)
from cloud_compliance.iac_parser import ParseResult


class CISControlCategory(str, Enum):
    """CIS control categories."""
    IDENTITY_ACCESS_MANAGEMENT = "identity_access_management"
    STORAGE = "storage"
    LOGGING = "logging"
    MONITORING = "monitoring"
    NETWORKING = "networking"
    DATABASE = "database"


@dataclass
class CISControl:
    """A CIS benchmark control definition."""

    control_id: str
    title: str
    description: str
    category: CISControlCategory
    severity: Severity
    remediation: str
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "controlId": self.control_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "remediation": self.remediation,
            "references": self.references,
        }


class CISValidator:
    """
    Validates IaC templates against CIS AWS Foundations Benchmark.

    Implements automated checks for CIS controls related to:
    - IAM (Identity and Access Management)
    - Storage (S3)
    - Logging (CloudTrail, CloudWatch)
    - Monitoring (CloudWatch Alarms)
    - Networking (VPC, Security Groups)
    - Database (RDS)

    Task 3.4: CIS Validator
    Validates: Requirements 3.1, 3.2, 3.3, 3.4

    Example:
        >>> validator = CISValidator()
        >>> report = validator.validate(parse_results)
        >>> report.is_compliant
        False
    """

    def __init__(
        self,
        *,
        cis_level: int = 1,  # CIS Level 1 or Level 2
        include_passed: bool = True,
    ) -> None:
        """
        Initialize the CIS validator.

        Args:
            cis_level: CIS benchmark level (1 or 2)
            include_passed: Include passed controls in report
        """
        self.cis_level = cis_level
        self.include_passed = include_passed
        self._engine = ComplianceEngine(include_passed=include_passed)
        self._load_cis_rules()

    def _load_cis_rules(self) -> None:
        """Load CIS-specific compliance rules."""
        # IAM Controls
        self._engine.register_rule(self._create_cis_1_16_rule())  # IAM policies
        self._engine.register_rule(self._create_cis_1_22_rule())  # Unused credentials

        # Storage Controls
        self._engine.register_rule(self._create_cis_2_1_1_rule())  # S3 public access
        self._engine.register_rule(self._create_cis_2_1_2_rule())  # S3 encryption
        self._engine.register_rule(self._create_cis_2_1_3_rule())  # S3 versioning
        self._engine.register_rule(self._create_cis_2_1_4_rule())  # S3 logging

        # Logging Controls
        self._engine.register_rule(self._create_cis_2_3_1_rule())  # CloudTrail enabled
        self._engine.register_rule(self._create_cis_2_3_2_rule())  # CloudTrail encryption

        # Networking Controls
        self._engine.register_rule(self._create_cis_5_1_rule())  # SSH restriction
        self._engine.register_rule(self._create_cis_5_2_rule())  # RDP restriction

        # Database Controls
        self._engine.register_rule(self._create_cis_6_1_rule())  # RDS encryption
        self._engine.register_rule(self._create_cis_6_2_rule())  # RDS public access

    def validate(
        self,
        parse_results: list[ParseResult] | ParseResult,
    ) -> CISComplianceReport:
        """
        Validate IaC against CIS AWS Benchmarks.

        Args:
            parse_results: Parsed IaC resources

        Returns:
            CISComplianceReport with findings
        """
        results = (
            [parse_results]
            if isinstance(parse_results, ParseResult)
            else parse_results
        )

        # Run compliance scan
        base_report = self._engine.scan(results)

        # Convert to CIS-specific report
        return CISComplianceReport(
            base_report=base_report,
            cis_level=self.cis_level,
            controls=self._get_implemented_controls(),
        )

    def _get_implemented_controls(self) -> list[CISControl]:
        """Get list of implemented CIS controls."""
        return [
            CISControl(
                control_id="1.16",
                title="Ensure IAM policies are attached only to groups or roles",
                description="IAM policies should be attached to groups or roles, not directly to users.",
                category=CISControlCategory.IDENTITY_ACCESS_MANAGEMENT,
                severity=Severity.LOW,
                remediation="Attach policies to groups and assign users to groups.",
                references=["CIS AWS Foundations Benchmark 1.16"],
            ),
            CISControl(
                control_id="2.1.1",
                title="Ensure S3 buckets are not publicly accessible",
                description="S3 buckets should not have public access policies or ACLs.",
                category=CISControlCategory.STORAGE,
                severity=Severity.HIGH,
                remediation="Configure S3 bucket access controls to restrict public access.",
                references=["CIS AWS Foundations Benchmark 2.1.1"],
            ),
            CISControl(
                control_id="2.1.2",
                title="Ensure S3 buckets have encryption enabled",
                description="S3 buckets should have server-side encryption enabled.",
                category=CISControlCategory.STORAGE,
                severity=Severity.MEDIUM,
                remediation="Enable default encryption on S3 buckets.",
                references=["CIS AWS Foundations Benchmark 2.1.2"],
            ),
            CISControl(
                control_id="2.1.3",
                title="Ensure S3 bucket versioning is enabled",
                description="S3 buckets should have versioning enabled for data protection.",
                category=CISControlCategory.STORAGE,
                severity=Severity.LOW,
                remediation="Enable versioning on S3 buckets.",
                references=["CIS AWS Foundations Benchmark 2.1.3"],
            ),
            CISControl(
                control_id="2.1.4",
                title="Ensure S3 bucket logging is enabled",
                description="S3 buckets should have server access logging enabled.",
                category=CISControlCategory.STORAGE,
                severity=Severity.LOW,
                remediation="Configure S3 bucket access logging.",
                references=["CIS AWS Foundations Benchmark 2.1.4"],
            ),
            CISControl(
                control_id="2.3.1",
                title="Ensure CloudTrail is enabled in all regions",
                description="CloudTrail should be enabled for all regions.",
                category=CISControlCategory.LOGGING,
                severity=Severity.HIGH,
                remediation="Enable CloudTrail with multi-region trail.",
                references=["CIS AWS Foundations Benchmark 2.3.1"],
            ),
            CISControl(
                control_id="5.1",
                title="Ensure no security groups allow ingress from 0.0.0.0/0 to port 22",
                description="SSH access should not be open to the world.",
                category=CISControlCategory.NETWORKING,
                severity=Severity.HIGH,
                remediation="Restrict SSH access to known IP ranges.",
                references=["CIS AWS Foundations Benchmark 5.1"],
            ),
            CISControl(
                control_id="5.2",
                title="Ensure no security groups allow ingress from 0.0.0.0/0 to port 3389",
                description="RDP access should not be open to the world.",
                category=CISControlCategory.NETWORKING,
                severity=Severity.HIGH,
                remediation="Restrict RDP access to known IP ranges.",
                references=["CIS AWS Foundations Benchmark 5.2"],
            ),
            CISControl(
                control_id="6.1",
                title="Ensure RDS instances have encryption at rest enabled",
                description="RDS instances should have storage encryption enabled.",
                category=CISControlCategory.DATABASE,
                severity=Severity.HIGH,
                remediation="Enable storage encryption on RDS instances.",
                references=["CIS AWS Foundations Benchmark 6.1"],
            ),
            CISControl(
                control_id="6.2",
                title="Ensure RDS instances are not publicly accessible",
                description="RDS instances should not be publicly accessible.",
                category=CISControlCategory.DATABASE,
                severity=Severity.HIGH,
                remediation="Set publicly_accessible to false.",
                references=["CIS AWS Foundations Benchmark 6.2"],
            ),
        ]

    # =========================================================================
    # CIS Rule Factories
    # =========================================================================

    def _create_cis_1_16_rule(self) -> ComplianceRule:
        """Create CIS 1.16 - IAM policies attached to groups/roles."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type != "aws_iam_user_policy":
                return None

            return ComplianceFinding(
                rule_id="CIS-1.16",
                rule_name="IAM Policy Attachment",
                severity=Severity.LOW,
                status=ComplianceStatus.WARNING,
                resource_type=resource.resource_type,
                resource_name=resource.resource_name,
                message="IAM policy attached directly to user instead of group/role",
                remediation="Attach policies to groups or roles, then assign users to groups",
                source_file=resource.source_file,
                line_number=resource.line_number,
                framework="CIS",
            )

        return ComplianceRule(
            rule_id="CIS-1.16",
            name="IAM Policy Attachment",
            description="Ensure IAM policies are attached only to groups or roles",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=["aws_iam_user_policy", "AWS::IAM::UserPolicy"],
            check_function=check,
            remediation="Attach policies to groups or roles",
            references=["CIS AWS Foundations Benchmark 1.16"],
        )

    def _create_cis_1_22_rule(self) -> ComplianceRule:
        """Create CIS 1.22 - Unused credentials check."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            # This is a runtime check, not IaC check
            # We can only check if the user is created
            return None

        return ComplianceRule(
            rule_id="CIS-1.22",
            name="Unused IAM Credentials",
            description="Ensure unused IAM credentials are removed",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=[],  # Runtime check only
            check_function=check,
            remediation="Remove unused IAM credentials",
            references=["CIS AWS Foundations Benchmark 1.22"],
        )

    def _create_cis_2_1_1_rule(self) -> ComplianceRule:
        """Create CIS 2.1.1 - S3 public access."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_s3_bucket", "AWS::S3::Bucket"]:
                return None

            acl = resource.properties.get("acl", "")
            if acl in ["public-read", "public-read-write", "website"]:
                return ComplianceFinding(
                    rule_id="CIS-2.1.1",
                    rule_name="S3 Public Access",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket is publicly accessible",
                    remediation="Configure S3 bucket access controls to restrict public access",
                    source_file=resource.source_file,
                    line_number=resource.line_number,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.1.1",
            name="S3 Public Access",
            description="Ensure S3 buckets are not publicly accessible",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Restrict S3 bucket access",
            references=["CIS AWS Foundations Benchmark 2.1.1"],
        )

    def _create_cis_2_1_2_rule(self) -> ComplianceRule:
        """Create CIS 2.1.2 - S3 encryption."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_s3_bucket", "AWS::S3::Bucket"]:
                return None

            encryption = resource.properties.get("encryption")
            server_side_encryption = resource.properties.get("server_side_encryption_configuration")

            if not encryption and not server_side_encryption:
                return ComplianceFinding(
                    rule_id="CIS-2.1.2",
                    rule_name="S3 Encryption",
                    severity=Severity.MEDIUM,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket does not have server-side encryption enabled",
                    remediation="Enable default encryption on S3 buckets",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.1.2",
            name="S3 Encryption",
            description="Ensure S3 buckets have encryption enabled",
            severity=Severity.MEDIUM,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Enable S3 encryption",
            references=["CIS AWS Foundations Benchmark 2.1.2"],
        )

    def _create_cis_2_1_3_rule(self) -> ComplianceRule:
        """Create CIS 2.1.3 - S3 versioning."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_s3_bucket", "AWS::S3::Bucket"]:
                return None

            versioning = resource.properties.get("versioning", {})
            if isinstance(versioning, dict):
                enabled = versioning.get("enabled", False)
            else:
                enabled = str(versioning).lower() == "enabled"

            if not enabled:
                return ComplianceFinding(
                    rule_id="CIS-2.1.3",
                    rule_name="S3 Versioning",
                    severity=Severity.LOW,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket versioning is not enabled",
                    remediation="Enable versioning on S3 buckets",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.1.3",
            name="S3 Versioning",
            description="Ensure S3 bucket versioning is enabled",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Enable S3 versioning",
            references=["CIS AWS Foundations Benchmark 2.1.3"],
        )

    def _create_cis_2_1_4_rule(self) -> ComplianceRule:
        """Create CIS 2.1.4 - S3 logging."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_s3_bucket", "AWS::S3::Bucket"]:
                return None

            logging = resource.properties.get("logging")
            if not logging:
                return ComplianceFinding(
                    rule_id="CIS-2.1.4",
                    rule_name="S3 Logging",
                    severity=Severity.LOW,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="S3 bucket server access logging is not enabled",
                    remediation="Configure S3 bucket access logging",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.1.4",
            name="S3 Logging",
            description="Ensure S3 bucket logging is enabled",
            severity=Severity.LOW,
            frameworks=["CIS"],
            resource_types=["aws_s3_bucket", "AWS::S3::Bucket"],
            check_function=check,
            remediation="Enable S3 logging",
            references=["CIS AWS Foundations Benchmark 2.1.4"],
        )

    def _create_cis_2_3_1_rule(self) -> ComplianceRule:
        """Create CIS 2.3.1 - CloudTrail enabled."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_cloudtrail", "AWS::CloudTrail::Trail"]:
                return None

            is_multi_region = resource.properties.get("is_multi_region_trail", False)
            if not is_multi_region:
                return ComplianceFinding(
                    rule_id="CIS-2.3.1",
                    rule_name="CloudTrail Multi-Region",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="CloudTrail is not configured for multi-region",
                    remediation="Enable multi-region trail",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.3.1",
            name="CloudTrail Multi-Region",
            description="Ensure CloudTrail is enabled in all regions",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_cloudtrail", "AWS::CloudTrail::Trail"],
            check_function=check,
            remediation="Enable multi-region CloudTrail",
            references=["CIS AWS Foundations Benchmark 2.3.1"],
        )

    def _create_cis_2_3_2_rule(self) -> ComplianceRule:
        """Create CIS 2.3.2 - CloudTrail encryption."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_cloudtrail", "AWS::CloudTrail::Trail"]:
                return None

            kms_key = resource.properties.get("kms_key_id")
            if not kms_key:
                return ComplianceFinding(
                    rule_id="CIS-2.3.2",
                    rule_name="CloudTrail Encryption",
                    severity=Severity.MEDIUM,
                    status=ComplianceStatus.WARNING,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="CloudTrail logs are not encrypted with KMS",
                    remediation="Enable KMS encryption for CloudTrail logs",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-2.3.2",
            name="CloudTrail Encryption",
            description="Ensure CloudTrail log file encryption is enabled",
            severity=Severity.MEDIUM,
            frameworks=["CIS"],
            resource_types=["aws_cloudtrail", "AWS::CloudTrail::Trail"],
            check_function=check,
            remediation="Enable KMS encryption",
            references=["CIS AWS Foundations Benchmark 2.3.2"],
        )

    def _create_cis_5_1_rule(self) -> ComplianceRule:
        """Create CIS 5.1 - SSH restriction."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"]:
                return None

            port = resource.properties.get("from_port", resource.properties.get("FromPort"))
            cidr = resource.properties.get("cidr_blocks", resource.properties.get("CidrIp"))

            if port in [22, "22"] and cidr in ["0.0.0.0/0", ["0.0.0.0/0"]]:
                return ComplianceFinding(
                    rule_id="CIS-5.1",
                    rule_name="SSH Open to World",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="Security group allows SSH from 0.0.0.0/0",
                    remediation="Restrict SSH access to known IP ranges",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-5.1",
            name="SSH Restriction",
            description="Ensure no security groups allow SSH from 0.0.0.0/0",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"],
            check_function=check,
            remediation="Restrict SSH access",
            references=["CIS AWS Foundations Benchmark 5.1"],
        )

    def _create_cis_5_2_rule(self) -> ComplianceRule:
        """Create CIS 5.2 - RDP restriction."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"]:
                return None

            port = resource.properties.get("from_port", resource.properties.get("FromPort"))
            cidr = resource.properties.get("cidr_blocks", resource.properties.get("CidrIp"))

            if port in [3389, "3389"] and cidr in ["0.0.0.0/0", ["0.0.0.0/0"]]:
                return ComplianceFinding(
                    rule_id="CIS-5.2",
                    rule_name="RDP Open to World",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="Security group allows RDP from 0.0.0.0/0",
                    remediation="Restrict RDP access to known IP ranges",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-5.2",
            name="RDP Restriction",
            description="Ensure no security groups allow RDP from 0.0.0.0/0",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_security_group_rule", "AWS::EC2::SecurityGroupIngress"],
            check_function=check,
            remediation="Restrict RDP access",
            references=["CIS AWS Foundations Benchmark 5.2"],
        )

    def _create_cis_6_1_rule(self) -> ComplianceRule:
        """Create CIS 6.1 - RDS encryption."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_db_instance", "AWS::RDS::DBInstance"]:
                return None

            storage_encrypted = resource.properties.get("storage_encrypted", False)

            if not storage_encrypted:
                return ComplianceFinding(
                    rule_id="CIS-6.1",
                    rule_name="RDS Encryption",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="RDS instance does not have storage encryption enabled",
                    remediation="Enable storage encryption on RDS instances",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-6.1",
            name="RDS Encryption",
            description="Ensure RDS instances have encryption at rest enabled",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_db_instance", "AWS::RDS::DBInstance"],
            check_function=check,
            remediation="Enable RDS encryption",
            references=["CIS AWS Foundations Benchmark 6.1"],
        )

    def _create_cis_6_2_rule(self) -> ComplianceRule:
        """Create CIS 6.2 - RDS public access."""
        from cloud_compliance.iac_parser import ParsedResource

        def check(resource: ParsedResource) -> ComplianceFinding | None:
            if resource.resource_type not in ["aws_db_instance", "AWS::RDS::DBInstance"]:
                return None

            publicly_accessible = resource.properties.get("publicly_accessible", False)

            if publicly_accessible:
                return ComplianceFinding(
                    rule_id="CIS-6.2",
                    rule_name="RDS Public Access",
                    severity=Severity.HIGH,
                    status=ComplianceStatus.FAIL,
                    resource_type=resource.resource_type,
                    resource_name=resource.resource_name,
                    message="RDS instance is publicly accessible",
                    remediation="Set publicly_accessible to false",
                    source_file=resource.source_file,
                    framework="CIS",
                )
            return None

        return ComplianceRule(
            rule_id="CIS-6.2",
            name="RDS Public Access",
            description="Ensure RDS instances are not publicly accessible",
            severity=Severity.HIGH,
            frameworks=["CIS"],
            resource_types=["aws_db_instance", "AWS::RDS::DBInstance"],
            check_function=check,
            remediation="Disable public accessibility",
            references=["CIS AWS Foundations Benchmark 6.2"],
        )


@dataclass
class CISComplianceReport:
    """CIS-specific compliance report."""

    base_report: ComplianceReport
    cis_level: int
    controls: list[CISControl]

    @property
    def is_cis_compliant(self) -> bool:
        """Check if CIS compliant."""
        return self.base_report.is_compliant

    @property
    def cis_findings(self) -> list[ComplianceFinding]:
        """Get CIS-specific findings."""
        return [f for f in self.base_report.findings if f.framework == "CIS"]

    def get_control_status(self, control_id: str) -> ComplianceStatus:
        """Get status for a specific CIS control."""
        for finding in self.cis_findings:
            if finding.rule_id == control_id or f"CIS-{control_id}" == finding.rule_id:
                return finding.status
        return ComplianceStatus.SKIPPED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "cisLevel": self.cis_level,
            "isCisCompliant": self.is_cis_compliant,
            "controls": [c.to_dict() for c in self.controls],
            "findings": [f.to_dict() for f in self.cis_findings],
            "summary": self.base_report.to_dict()["summary"],
            "baseReport": self.base_report.to_dict(),
        }
