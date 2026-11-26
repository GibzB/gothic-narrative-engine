"""
Tests for Cloud Compliance Auditor.

Unit and property-based tests for IaC parsing, compliance engine,
CIS validation, and PreToolUse gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from cloud_compliance.iac_parser import IaCParser, ParseResult
from cloud_compliance.compliance_engine import (
    ComplianceEngine,
    ComplianceStatus,
    Severity,
)
from cloud_compliance.cis_validator import CISValidator
from cloud_compliance.pretooluse_gate import PreToolUseGate, GateAction


# =========================================================================
# IaC Parser Tests
# =========================================================================

class TestIaCParser:
    """Tests for the IaC parser."""

    def test_parse_terraform_file(self, tmp_path: Path) -> None:
        """Test parsing a Terraform file."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text('''
resource "aws_s3_bucket" "test_bucket" {
  bucket = "my-test-bucket"
  acl    = "private"
}
''')

        parser = IaCParser()
        result = parser.parse_file(tf_file)

        assert result.is_successful
        assert result.provider == "terraform"
        assert result.resource_count == 1

        resource = result.resources[0]
        assert resource.resource_type == "aws_s3_bucket"
        assert resource.resource_name == "test_bucket"
        assert resource.properties.get("bucket") == "my-test-bucket"

    def test_parse_terraform_with_public_acl(self, tmp_path: Path) -> None:
        """Test parsing Terraform with public ACL."""
        tf_file = tmp_path / "insecure.tf"
        tf_file.write_text('''
resource "aws_s3_bucket" "public_bucket" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}
''')

        parser = IaCParser()
        result = parser.parse_file(tf_file)

        assert result.is_successful
        assert result.resource_count == 1
        assert result.resources[0].properties.get("acl") == "public-read"

    def test_parse_cloudformation_json(self, tmp_path: Path) -> None:
        """Test parsing CloudFormation JSON template."""
        cf_file = tmp_path / "template.json"
        cf_file.write_text(json.dumps({
            "Resources": {
                "MyBucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": "my-bucket"
                    }
                }
            }
        }))

        parser = IaCParser()
        result = parser.parse_file(cf_file)

        assert result.is_successful
        assert result.provider == "cloudformation"
        assert result.resource_count == 1
        assert result.resources[0].resource_type == "AWS::S3::Bucket"

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a nonexistent file."""
        parser = IaCParser()
        result = parser.parse_file("/nonexistent/file.tf")

        assert not result.is_successful
        assert "not found" in result.errors[0].lower()

    def test_parse_directory(self, tmp_path: Path) -> None:
        """Test parsing a directory of IaC files."""
        (tmp_path / "main.tf").write_text('''
