"""
Cloud Compliance Auditor CLI.

Terminal-based CLI tool for scanning IaC templates (Terraform, CDK)
against AWS security rules and CIS benchmarks.

Uses skillforge-core for skill compilation and validation.

Task 3.1: CLI Application Structure
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from cloud_compliance.iac_parser import IaCParser, ParseResult
from cloud_compliance.compliance_engine import ComplianceEngine, ComplianceReport, Severity
from cloud_compliance.cis_validator import CISValidator, CISComplianceReport


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="compliance-auditor")
def main() -> None:
    """Cloud Compliance Auditor - Scan IaC for security issues.

    Enterprise-grade compliance scanning for AWS infrastructure-as-code
    templates. Supports Terraform, AWS CDK, and CloudFormation.

    Examples:
        compliance-auditor scan ./infrastructure
        compliance-auditor scan ./main.tf --format json
        compliance-auditor cis ./samples --level 2
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["text", "json", "markdown"]), default="text", help="Output format")
@click.option("--severity", "-s", type=click.Choice(["critical", "high", "medium", "low", "all"]), default="all", help="Minimum severity")
@click.option("--framework", "-w", type=click.Choice(["cis", "nist", "pci", "all"]), default="all", help="Compliance framework")
@click.option("--fail-on-violations", is_flag=True, help="Exit with error code on violations")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def scan(
    path: str,
    format: str,
    severity: str,
    framework: str,
    fail_on_violations: bool,
    output: str | None,
) -> None:
    """Scan an IaC file or directory for compliance issues.

    Analyzes infrastructure-as-code templates for security misconfigurations
    and compliance violations.
    """
    target = Path(path)

    # Initialize parser and engine
    parser = IaCParser(include_raw_content=False)
    engine = ComplianceEngine(include_passed=True)
    engine.load_default_rules()

    # Parse IaC files
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Parsing IaC files...", total=None)

        if target.is_file():
            parse_results = [parser.parse_file(target)]
        else:
            parse_results = parser.parse_directory(target)

    # Filter valid results
    valid_results = [r for r in parse_results if r.is_successful]

    if not valid_results:
        console.print("[red]No valid IaC files found[/red]")
        sys.exit(1)

    # Run compliance scan
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Running compliance checks...", total=None)
        report = engine.scan(valid_results)

    # Output results
    if format == "json":
        output_data = json.dumps(report.to_dict(), indent=2)
    elif format == "markdown":
        output_data = _format_markdown_report(report)
    else:
        _display_report(report, severity)
        output_data = None

    if output:
        Path(output).write_text(output_data or "")
        console.print(f"\n[green]Report saved to {output}[/green]")

    if format == "json" and not output:
        console.print(output_data)

    # Exit with error code if violations found
    if fail_on_violations and report.failed > 0:
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--level", "-l", type=click.Choice(["1", "2"]), default="1", help="CIS benchmark level")
@click.option("--format", "-f", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--fail-on-violations", is_flag=True, help="Exit with error code on violations")
def cis(
    path: str,
    level: str,
    format: str,
    fail_on_violations: bool,
) -> None:
    """Validate IaC against CIS AWS Foundations Benchmark.

    Performs compliance checks against CIS controls for AWS security.
    """
    target = Path(path)

    # Initialize parser and validator
    parser = IaCParser()
    validator = CISValidator(cis_level=int(level))

    # Parse IaC files
    if target.is_file():
        parse_results = [parser.parse_file(target)]
    else:
        parse_results = parser.parse_directory(target)

    valid_results = [r for r in parse_results if r.is_successful]

    if not valid_results:
        console.print("[red]No valid IaC files found[/red]")
        sys.exit(1)

    # Run CIS validation
    cis_report = validator.validate(valid_results)

    # Output results
    if format == "json":
        console.print(json.dumps(cis_report.to_dict(), indent=2))
    else:
        _display_cis_report(cis_report)

    if fail_on_violations and cis_report.is_cis_compliant is False:
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True))
def parse(path: str) -> None:
    """Parse and display IaC resource structure.

    Useful for debugging and understanding IaC templates.
    """
    target = Path(path)
    parser = IaCParser()

    if target.is_file():
        result = parser.parse_file(target)
        _display_parse_result(result)
    else:
        results = parser.parse_directory(target)
        for result in results:
            if result.is_successful:
                _display_parse_result(result)


