"""
PreToolUse Gate - Security hook for blocking dangerous operations.

Implements a Kiro Agent Hook that intercepts tool invocations before
execution and blocks dangerous shell commands and AWS operations.

Task 3.5: Implement PreToolUse Gate
Validates: Requirements 3.5, 5.3
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class GateAction(str, Enum):
    """Actions the gate can take."""
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"


class Severity(str, Enum):
    """Severity levels for blocked operations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class GateDecision:
    """Decision made by the PreToolUse gate."""

    action: GateAction
    reason: str
    severity: Severity = Severity.MEDIUM
    matched_patterns: list[str] = field(default_factory=list)
    remediation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "action": self.action.value,
            "reason": self.reason,
            "severity": self.severity.value,
            "matchedPatterns": self.matched_patterns,
            "remediation": self.remediation,
            "metadata": self.metadata,
        }

    def to_exit_code(self) -> int:
        """Convert to exit code for hook protocol."""
        if self.action == GateAction.ALLOW:
            return 0
        elif self.action == GateAction.BLOCK:
            return 2  # Kiro uses exit code 2 to block
        else:
            return 1  # Warning


@dataclass
class BlockedPattern:
    """A pattern that triggers blocking."""

    pattern: str
    description: str
    severity: Severity
    remediation: str
    category: str = "general"
    is_regex: bool = False


