"""
Python stdio MCP Server exposing SkillForge core tools to Kiro.

This module provides a Model Context Protocol (MCP) server that exposes
all SkillForge core functionality as MCP tools consumable by Kiro IDE/CLI.

Adapted from tripleyak/SkillForge MCP server patterns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from skillforge.frontmatter import parse_frontmatter, parse_frontmatter_file
from skillforge.triage import TriageRouter, TriageIntent
from skillforge.validate import SkillValidator
from skillforge.evals import PBTRunner
from skillforge.doctor import EcosystemDoctor, quick_check
from skillforge.compiler import SkillCompiler


# MCP Protocol version
PROTOCOL_VERSION = "2024-11-05"


# Tool definitions
TOOLS: list[dict[str, Any]] = [
    {
        "name": "skillforge_parse",
        "description": "Parse YAML frontmatter from a skill definition file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Raw skill content with frontmatter",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional path to skill file (takes precedence over content)",
                },
            },
        },
    },
    {
        "name": "skillforge_validate",
        "description": "Validate a skill definition for structural integrity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to SKILL.md file to validate",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "skillforge_triage",
        "description": "Classify a skill request into USE/IMPROVE/CREATE/COMPOSE/CLARIFY intent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": "Natural language skill request",
                },
            },
            "required": ["request"],
        },
    },
    {
        "name": "skillforge_doctor",
        "description": "Diagnose workspace health and .kiro/ configuration",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_root": {
                    "type": "string",
                    "description": "Root directory of the workspace",
                },
            },
            "required": ["workspace_root"],
        },
    },
    {
        "name": "skillforge_test",
        "description": "Run property-based tests against a skill's parameter schema",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_path": {
                    "type": "string",
                    "description": "Path to SKILL.md file to test",
                },
                "max_examples": {
                    "type": "integer",
                    "description": "Maximum test examples (default: 50)",
                    "default": 50,
                },
            },
            "required": ["skill_path"],
        },
    },
    {
        "name": "skillforge_compile",
        "description": "Compile a skill to MCP server code or Kiro hook JSON",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_path": {
                    "type": "string",
                    "description": "Path to SKILL.md file to compile",
                },
                "output_type": {
                    "type": "string",
                    "enum": ["mcp_server", "kiro_hook", "steering"],
                    "description": "Type of output to generate",
                },
                "trigger": {
                    "type": "string",
                    "description": "Trigger type for Kiro hooks (e.g., PreToolUse)",
                },
            },
            "required": ["skill_path", "output_type"],
        },
    },
]


class MCPServer:
    """
    MCP stdio server exposing SkillForge tools.

    Handles JSON-RPC 2.0 protocol over stdin/stdout.
    Supports initialize, tools/list, and tools/call methods.

    Example:
        >>> server = MCPServer()
        >>> server.run()  # Starts the stdio server loop
    """

    def __init__(
        self,
        *,
        server_name: str = "skillforge-core",
        version: str = "0.1.0",
    ) -> None:
        """Initialize the MCP server."""
        self.server_name = server_name
        self.version = version
        self.tool_handlers: dict[str, Callable[[dict[str, Any]], list[dict[str, Any]]]] = {
            "skillforge_parse": self._handle_parse,
            "skillforge_validate": self._handle_validate,
            "skillforge_triage": self._handle_triage,
            "skillforge_doctor": self._handle_doctor,
            "skillforge_test": self._handle_test,
            "skillforge_compile": self._handle_compile,
        }

    def run(self) -> None:
        """Run the MCP stdio server loop."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())
                response = self._handle_request(request)

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                self._send_error(None, -32700, f"Parse error: {e}")

            except Exception as e:
                self._send_error(None, -32603, f"Internal error: {e}")

    def _handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming JSON-RPC request."""
        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._handle_initialize(request_id, params)

        elif method == "tools/list":
            return self._handle_tools_list(request_id)

        elif method == "tools/call":
            return self._handle_tools_call(request_id, params)

        else:
            return self._error_response(request_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.version,
                },
            },
        }

    def _handle_tools_list(self, request_id: Any) -> dict[str, Any]:
        """Handle tools/list request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": TOOLS,
            },
        }

    def _handle_tools_call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        handler = self.tool_handlers.get(tool_name)
        if not handler:
            return self._error_response(request_id, -32601, f"Unknown tool: {tool_name}")

        try:
            content = handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content,
                },
            }

        except Exception as e:
            return self._error_response(request_id, -32603, f"Tool execution failed: {e}")

    def _handle_parse(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_parse tool."""
        file_path = args.get("file_path")
        content = args.get("content")

        if file_path:
            result = parse_frontmatter_file(file_path)
        elif content:
            result = parse_frontmatter(content)
        else:
            raise ValueError("Either file_path or content must be provided")

        return [{
            "type": "text",
            "text": json.dumps({
                "metadata": result.metadata,
                "body": result.body[:500] + "..." if len(result.body) > 500 else result.body,
                "is_valid": result.is_valid,
                "errors": result.errors,
            }, indent=2),
        }]

    def _handle_validate(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_validate tool."""
        file_path = args.get("file_path")
        if not file_path:
            raise ValueError("file_path is required")

        validator = SkillValidator()
        result = validator.validate_file(file_path)

        return [{
            "type": "text",
            "text": json.dumps({
                "is_valid": result.is_valid,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "errors": [{"code": e.code, "message": e.message, "location": e.location} for e in result.errors],
                "warnings": [{"code": w.code, "message": w.message, "location": w.location} for w in result.warnings],
            }, indent=2),
        }]

    def _handle_triage(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_triage tool."""
        request = args.get("request")
        if not request:
            raise ValueError("request is required")

        router = TriageRouter()
        result = router.triage(request)

        return [{
            "type": "text",
            "text": json.dumps({
                "intent": result.intent.value,
                "confidence": result.confidence,
                "matched_skill": result.matched_skill,
                "matched_skills": result.matched_skills,
                "reasoning": result.reasoning,
                "suggested_questions": result.suggested_questions,
            }, indent=2),
        }]

    def _handle_doctor(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_doctor tool."""
        workspace_root = args.get("workspace_root")
        if not workspace_root:
            raise ValueError("workspace_root is required")

        doctor = EcosystemDoctor()
        report = doctor.diagnose(workspace_root)

        return [{
            "type": "text",
            "text": json.dumps(report.to_dict(), indent=2),
        }]

    def _handle_test(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_test tool."""
        skill_path = args.get("skill_path")
        max_examples = args.get("max_examples", 50)

        if not skill_path:
            raise ValueError("skill_path is required")

        runner = PBTRunner(max_examples=max_examples)
        results = runner.run_skill_tests(skill_path)

        return [{
            "type": "text",
            "text": json.dumps({
                "passed": all(r.passed for r in results),
                "results": [
                    {
                        "property": r.property_name,
                        "passed": r.passed,
                        "test_count": r.test_count,
                        "failure_count": r.failure_count,
                        "errors": r.errors,
                    }
                    for r in results
                ],
            }, indent=2),
        }]

    def _handle_compile(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle skillforge_compile tool."""
        skill_path = args.get("skill_path")
        output_type = args.get("output_type")
        trigger = args.get("trigger", "PreToolUse")

        if not skill_path:
            raise ValueError("skill_path is required")
        if not output_type:
            raise ValueError("output_type is required")

        compiler = SkillCompiler()

        if output_type == "mcp_server":
            result = compiler.compile_to_mcp(skill_path)
        elif output_type == "kiro_hook":
            result = compiler.compile_to_hook(skill_path, trigger=trigger)
        elif output_type == "steering":
            result = compiler.compile_to_steering(skill_path)
        else:
            raise ValueError(f"Unknown output_type: {output_type}")

        return [{
            "type": "text",
            "text": json.dumps({
                "is_successful": result.is_successful,
                "output_type": result.output_type,
                "errors": result.errors,
                "warnings": result.warnings,
                "generated_code": result.generated_code[:2000] + "..." if len(result.generated_code) > 2000 else result.generated_code,
            }, indent=2),
        }]

    def _error_response(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def _send_error(self, request_id: Any, code: int, message: str) -> None:
        """Send an error response to stdout."""
        response = self._error_response(request_id, code, message)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    """Entry point for the MCP server."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