@main.command()
@click.argument("path", type=click.Path(exists=True))
def validate(path: str) -> None:
    """Validate a skill definition file."""
    try:
        from skillforge import SkillValidator

        validator = SkillValidator()
        result = validator.validate_file(path)

        if result.is_valid:
            console.print(Panel.fit("[green]✓[/green] Skill is valid", title="Validation Result"))
        else:
            console.print(Panel.fit("[red]✗[/red] Skill has errors", title="Validation Result"))
            for error in result.errors:
                console.print(f"  [red]•[/red] {error}")
    except ImportError:
        console.print("[yellow]skillforge-core not installed. Using built-in validation.[/yellow]")
        _validate_skill_basic(path)


@main.command()
@click.option("--generate-hook", is_flag=True, help="Generate Kiro hook JSON")
def gate(generate_hook: bool) -> None:
    """Manage the PreToolUse security gate.

    The security gate blocks dangerous operations before they execute.
    """
    if generate_hook:
        from cloud_compliance.pretooluse_gate import PreToolUseGate

        gate = PreToolUseGate()
        hook_json = gate.generate_hook_json()
        console.print(Panel(hook_json, title="PreToolUse Security Gate Hook"))
        console.print("\n[dim]Save this to .kiro/hooks/pre-tool-security-gate.json[/dim]")
    else:
        console.print("[yellow]Use --generate-hook to create a Kiro hook configuration[/yellow]")


def _display_report(report: ComplianceReport, severity_filter: str) -> None:
    """Display compliance report in terminal."""
    # Summary panel
    summary_text = (
        f"Files Scanned: {report.files_scanned}\n"
        f"Resources Scanned: {report.resources_scanned}\n"
        f"Frameworks: {', '.join(report.frameworks) or 'None'}"
    )
    console.print(Panel(summary_text, title="Scan Summary"))

    # Status panel
    status_color = "green" if report.is_compliant else "red"
    status_text = (
        f"[green]Passed: {report.passed}[/green]\n"
        f"[red]Failed: {report.failed}[/red]\n"
        f"[yellow]Warnings: {report.warnings}[/yellow]\n"
        f"[blue]Skipped: {report.skipped}[/blue]"
    )
    console.print(Panel(status_text, title=f"[{status_color}]Compliance Status[/{status_color}]"))

    if not report.findings:
        console.print("\n[green]No compliance issues found![/green]")
        return

    # Filter by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    filtered_findings = [
        f for f in report.findings
        if severity_filter == "all" or f.severity.value == severity_filter
    ]

    # Sort by severity
    filtered_findings.sort(key=lambda f: severity_order.get(f.severity.value, 5))

    # Findings table
    table = Table(title=f"Compliance Findings ({len(filtered_findings)})")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Status", width=8)
    table.add_column("Rule", width=10)
    table.add_column("Resource", width=25)
    table.add_column("Message")

    for finding in filtered_findings:
        severity_colors = {
            "critical": "red bold",
            "high": "red",
            "medium": "yellow",
            "low": "blue",
            "info": "dim",
        }
        severity_style = severity_colors.get(finding.severity.value, "white")
        status_style = "green" if finding.status.value == "pass" else "red"

        table.add_row(
            f"[{severity_style}]{finding.severity.value.upper()}[/{severity_style}]",
            f"[{status_style}]{finding.status.value.upper()}[/{status_style}]",
            finding.rule_id,
            f"{finding.resource_name}"[:25],
            finding.message[:50] + ("..." if len(finding.message) > 50 else ""),
        )

    console.print(table)

    # Show remediations for failures
    failures = [f for f in filtered_findings if f.status.value == "fail"]
    if failures:
        console.print("\n[bold]Remediation Steps:[/bold]")
        for finding in failures[:5]:  # Show top 5
            console.print(f"\n[red]• {finding.rule_id}[/red] - {finding.resource_name}")
            if finding.remediation:
                console.print(f"  [dim]{finding.remediation}[/dim]")


