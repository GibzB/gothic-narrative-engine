"""
Cloud Compliance Auditor - IaC scanning and CIS benchmark validation.

Enterprise Cloud Compliance Auditor for AWS infrastructure-as-code.
Supports Terraform, AWS CDK, and CloudFormation templates.

Implements:
- Task 3.2: IaC Parser - Parse AWS CDK/Terraform templates
- Task 3.3: Compliance Engine - Load and execute compliance skills
- Task 3.4: CIS Validator - Validate against CIS AWS Benchmarks
- Task 3.5: PreToolUse Gate - Security hook for blocking dangerous operations
"""

__version__ = "0.1.0"

from cloud_compliance.iac_parser import (
    IaCParser,
    ParseResult,
    ParsedResource,
)

from cloud_compliance.compliance_engine import (
    ComplianceEngine,
    ComplianceReport,
    ComplianceFinding,
    ComplianceRule,
    ComplianceStatus,
    Severity,
)

from cloud_compliance.cis_validator import (
    CISValidator,
    CISComplianceReport,
    CISControl,
    CISControlCategory,
)

from cloud_compliance.pretooluse_gate import (
    PreToolUseGate,
    GateAction,
    GateDecision,
    BlockedPattern,
)

__all__ = [
    # Parser
    "IaCParser",
    "ParseResult",
    "ParsedResource",
    # Compliance Engine
    "ComplianceEngine",
    "ComplianceReport",
    "ComplianceFinding",
    "ComplianceRule",
    "ComplianceStatus",
    "Severity",
    # CIS Validator
    "CISValidator",
    "CISComplianceReport",
    "CISControl",
    "CISControlCategory",
    # PreToolUse Gate
    "PreToolUseGate",
    "GateAction",
    "GateDecision",
    "BlockedPattern",
]
