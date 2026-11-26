"""
IaC Parser - Parse AWS CDK/Terraform templates.

Supports parsing of:
- Terraform (.tf) files
- AWS CDK TypeScript/JavaScript templates
- CloudFormation JSON/YAML templates

Task 3.2: Implement IaC Parser
Validates: Requirements 3.1, 3.2
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ParsedResource:
    """A parsed infrastructure resource."""

    resource_type: str
    resource_name: str
    properties: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    line_number: int = 0
    raw_content: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "resourceType": self.resource_type,
            "resourceName": self.resource_name,
            "properties": self.properties,
            "sourceFile": self.source_file,
            "lineNumber": self.line_number,
        }


@dataclass
class ParseResult:
    """Result of parsing an IaC file."""

    is_successful: bool = True
    resources: list[ParsedResource] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    provider: str = ""  # "terraform", "cdk", "cloudformation"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def resource_count(self) -> int:
        return len(self.resources)

    def get_resources_by_type(self, resource_type: str) -> list[ParsedResource]:
        """Filter resources by type."""
        return [r for r in self.resources if r.resource_type == resource_type]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "isSuccessful": self.is_successful,
            "resources": [r.to_dict() for r in self.resources],
            "variables": self.variables,
            "outputs": self.outputs,
            "provider": self.provider,
            "errors": self.errors,
            "warnings": self.warnings,
            "resourceCount": self.resource_count,
        }


class IaCParser:
    """
    Parser for Infrastructure-as-Code templates.

    Supports:
    - Terraform (.tf) files
    - AWS CDK TypeScript/JavaScript
    - CloudFormation JSON/YAML

    Task 3.2: IaC Parser
    Validates: Requirements 3.1, 3.2

    Example:
        >>> parser = IaCParser()
        >>> result = parser.parse_file(Path("main.tf"))
        >>> result.provider
        'terraform'
    """

    def __init__(
        self,
        *,
        include_raw_content: bool = False,
        extract_variables: bool = True,
    ) -> None:
        """
        Initialize the IaC parser.

        Args:
            include_raw_content: Include raw resource content in results
            extract_variables: Extract and resolve variables
        """
        self.include_raw_content = include_raw_content
        self.extract_variables = extract_variables

    def parse_file(self, file_path: Path | str) -> ParseResult:
        """
        Parse an IaC file and extract resources.

        Args:
            file_path: Path to the IaC file

        Returns:
            ParseResult with extracted resources
        """
        path = Path(file_path)

        if not path.exists():
            return ParseResult(
                is_successful=False,
                errors=[f"File not found: {path}"],
            )

        # Detect file type and parse accordingly
        suffix = path.suffix.lower()

        if suffix == ".tf":
            return self._parse_terraform(path)
        elif suffix in (".json",):
            return self._parse_json_template(path)
        elif suffix in (".yaml", ".yml"):
            return self._parse_yaml_template(path)
        elif suffix in (".ts", ".js"):
            return self._parse_cdk(path)
        else:
            return ParseResult(
                is_successful=False,
                errors=[f"Unsupported file type: {suffix}"],
            )

    def parse_directory(self, dir_path: Path | str) -> list[ParseResult]:
        """
        Parse all IaC files in a directory.

        Args:
            dir_path: Path to the directory

        Returns:
            List of ParseResults for each file
        """
        path = Path(dir_path)
        results: list[ParseResult] = []

        if not path.is_dir():
            return results

        # Parse Terraform files
        for tf_file in path.rglob("*.tf"):
            results.append(self.parse_file(tf_file))

        # Parse CloudFormation/CDK files
        for json_file in path.rglob("*.json"):
            results.append(self.parse_file(json_file))

        for yaml_file in path.rglob("*.yml"):
            results.append(self.parse_file(yaml_file))

        for yaml_file in path.rglob("*.yaml"):
            results.append(self.parse_file(yaml_file))

        # Parse CDK files
        for ts_file in path.rglob("*.ts"):
            if "cdk" in ts_file.read_text(errors="ignore").lower()[:500]:
                results.append(self.parse_file(ts_file))

        return results

    def _parse_terraform(self, path: Path) -> ParseResult:
        """
        Parse a Terraform .tf file.

        Uses HCL-like parsing to extract resource blocks.

        Args:
            path: Path to the .tf file

        Returns:
            ParseResult with Terraform resources
        """
        result = ParseResult(provider="terraform")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Failed to read file: {e}")
            return result

        # Extract resource blocks using regex-based parsing
        # This is a simplified parser; for production use, consider python-hcl2
        resources = self._extract_terraform_resources(content, str(path))
        result.resources = resources

        # Extract variables
        if self.extract_variables:
            result.variables = self._extract_terraform_variables(content)

        # Extract outputs
        result.outputs = self._extract_terraform_outputs(content)

        return result

    def _extract_terraform_resources(
        self,
        content: str,
        source_file: str,
    ) -> list[ParsedResource]:
        """
        Extract resource blocks from Terraform content.

        Uses a state-machine approach to parse nested blocks.

        Args:
            content: Terraform file content
            source_file: Source file path for reference

        Returns:
            List of ParsedResource objects
        """
        resources: list[ParsedResource] = []
        lines = content.split("\n")

        # Pattern to match resource block start
        resource_pattern = re.compile(
            r'resource\s+"(?P<type>[^"]+)"\s+"(?P<name>[^"]+)"\s*\{'
        )

        i = 0
        while i < len(lines):
            line = lines[i]
            match = resource_pattern.search(line)

            if match:
                resource_type = match.group("type")
                resource_name = match.group("name")
                line_number = i + 1

                # Extract the block content
                block_content, end_line = self._extract_block(lines, i)
                properties = self._parse_block_properties(block_content)

                resource = ParsedResource(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    properties=properties,
                    source_file=source_file,
                    line_number=line_number,
                    raw_content=block_content if self.include_raw_content else "",
                )
                resources.append(resource)

                i = end_line + 1
            else:
                i += 1

        return resources

    def _extract_block(self, lines: list[str], start_idx: int) -> tuple[str, int]:
        """
        Extract a block starting from the given line index.

        Handles nested braces correctly.

        Args:
            lines: All lines in the file
            start_idx: Starting line index

        Returns:
            Tuple of (block content, ending line index)
        """
        brace_count = 0
        block_lines: list[str] = []
        found_open = False

        for i in range(start_idx, len(lines)):
            line = lines[i]
            block_lines.append(line)

            # Count braces
            for char in line:
                if char == "{":
                    brace_count += 1
                    found_open = True
                elif char == "}":
                    brace_count -= 1

            # Block is complete when braces are balanced
            if found_open and brace_count == 0:
                return "\n".join(block_lines), i

        return "\n".join(block_lines), len(lines) - 1

    def _parse_block_properties(self, block_content: str) -> dict[str, Any]:
        """
        Parse properties from a Terraform block.

        Simple key-value extraction; doesn't handle all HCL features.

        Args:
            block_content: Content of a Terraform block

        Returns:
            Dictionary of properties
        """
        properties: dict[str, Any] = {}

        # Simple key = value pattern
        simple_pattern = re.compile(r'^\s*(\w+)\s*=\s*"([^"]*)"', re.MULTILINE)
        for match in simple_pattern.finditer(block_content):
            key, value = match.groups()
            properties[key] = value

        # Boolean values
        bool_pattern = re.compile(r'^\s*(\w+)\s*=\s*(true|false)', re.MULTILINE)
        for match in bool_pattern.finditer(block_content):
            key, value = match.groups()
            properties[key] = value.lower() == "true"

        # List values
        list_pattern = re.compile(r'^\s*(\w+)\s*=\s*\[([^\]]+)\]', re.MULTILINE)
        for match in list_pattern.finditer(block_content):
            key, values_str = match.groups()
            # Simple list parsing
            values = [
                v.strip().strip('"').strip("'")
                for v in values_str.split(",")
                if v.strip()
            ]
            properties[key] = values

        return properties

    def _extract_terraform_variables(self, content: str) -> dict[str, Any]:
        """
        Extract variable declarations from Terraform content.

        Args:
            content: Terraform file content

        Returns:
            Dictionary of variables
        """
        variables: dict[str, Any] = {}

        variable_pattern = re.compile(
            r'variable\s+"(?P<name>[^"]+)"\s*\{(?P<body>[^}]*)\}',
            re.DOTALL,
        )

        for match in variable_pattern.finditer(content):
            var_name = match.group("name")
            var_body = match.group("body")

            # Extract default value if present
            default_match = re.search(r'default\s*=\s*"([^"]*)"', var_body)
            if default_match:
                variables[var_name] = default_match.group(1)
            else:
                variables[var_name] = None

        return variables

    def _extract_terraform_outputs(self, content: str) -> dict[str, Any]:
        """
        Extract output declarations from Terraform content.

        Args:
            content: Terraform file content

        Returns:
            Dictionary of outputs
        """
        outputs: dict[str, Any] = {}

        output_pattern = re.compile(
            r'output\s+"(?P<name>[^"]+)"\s*\{(?P<body>[^}]*)\}',
            re.DOTALL,
        )

        for match in output_pattern.finditer(content):
            output_name = match.group("name")
            outputs[output_name] = {"defined": True}

        return outputs

    def _parse_json_template(self, path: Path) -> ParseResult:
        """
        Parse a JSON template (CloudFormation or CDK synthesis).

        Args:
            path: Path to the JSON file

        Returns:
            ParseResult with resources
        """
        result = ParseResult(provider="cloudformation")

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_successful = False
            result.errors.append(f"Invalid JSON: {e}")
            return result
        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Failed to read file: {e}")
            return result

        # Detect template type
        if "Resources" in data:
            # CloudFormation format
            result.provider = "cloudformation"
            resources = self._extract_cloudformation_resources(data, str(path))
            result.resources = resources
        elif "resources" in data:
            # CDK synthesis output
            result.provider = "cdk"
            resources = self._extract_cdk_resources(data, str(path))
            result.resources = resources

        return result

    def _parse_yaml_template(self, path: Path) -> ParseResult:
        """
        Parse a YAML template (CloudFormation).

        Args:
            path: Path to the YAML file

        Returns:
            ParseResult with resources
        """
        result = ParseResult(provider="cloudformation")

        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            result.is_successful = False
            result.errors.append(f"Invalid YAML: {e}")
            return result
        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Failed to read file: {e}")
            return result

        if "Resources" in data:
            resources = self._extract_cloudformation_resources(data, str(path))
            result.resources = resources

        return result

    def _extract_cloudformation_resources(
        self,
        data: dict[str, Any],
        source_file: str,
    ) -> list[ParsedResource]:
        """
        Extract resources from CloudFormation template data.

        Args:
            data: Parsed CloudFormation template
            source_file: Source file path

        Returns:
            List of ParsedResource objects
        """
        resources: list[ParsedResource] = []

        for name, resource in data.get("Resources", {}).items():
            resource_type = resource.get("Type", "Unknown")
            properties = resource.get("Properties", {})

            parsed = ParsedResource(
                resource_type=resource_type,
                resource_name=name,
                properties=properties,
                source_file=source_file,
            )
            resources.append(parsed)

        return resources

    def _extract_cdk_resources(
        self,
        data: dict[str, Any],
        source_file: str,
    ) -> list[ParsedResource]:
        """
        Extract resources from CDK synthesis output.

        Args:
            data: Parsed CDK synthesis output
            source_file: Source file path

        Returns:
            List of ParsedResource objects
        """
        resources: list[ParsedResource] = []

        # CDK synthesis output has a different structure
        for resource in data.get("resources", []):
            resource_type = resource.get("type", resource.get("Construct", "Unknown"))
            resource_name = resource.get("id", "unnamed")
            properties = resource.get("properties", resource.get("props", {}))

            parsed = ParsedResource(
                resource_type=resource_type,
                resource_name=resource_name,
                properties=properties,
                source_file=source_file,
            )
            resources.append(parsed)

        return resources

    def _parse_cdk(self, path: Path) -> ParseResult:
        """
        Parse an AWS CDK TypeScript/JavaScript file.

        Note: This is a simplified parser that extracts resource patterns
        from CDK code. Full parsing would require TypeScript AST parsing.

        Args:
            path: Path to the CDK file

        Returns:
            ParseResult with extracted resources
        """
        result = ParseResult(provider="cdk")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            result.is_successful = False
            result.errors.append(f"Failed to read file: {e}")
            return result

        # Pattern to match CDK construct instantiations
        # e.g., new s3.Bucket(this, 'MyBucket', { ... })
        construct_pattern = re.compile(
            r'new\s+(?P<fqn>[\w.]+)\s*\(\s*this\s*,\s*[\'"](?P<id>\w+)[\'"]'
        )

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            match = construct_pattern.search(line)
            if match:
                fqn = match.group("fqn")  # Fully qualified name
                resource_id = match.group("id")

                # Map CDK construct to AWS resource type
                resource_type = self._map_cdk_construct_to_aws(fqn)

                resource = ParsedResource(
                    resource_type=resource_type,
                    resource_name=resource_id,
                    properties={"cdkConstruct": fqn},
                    source_file=str(path),
                    line_number=i,
                )
                result.resources.append(resource)

        return result

    def _map_cdk_construct_to_aws(self, construct_fqn: str) -> str:
        """
        Map a CDK construct FQN to an AWS resource type.

        Args:
            construct_fqn: Fully qualified construct name (e.g., s3.Bucket)

        Returns:
            AWS resource type (e.g., AWS::S3::Bucket)
        """
        # Common CDK construct to AWS resource mappings
        mappings = {
            "s3.Bucket": "AWS::S3::Bucket",
            "s3.BucketBase": "AWS::S3::Bucket",
            "dynamodb.Table": "AWS::DynamoDB::Table",
            "lambda.Function": "AWS::Lambda::Function",
            "lambda.FunctionBase": "AWS::Lambda::Function",
            "sqs.Queue": "AWS::SQS::Queue",
            "sns.Topic": "AWS::SNS::Topic",
            "ec2.Instance": "AWS::EC2::Instance",
            "ec2.Vpc": "AWS::EC2::VPC",
            "rds.DatabaseInstance": "AWS::RDS::DBInstance",
            "apigateway.RestApi": "AWS::ApiGateway::RestApi",
            "cloudfront.Distribution": "AWS::CloudFront::Distribution",
            "cognito.UserPool": "AWS::Cognito::UserPool",
            "iam.Role": "AWS::IAM::Role",
            "iam.Policy": "AWS::IAM::Policy",
            "kms.Key": "AWS::KMS::Key",
            "secretsmanager.Secret": "AWS::SecretsManager::Secret",
            "sagemaker.Endpoint": "AWS::SageMaker::Endpoint",
            "ecs.Cluster": "AWS::ECS::Cluster",
            "ecs.Service": "AWS::ECS::Service",
            "ecs.TaskDefinition": "AWS::ECS::TaskDefinition",
            "eks.Cluster": "AWS::EKS::Cluster",
            "cloudwatch.Alarm": "AWS::CloudWatch::Alarm",
            "logs.LogGroup": "AWS::Logs::LogGroup",
        }

        # Check direct mapping
        if construct_fqn in mappings:
            return mappings[construct_fqn]

        # Try partial match
        for key, value in mappings.items():
            if key in construct_fqn or construct_fqn.endswith(key.split(".")[-1]):
                return value

        # Return CDK construct name if no mapping found
        return f"CDK::{construct_fqn}"
