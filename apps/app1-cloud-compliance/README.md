# Cloud Compliance Auditor

Enterprise Cloud Compliance Auditor - CLI tool for IaC scanning and CIS benchmark validation.

## Features

- Scan Terraform files for AWS security issues
- Check CDK templates for compliance violations
- Validate skill definitions
- Rich terminal output with severity indicators

## Installation

```bash
pip install -e .
```

## Usage

### Scan IaC Files

```bash
# Scan a single file
compliance-auditor scan main.tf

# Scan a directory
compliance-auditor scan ./terraform/

# Output as JSON
compliance-auditor scan main.tf --format json
```

### Validate Skills

```bash
compliance-auditor validate skills/aws-audit/SKILL.md
```

## Checks

- **S3-001**: Public S3 bucket ACLs
- **S3-002**: Missing server-side encryption
- **IAM-001**: Wildcard IAM actions

## Integration with skillforge-core

This app imports skill definitions compiled by the skillforge-core engine.