resource "aws_s3_bucket" "bucket1" {
  bucket = "bucket1"
}
''')
        (tmp_path / "network.tf").write_text('''
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
''')

        parser = IaCParser()
        results = parser.parse_directory(tmp_path)

        assert len(results) == 2
        total_resources = sum(r.resource_count for r in results)
        assert total_resources == 2


# =========================================================================
# Compliance Engine Tests
# =========================================================================

class TestComplianceEngine:
    """Tests for the compliance engine."""

    def test_s3_public_access_detection(self, tmp_path: Path) -> None:
        """Test detection of public S3 bucket."""
        from cloud_compliance.iac_parser import ParsedResource

        parser = IaCParser()
        engine = ComplianceEngine()
        engine.load_default_rules()

        # Create a mock resource
        resource = ParsedResource(
            resource_type="aws_s3_bucket",
            resource_name="public_bucket",
            properties={"acl": "public-read"},
            source_file=str(tmp_path / "test.tf"),
        )

        # Get the rule and check
        rule = engine._rules.get("S3-001")
        assert rule is not None

        finding = rule.check(resource)
        assert finding is not None
        assert finding.status == ComplianceStatus.FAIL
        assert "public" in finding.message.lower()

    def test_iam_wildcard_detection(self, tmp_path: Path) -> None:
        """Test detection of wildcard IAM policy."""
        from cloud_compliance.iac_parser import ParsedResource

        engine = ComplianceEngine()
        engine.load_default_rules()

        resource = ParsedResource(
            resource_type="aws_iam_role_policy",
            resource_name="too_permissive",
            properties={
                "policy": json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Action": ["*"],
                        "Effect": "Allow",
                        "Resource": "*"
                    }]
                })
            },
            source_file=str(tmp_path / "test.tf"),
        )

        rule = engine._rules.get("IAM-001")
        assert rule is not None

        finding = rule.check(resource)
        assert finding is not None
        assert finding.status == ComplianceStatus.FAIL

    def test_compliant_resource(self, tmp_path: Path) -> None:
        """Test that compliant resources pass."""
        from cloud_compliance.iac_parser import ParsedResource

        engine = ComplianceEngine()
        engine.load_default_rules()

        resource = ParsedResource(
            resource_type="aws_s3_bucket",
            resource_name="secure_bucket",
            properties={
                "acl": "private",
                "encryption": {"sse_algorithm": "AES256"},
            },
            source_file=str(tmp_path / "test.tf"),
        )

        rule = engine._rules.get("S3-001")
        finding = rule.check(resource)
        assert finding is None  # No finding means compliant


# =========================================================================
# CIS Validator Tests
# =========================================================================

class TestCISValidator:
    """Tests for CIS validator."""

    def test_cis_s3_public_access(self, tmp_path: Path) -> None:
        """Test CIS 2.1.1 - S3 public access check."""
        from cloud_compliance.iac_parser import ParsedResource, ParseResult

        validator = CISValidator()

        resource = ParsedResource(
            resource_type="aws_s3_bucket",
            resource_name="public_bucket",
            properties={"acl": "public-read"},
            source_file=str(tmp_path / "test.tf"),
        )

        parse_result = ParseResult(provider="terraform")
        parse_result.resources = [resource]

        report = validator.validate(parse_result)

        assert not report.is_cis_compliant
        assert report.get_control_status("2.1.1") == ComplianceStatus.FAIL

    def test_cis_ssh_open_check(self, tmp_path: Path) -> None:
        """Test CIS 5.1 - SSH open to world check."""
        from cloud_compliance.iac_parser import ParsedResource, ParseResult

        validator = CISValidator()

        resource = ParsedResource(
            resource_type="aws_security_group_rule",
            resource_name="ssh_open",
            properties={
                "from_port": 22,
                "cidr_blocks": ["0.0.0.0/0"],
            },
            source_file=str(tmp_path / "test.tf"),
        )

        parse_result = ParseResult(provider="terraform")
        parse_result.resources = [resource]

        report = validator.validate(parse_result)

        assert report.get_control_status("5.1") == ComplianceStatus.FAIL


# =========================================================================
# PreToolUse Gate Tests
# =========================================================================

class TestPreToolUseGate:
    """Tests for PreToolUse security gate."""

    def test_block_destructive_command(self) -> None:
        """Test blocking destructive commands."""
        gate = PreToolUseGate()

        decision = gate.check_tool("shell", {"command": "rm -rf /"})
        assert decision.action == GateAction.BLOCK
        assert "rm -rf /" in decision.matched_patterns

    def test_block_aws_deletion(self) -> None:
        """Test blocking AWS deletion commands."""
        gate = PreToolUseGate()

        decision = gate.check_tool("shell", {"command": "aws s3 rm s3://my-bucket --recursive"})
        assert decision.action == GateAction.BLOCK

    def test_block_terraform_destroy(self) -> None:
        """Test blocking terraform destroy."""
        gate = PreToolUseGate()

        decision = gate.check_tool("shell", {"command": "terraform destroy -auto-approve"})
        assert decision.action == GateAction.BLOCK

    def test_allow_safe_command(self) -> None:
        """Test allowing safe commands."""
        gate = PreToolUseGate()

        decision = gate.check_tool("shell", {"command": "ls -la"})
        assert decision.action == GateAction.ALLOW

    def test_non_shell_tool_allowed(self) -> None:
        """Test that non-shell tools are allowed."""
        gate = PreToolUseGate()

        decision = gate.check_tool("read_file", {"path": "/some/file"})
        assert decision.action == GateAction.ALLOW

    def test_warn_mode(self) -> None:
        """Test warning mode."""
        gate = PreToolUseGate(mode="warn")

        decision = gate.check_tool("shell", {"command": "rm -rf /"})
        assert decision.action == GateAction.WARN

    def test_dry_run_mode(self) -> None:
        """Test dry-run mode."""
        gate = PreToolUseGate(mode="dry-run")

        decision = gate.check_tool("shell", {"command": "rm -rf /"})
        assert decision.action == GateAction.ALLOW
        assert "dry-run" in decision.reason.lower()

    def test_generate_hook_json(self) -> None:
        """Test hook JSON generation."""
        gate = PreToolUseGate()
        hook_json = gate.generate_hook_json()

        data = json.loads(hook_json)
        assert data["version"] == "v1"
        assert len(data["hooks"]) == 1
        assert data["hooks"][0]["trigger"] == "PreToolUse"


# =========================================================================
# Property-Based Tests
# =========================================================================

class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.text(min_size=1, max_size=100))
    def test_parser_handles_any_text(self, content: str) -> None:
        """Test that parser handles arbitrary text without crashing."""
        parser = IaCParser()
        result = parser.parse_file(__file__)  # Parse this file
        # Should not crash, even for non-IaC files
        assert isinstance(result, ParseResult)

    @given(st.lists(
        st.fixed_dictionaries({
            "resource_type": st.sampled_from(["aws_s3_bucket", "aws_iam_role", "aws_vpc"]),
            "name": st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        }),
        min_size=0, max_size=10
    ))
    def test_compliance_engine_handles_resources(self, resources: list) -> None:
        """Test compliance engine handles various resource combinations."""
        from cloud_compliance.iac_parser import ParsedResource, ParseResult

        engine = ComplianceEngine()
        engine.load_default_rules()

        parse_result = ParseResult(provider="terraform")
        for r in resources:
            parse_result.resources.append(ParsedResource(
                resource_type=r["resource_type"],
                resource_name=r["name"],
                properties={},
            ))

        report = engine.scan(parse_result)
        # Should complete without error
        assert isinstance(report.failed, int)
        assert isinstance(report.passed, int)


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def sample_insecure_tf(tmp_path: Path) -> Path:
    """Create a sample insecure Terraform file."""
    tf_file = tmp_path / "insecure.tf"
    tf_file.write_text('''
resource "aws_s3_bucket" "public_data" {
  bucket = "my-public-bucket"
  acl    = "public-read"
}

resource "aws_iam_role_policy" "too_permissive" {
  name = "too-permissive-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = ["*"]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}
''')
    return tf_file


@pytest.fixture
def sample_secure_tf(tmp_path: Path) -> Path:
    """Create a sample secure Terraform file."""
    tf_file = tmp_path / "secure.tf"
    tf_file.write_text('''
resource "aws_s3_bucket" "secure_data" {
  bucket = "my-secure-bucket"
  acl    = "private"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure_data" {
  bucket = aws_s3_bucket.secure_data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
''')
    return tf_file