def _display_cis_report(report: CISComplianceReport) -> None:
    """Display CIS compliance report."""
    # Summary
    status = "[green]COMPLIANT[/green]" if report.is_cis_compliant else "[red]NON-COMPLIANT[/red]"
    console.print(Panel(
        f"CIS Level: {report.cis_level}\n"
        f"Status: {status}\n"
        f"Findings: {len(report.cis_findings)}",
        title="CIS AWS Foundations Benchmark",
    ))

    # Control status table
    table = Table(title="CIS Control Status")
    table.add_column("Control ID", width=12)
    table.add_column("Title", width=40)
    table.add_column("Status", width=10)

    for control in report.controls:
        status = report.get_control_status(control.control_id)
        status_style = "green" if status.value == "pass" else "red" if status.value == "fail" else "yellow"
        table.add_row(
            control.control_id,
            control.title[:40] + ("..." if len(control.title) > 40 else ""),
            f"[{status_style}]{status.value.upper()}[/{status_style}]",
        )

    console.print(table)


def _display_parse_result(result: ParseResult) -> None:
    """Display parsed IaC resources."""
    tree = Tree(f"[bold]{result.provider}[/bold] - {result.resource_count} resources")

    # Group resources by type
    resources_by_type: dict[str, list] = {}
    for resource in result.resources:
        if resource.resource_type not in resources_by_type:
            resources_by_type[resource.resource_type] = []
        resources_by_type[resource.resource_type].append(resource)

    for resource_type, resources in resources_by_type.items():
        type_branch = tree.add(f"[blue]{resource_type}[/blue] ({len(resources)})")
        for resource in resources[:5]:  # Show max 5 per type
            type_branch.add(f"[green]{resource.resource_name}[/green]")
        if len(resources) > 5:
            type_branch.add(f"[dim]... and {len(resources) - 5} more[/dim]")

    console.print(tree)

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  [red]•[/red] {error}")


def _format_markdown_report(report: ComplianceReport) -> str:
    """Format report as markdown."""
    lines = [
        "# Cloud Compliance Report",
        "",
        "## Summary",
        "",
        f"- **Files Scanned**: {report.files_scanned}",
        f"- **Resources Scanned**: {report.resources_scanned}",
        f"- **Frameworks**: {', '.join(report.frameworks) or 'None'}",
        "",
        "## Status",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| Passed | {report.passed} |",
        f"| Failed | {report.failed} |",
        f"| Warnings | {report.warnings} |",
        "",
        "## Findings",
        "",
    ]

    for finding in report.findings:
        status_emoji = "✅" if finding.status.value == "pass" else "❌" if finding.status.value == "fail" else "⚠️"
        lines.append(f"### {status_emoji} {finding.rule_id}: {finding.rule_name}")
        lines.append("")
        lines.append(f"- **Severity**: {finding.severity.value.upper()}")
        lines.append(f"- **Resource**: `{finding.resource_name}` ({finding.resource_type})")
        lines.append(f"- **Message**: {finding.message}")
        if finding.remediation:
            lines.append(f"- **Remediation**: {finding.remediation}")
        lines.append("")

    return "\n".join(lines)


def _validate_skill_basic(path: str) -> None:
    """Basic skill validation without skillforge-core."""
    import yaml

    skill_path = Path(path)
    content = skill_path.read_text()

    if not content.startswith("---"):
        console.print("[red]✗ Missing YAML frontmatter[/red]")
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        console.print("[red]✗ Invalid frontmatter format[/red]")
        return

    try:
        metadata = yaml.safe_load(parts[1])
        console.print("[green]✓ Valid YAML frontmatter[/green]")

        required = ["name", "description"]
        for field in required:
            if field not in metadata:
                console.print(f"[yellow]⚠ Missing recommended field: {field}[/yellow]")
            else:
                console.print(f"[green]✓ Has {field}[/green]")

    except yaml.YAMLError as e:
        console.print(f"[red]✗ YAML parse error: {e}[/red]")


if __name__ == "__main__":
    main()