class PreToolUseGate:
    """
    Security gate that blocks dangerous operations.

    Intercepts tool invocations and checks them against a list of
    dangerous patterns. Used as a Kiro Agent Hook for PreToolUse trigger.

    Task 3.5: PreToolUse Gate
    Validates: Requirements 3.5, 5.3

    Example:
        >>> gate = PreToolUseGate()
        >>> decision = gate.check_tool("shell", {"command": "rm -rf /"})
        >>> decision.action
        <GateAction.BLOCK: 'block'>
    """

    def __init__(
        self,
        *,
        mode: str = "block",  # "block", "warn", "dry-run"
        custom_patterns: list[BlockedPattern] | None = None,
    ) -> None:
        """
        Initialize the PreToolUse gate.

        Args:
            mode: Gate mode - "block", "warn", or "dry-run"
            custom_patterns: Additional patterns to block
        """
        self.mode = mode
        self._patterns: list[BlockedPattern] = []
        self._load_default_patterns()

        if custom_patterns:
            self._patterns.extend(custom_patterns)

    def _load_default_patterns(self) -> None:
        """Load default dangerous operation patterns."""
        # Critical - Destructive File Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="rm -rf /",
                description="Recursive root deletion",
                severity=Severity.CRITICAL,
                remediation="Use targeted deletion with specific paths",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="rm -rf /*",
                description="Recursive root deletion with wildcard",
                severity=Severity.CRITICAL,
                remediation="Use targeted deletion with specific paths",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="rm -rf ~",
                description="Recursive home directory deletion",
                severity=Severity.CRITICAL,
                remediation="Use targeted deletion with specific paths",
                category="filesystem",
            ),
            BlockedPattern(
                pattern=":(){ :|:& };:",
                description="Fork bomb",
                severity=Severity.CRITICAL,
                remediation="This is a denial-of-service attack",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="> /dev/sda",
                description="Direct disk write",
                severity=Severity.CRITICAL,
                remediation="Avoid direct disk operations",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="mkfs",
                description="Format filesystem",
                severity=Severity.CRITICAL,
                remediation="Avoid filesystem formatting commands",
                category="filesystem",
            ),
        ])

        # High - AWS Destructive Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="aws s3 rm",
                description="S3 bucket/object deletion",
                severity=Severity.HIGH,
                remediation="Verify deletion target and use --dryrun first",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws s3 rb",
                description="S3 bucket removal",
                severity=Severity.HIGH,
                remediation="Verify bucket is empty and should be removed",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws ec2 terminate-instances",
                description="EC2 instance termination",
                severity=Severity.HIGH,
                remediation="Verify instance should be terminated",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws rds delete-db-instance",
                description="RDS instance deletion",
                severity=Severity.HIGH,
                remediation="Verify database backup and deletion",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws dynamodb delete-table",
                description="DynamoDB table deletion",
                severity=Severity.HIGH,
                remediation="Verify table backup and deletion",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws lambda delete-function",
                description="Lambda function deletion",
                severity=Severity.HIGH,
                remediation="Verify function should be deleted",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws cloudformation delete-stack",
                description="CloudFormation stack deletion",
                severity=Severity.HIGH,
                remediation="Verify stack deletion consequences",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws iam delete-role",
                description="IAM role deletion",
                severity=Severity.HIGH,
                remediation="Verify role is not in use",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws kms schedule-key-deletion",
                description="KMS key deletion scheduling",
                severity=Severity.HIGH,
                remediation="Verify key is no longer needed",
                category="aws",
            ),
        ])

        # High - Terraform/Infrastructure Destructive Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="terraform destroy",
                description="Terraform infrastructure destruction",
                severity=Severity.HIGH,
                remediation="Review destruction plan and confirm",
                category="infrastructure",
            ),
            BlockedPattern(
                pattern="cdk destroy",
                description="CDK stack destruction",
                severity=Severity.HIGH,
                remediation="Review destruction plan and confirm",
                category="infrastructure",
            ),
            BlockedPattern(
                pattern="pulumi destroy",
                description="Pulumi stack destruction",
                severity=Severity.HIGH,
                remediation="Review destruction plan and confirm",
                category="infrastructure",
            ),
            BlockedPattern(
                pattern="sam delete",
                description="SAM application deletion",
                severity=Severity.HIGH,
                remediation="Verify deletion parameters",
                category="infrastructure",
            ),
        ])

        # High - Database Destructive Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="DROP DATABASE",
                description="Database deletion",
                severity=Severity.HIGH,
                remediation="Verify database backup before deletion",
                category="database",
            ),
            BlockedPattern(
                pattern="DROP TABLE",
                description="Table deletion",
                severity=Severity.HIGH,
                remediation="Verify table backup before deletion",
                category="database",
            ),
            BlockedPattern(
                pattern="TRUNCATE TABLE",
                description="Table truncation",
                severity=Severity.HIGH,
                remediation="Verify data backup before truncation",
                category="database",
            ),
            BlockedPattern(
                pattern="DELETE FROM",
                description="Bulk deletion",
                severity=Severity.MEDIUM,
                remediation="Verify WHERE clause is correct",
                category="database",
            ),
        ])

        # Medium - System Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="chmod -R 777",
                description="Recursive world-writable permissions",
                severity=Severity.MEDIUM,
                remediation="Use more restrictive permissions",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="chown -R",
                description="Recursive ownership change",
                severity=Severity.MEDIUM,
                remediation="Verify ownership change scope",
                category="filesystem",
            ),
            BlockedPattern(
                pattern="curl.*|.*sh",
                description="Piping curl to shell",
                severity=Severity.MEDIUM,
                remediation="Download and inspect script before executing",
                category="network",
                is_regex=True,
            ),
            BlockedPattern(
                pattern="wget.*|.*sh",
                description="Piping wget to shell",
                severity=Severity.MEDIUM,
                remediation="Download and inspect script before executing",
                category="network",
                is_regex=True,
            ),
        ])

        # Medium - AWS Expensive Operations
        self._patterns.extend([
            BlockedPattern(
                pattern="aws ec2 run-instances",
                description="EC2 instance launch",
                severity=Severity.MEDIUM,
                remediation="Verify instance type and count",
                category="aws",
            ),
            BlockedPattern(
                pattern="aws rds create-db-instance",
                description="RDS instance creation",
                severity=Severity.MEDIUM,
                remediation="Verify instance class and storage",
                category="aws",
            ),
        ])

        # Low - Information Disclosure
        self._patterns.extend([
            BlockedPattern(
                pattern="aws sts get-caller-identity",
                description="AWS identity check",
                severity=Severity.LOW,
                remediation="This is informational, proceed with caution",
                category="aws",
            ),
        ])

    def check_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> GateDecision:
        """
        Check a tool invocation against dangerous patterns.

        Args:
            tool_name: Name of the tool being invoked
            tool_input: Tool input parameters

        Returns:
            GateDecision with action and reason
        """
        # Only check shell commands
        if tool_name.lower() != "shell":
            return GateDecision(
                action=GateAction.ALLOW,
                reason="Tool not subject to security gate",
                severity=Severity.LOW,
            )

        # Get command from input
        command = tool_input.get("command", "")
        if not command:
            return GateDecision(
                action=GateAction.ALLOW,
                reason="No command to check",
            )

        # Check against patterns
        matched_patterns: list[str] = []
        max_severity = Severity.LOW
        remediation = ""

        for pattern in self._patterns:
            matched = False

            if pattern.is_regex:
                try:
                    matched = bool(re.search(pattern.pattern, command, re.IGNORECASE))
                except re.error:
                    matched = pattern.pattern.lower() in command.lower()
            else:
                matched = pattern.pattern.lower() in command.lower()

            if matched:
                matched_patterns.append(pattern.pattern)

                if pattern.severity.value > max_severity.value:
                    max_severity = pattern.severity

                if not remediation:
                    remediation = pattern.remediation

        if matched_patterns:
            if self.mode == "dry-run":
                return GateDecision(
                    action=GateAction.ALLOW,
                    reason=f"[DRY-RUN] Would block: matched {len(matched_patterns)} dangerous patterns",
                    severity=max_severity,
                    matched_patterns=matched_patterns,
                    remediation=remediation,
                )
            elif self.mode == "warn":
                return GateDecision(
                    action=GateAction.WARN,
                    reason=f"Warning: command matches {len(matched_patterns)} dangerous patterns",
                    severity=max_severity,
                    matched_patterns=matched_patterns,
                    remediation=remediation,
                )
            else:  # block mode
                return GateDecision(
                    action=GateAction.BLOCK,
                    reason=f"BLOCKED: Command matches dangerous patterns: {', '.join(matched_patterns[:3])}",
                    severity=max_severity,
                    matched_patterns=matched_patterns,
                    remediation=remediation,
                )

        return GateDecision(
            action=GateAction.ALLOW,
            reason="No dangerous patterns detected",
        )

    def check_from_stdin(self) -> GateDecision:
        """
        Check tool invocation from stdin (for Kiro hook protocol).

        Reads JSON from stdin containing hook context and returns
        a decision. Exit code indicates action:
        - 0: Allow
        - 1: Warn
        - 2: Block

        Returns:
            GateDecision with action
        """
        try:
            # Read JSON from stdin
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            return GateDecision(
                action=GateAction.ALLOW,
                reason="Invalid JSON input, allowing by default",
            )

        # Extract tool name and input
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        return self.check_tool(tool_name, tool_input)

    def execute_as_hook(self) -> int:
        """
        Execute as a Kiro hook.

        Reads from stdin, checks, and outputs result.
        Exit code determines action.

        Returns:
            Exit code (0=allow, 1=warn, 2=block)
        """
        decision = self.check_from_stdin()

        if decision.action == GateAction.BLOCK:
            # Output block message to stderr
            print(f"BLOCKED BY SECURITY GATE: {decision.reason}", file=sys.stderr)
            if decision.remediation:
                print(f"Remediation: {decision.remediation}", file=sys.stderr)

        return decision.to_exit_code()

    def generate_hook_json(self) -> str:
        """
        Generate a Kiro hook JSON configuration.

        Returns:
            JSON string for .kiro/hooks/pre-tool-security-gate.json
        """
        hook_config = {
            "version": "v1",
            "hooks": [
                {
                    "name": "pre-tool-security-gate",
                    "description": "Blocks destructive shell or AWS deletion commands before execution.",
                    "trigger": "PreToolUse",
                    "matcher": "shell",
                    "action": {
                        "type": "command",
                        "command": f"python3 -c '{self._get_inline_script()}'",
                    },
                    "timeout": 10,
                    "enabled": True,
                }
            ],
        }

        return json.dumps(hook_config, indent=2)

    def _get_inline_script(self) -> str:
        """Get inline Python script for the hook."""
        return """
import sys, json
try:
    ctx = json.load(sys.stdin)
    tool_input = ctx.get("tool_input", {})
    cmd = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else str(tool_input)
    blocked = [
        "rm -rf /",
        "aws s3 rm",
        "aws s3 rb",
        "terraform destroy",
        "DROP DATABASE",
        "DROP TABLE",
    ]
    hits = [b for b in blocked if b.lower() in cmd.lower()]
    if hits:
        sys.stderr.write(f"BLOCKED BY SECURITY GATE: {hits}\\\\n")
        sys.exit(2)
    sys.exit(0)
except Exception as e:
    sys.stderr.write(f"Security gate error: {e}\\\\n")
    sys.exit(0)
""".strip()


def main() -> int:
    """Main entry point for hook execution."""
    gate = PreToolUseGate()
    return gate.execute_as_hook()


if __name__ == "__main__":
    sys.exit(main())
