"""
Skill Compiler - Transpiles Skills to MCP Tools and Kiro Hooks.

Converts verified skill definitions into native Model Context Protocol
(MCP) stdio servers and Kiro Agent Hooks.

Implements:
- Task 2.7.1: MCP Compiler - Generate MCP tool definitions with valid JSON Schema
- Task 2.7.2: Hook Compiler - Generate Kiro Agent Hook JSON from skill definitions
- Task 2.7.3: Runtime Validator - Validate output formats for Python/TypeScript artifacts

Adapted from tripleyak/SkillForge compile_skill.py patterns.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.6
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from skillforge.frontmatter import parse_frontmatter, parse_frontmatter_file, FrontmatterResult


# ============================================================================
# Compilation Result Types
# ============================================================================

class OutputType(str, Enum):
    """Types of compilation outputs."""
    MCP_SERVER = "mcp_server"
    KIRO_HOOK = "kiro_hook"
    STEERING = "steering"
    PYTHON_ARTIFACT = "python_artifact"
    TYPESCRIPT_ARTIFACT = "typescript_artifact"


@dataclass
class CompilationResult:
    """Result of compiling a skill."""

    is_successful: bool = True
    output_type: str = ""  # "mcp_server", "kiro_hook", "steering"
    output_path: Path | None = None
    generated_code: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            "isSuccessful": self.is_successful,
            "outputType": self.output_type,
            "outputPath": str(self.output_path) if self.output_path else None,
            "generatedCode": self.generated_code,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool from a skill."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


# ============================================================================
# Hook Trigger Types (Task 2.7.2)
# ============================================================================

class HookTrigger(str, Enum):
    """Supported Kiro Agent Hook triggers."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_FILE_SAVE = "PostFileSave"
    POST_FILE_CREATE = "PostFileCreate"
    POST_FILE_DELETE = "PostFileDelete"
    AGENT_SPAWN = "AgentSpawn"
    SESSION_START = "SessionStart"
    STOP = "Stop"


class HookActionType(str, Enum):
    """Types of hook actions."""
    COMMAND = "command"
    AGENT = "agent"


@dataclass
class HookDefinition:
    """Definition of a Kiro Agent Hook."""
    name: str
    trigger: HookTrigger
    action_type: HookActionType
    description: str = ""
    matcher: str | None = None
    timeout: int = 60
    enabled: bool = True
    command: str | None = None
    prompt: str | None = None
    async_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to Kiro hook JSON format."""
        hook: dict[str, Any] = {
            "name": self.name,
            "trigger": self.trigger.value,
            "enabled": self.enabled,
            "action": {"type": self.action_type.value},
        }

        if self.description:
            hook["description"] = self.description
        if self.matcher:
            hook["matcher"] = self.matcher
        if self.timeout > 0:
            hook["timeout"] = self.timeout

        if self.action_type == HookActionType.COMMAND and self.command:
            hook["action"]["command"] = self.command
        elif self.action_type == HookActionType.AGENT and self.prompt:
            hook["action"]["prompt"] = self.prompt

        if self.async_execution:
            hook["async"] = True

        return hook


# ============================================================================
# MCP Compiler (Task 2.7.1)
# ============================================================================


class MCPCompiler:
    """
    Generates MCP tool definitions with valid JSON Schema.

    Loads intermediate representation from Synthesis phase and generates
    MCP tool definitions in valid JSON Schema format.

    Task 2.7.1: MCP Compiler
    Validates: Requirements 5.1, 5.2

    Example:
        >>> compiler = MCPCompiler()
        >>> tool_def = compiler.compile_tool_definition(skill_metadata)
        >>> tool_def.name
        'my-skill'
    """

    def __init__(
        self,
        *,
        schema_version: str = "2024-11-05",
        strict_schema: bool = True,
    ) -> None:
        """
        Initialize the MCP compiler.

        Args:
            schema_version: MCP protocol version
            strict_schema: Whether to enforce strict JSON Schema validation
        """
        self.schema_version = schema_version
        self.strict_schema = strict_schema

    def compile_tool_definition(
        self,
        skill_metadata: dict[str, Any],
        *,
        tool_name: str | None = None,
    ) -> MCPToolDefinition:
        """
        Generate an MCP tool definition from skill metadata.

        Args:
            skill_metadata: Parsed skill metadata from frontmatter
            tool_name: Optional override for tool name

        Returns:
            MCPToolDefinition with valid JSON Schema inputSchema
        """
        name = tool_name or skill_metadata.get("name", "unknown-skill")
        description = skill_metadata.get("description", "")
        parameters = skill_metadata.get("parameters", {})

        # Build valid JSON Schema for inputSchema
        input_schema = self._build_input_schema(parameters)

        return MCPToolDefinition(
            name=self._sanitize_tool_name(name),
            description=description,
            input_schema=input_schema,
        )

    def compile_from_frontmatter(
        self,
        fm: FrontmatterResult,
        *,
        tool_name: str | None = None,
    ) -> MCPToolDefinition:
        """
        Generate an MCP tool definition from parsed frontmatter.

        Args:
            fm: Parsed frontmatter result
            tool_name: Optional override for tool name

        Returns:
            MCPToolDefinition with valid JSON Schema inputSchema
        """
        name = tool_name or fm.name or "unknown-skill"
        description = fm.description or ""
        parameters = fm.parameters or {}

        input_schema = self._build_input_schema(parameters)

        return MCPToolDefinition(
            name=self._sanitize_tool_name(name),
            description=description,
            input_schema=input_schema,
        )

    def _build_input_schema(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build a valid JSON Schema Draft-07 inputSchema.

        Ensures the schema conforms to MCP tool inputSchema requirements:
        - Must be a valid JSON Schema object
        - Should have $schema declaration
        - Should define type as "object"
        - Should have properties for parameter definitions

        Args:
            parameters: Raw parameters from skill definition

        Returns:
            Valid JSON Schema object
        """
        # If parameters already looks like a complete schema, validate it
        if "$schema" in parameters or "type" in parameters:
            return self._validate_and_fix_schema(parameters)

        # Otherwise, wrap in a proper schema
        schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "object",
        }

        if parameters:
            schema["properties"] = {}
            schema["additionalProperties"] = True

            for param_name, param_def in parameters.items():
                schema["properties"][param_name] = self._normalize_param_schema(param_def)

                # Track required parameters
                if isinstance(param_def, dict) and param_def.get("required"):
                    if "required" not in schema:
                        schema["required"] = []
                    schema["required"].append(param_name)

        return schema

    def _validate_and_fix_schema(
        self,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate and fix a JSON Schema for MCP compatibility.

        Args:
            schema: Schema to validate

        Returns:
            Fixed schema
        """
        fixed = schema.copy()

        # Ensure $schema declaration
        if "$schema" not in fixed and self.strict_schema:
            fixed["$schema"] = "https://json-schema.org/draft-07/schema#"

        # Ensure type is defined
        if "type" not in fixed and "oneOf" not in fixed and "anyOf" not in fixed:
            fixed["type"] = "object"

        return fixed

    def _normalize_param_schema(
        self,
        param_def: Any,
    ) -> dict[str, Any]:
        """
        Normalize a parameter definition to valid JSON Schema.

        Args:
            param_def: Raw parameter definition

        Returns:
            Normalized JSON Schema for the parameter
        """
        if not isinstance(param_def, dict):
            # Simple type hint
            return {"type": self._infer_type(param_def)}

        normalized: dict[str, Any] = {}

        # Copy type if present
        if "type" in param_def:
            normalized["type"] = param_def["type"]
        elif "oneOf" in param_def or "anyOf" in param_def:
            # Allow complex type definitions
            normalized.update({k: v for k, v in param_def.items() if k != "required"})
            return normalized
        else:
            normalized["type"] = "string"  # Default to string

        # Copy other schema properties
        for key in ("description", "enum", "default", "minimum", "maximum",
                    "minLength", "maxLength", "pattern", "format",
                    "items", "properties", "additionalProperties"):
            if key in param_def:
                normalized[key] = param_def[key]

        return normalized

    def _infer_type(self, value: Any) -> str:
        """Infer JSON Schema type from a value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"

    def _sanitize_tool_name(self, name: str) -> str:
        """
        Sanitize tool name for MCP compatibility.

        Tool names should be lowercase with hyphens, matching
        pattern: ^[a-z][a-z0-9_-]*$
        """
        # Convert to lowercase
        sanitized = name.lower()
        # Replace spaces and underscores with hyphens
        sanitized = re.sub(r"[\s_]+", "-", sanitized)
        # Remove invalid characters
        sanitized = re.sub(r"[^a-z0-9_-]", "", sanitized)
        # Ensure starts with letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "tool-" + sanitized
        return sanitized or "unnamed-tool"


# ============================================================================
# Hook Compiler (Task 2.7.2)
# ============================================================================

class HookCompiler:
    """
    Generates Kiro Agent Hook definitions from skill specifications.

    Supports PreToolUse, PostToolUse, FileEdited triggers and generates
    valid Kiro hook JSON configurations.

    Task 2.7.2: Hook Compiler
    Validates: Requirements 5.3

    Example:
        >>> compiler = HookCompiler()
        >>> hook = compiler.compile_hook(skill_metadata, trigger=HookTrigger.PRE_TOOL_USE)
        >>> hook.name
        'SkillForge: my-skill'
    """

    def __init__(
        self,
        *,
        default_timeout: int = 60,
        default_enabled: bool = True,
    ) -> None:
        """
        Initialize the hook compiler.

        Args:
            default_timeout: Default timeout in seconds for hooks
            default_enabled: Whether hooks are enabled by default
        """
        self.default_timeout = default_timeout
        self.default_enabled = default_enabled

    def compile_hook(
        self,
        skill_metadata: dict[str, Any],
        *,
        trigger: HookTrigger | str = HookTrigger.PRE_TOOL_USE,
        matcher: str | None = None,
        action_type: HookActionType = HookActionType.COMMAND,
        command: str | None = None,
        prompt: str | None = None,
        description: str | None = None,
        timeout: int | None = None,
        enabled: bool | None = None,
        async_execution: bool = False,
    ) -> HookDefinition:
        """
        Compile a skill to a Kiro Agent Hook definition.

        Args:
            skill_metadata: Parsed skill metadata from frontmatter
            trigger: Hook trigger type
            matcher: Optional regex matcher for trigger
            action_type: Type of action (command or agent)
            command: Command to execute (for command type)
            prompt: Prompt to inject (for agent type)
            description: Hook description
            timeout: Timeout in seconds
            enabled: Whether hook is enabled
            async_execution: Whether to execute asynchronously

        Returns:
            HookDefinition for the skill
        """
        trigger_enum = trigger if isinstance(trigger, HookTrigger) else HookTrigger(trigger)

        skill_name = skill_metadata.get("name", "unknown-skill")
        skill_description = skill_metadata.get("description", "")

        # Build default command if not provided
        if action_type == HookActionType.COMMAND and not command:
            command = f"skillforge invoke {skill_name}"

        return HookDefinition(
            name=f"SkillForge: {skill_name}",
            trigger=trigger_enum,
            action_type=action_type,
            description=description or skill_description,
            matcher=matcher,
            timeout=timeout if timeout is not None else self.default_timeout,
            enabled=enabled if enabled is not None else self.default_enabled,
            command=command,
            prompt=prompt,
            async_execution=async_execution,
        )

    def compile_from_frontmatter(
        self,
        fm: FrontmatterResult,
        *,
        trigger: HookTrigger | str = HookTrigger.PRE_TOOL_USE,
        matcher: str | None = None,
        **kwargs: Any,
    ) -> HookDefinition:
        """
        Compile from parsed frontmatter.

        Args:
            fm: Parsed frontmatter result
            trigger: Hook trigger type
            matcher: Optional regex matcher
            **kwargs: Additional hook options

        Returns:
            HookDefinition for the skill
        """
        metadata = {
            "name": fm.name or "unknown-skill",
            "description": fm.description or "",
            "parameters": fm.parameters,
        }
        return self.compile_hook(metadata, trigger=trigger, matcher=matcher, **kwargs)

    def compile_hook_json(
        self,
        skill_metadata: dict[str, Any],
        *,
        trigger: HookTrigger | str = HookTrigger.PRE_TOOL_USE,
        **kwargs: Any,
    ) -> str:
        """
        Compile a skill to Kiro hook JSON format.

        Generates a complete v1 hook file with proper structure.

        Args:
            skill_metadata: Parsed skill metadata
            trigger: Hook trigger type
            **kwargs: Additional hook options

        Returns:
            JSON string of hook configuration
        """
        hook_def = self.compile_hook(skill_metadata, trigger=trigger, **kwargs)

        hook_config = {
            "version": "v1",
            "hooks": [hook_def.to_dict()],
        }

        return json.dumps(hook_config, indent=2)

    def compile_multiple_hooks(
        self,
        hooks: list[HookDefinition],
    ) -> str:
        """
        Compile multiple hook definitions into a single hook file.

        Args:
            hooks: List of HookDefinition objects

        Returns:
            JSON string of combined hook configuration
        """
        hook_config = {
            "version": "v1",
            "hooks": [h.to_dict() for h in hooks],
        }

        return json.dumps(hook_config, indent=2)


# ============================================================================
# Runtime Validator (Task 2.7.3)
# ============================================================================

@dataclass
class RuntimeValidationResult:
    """Result of runtime artifact validation."""

    is_valid: bool = True
    artifact_type: str = ""  # "python" or "typescript"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "isValid": self.is_valid,
            "artifactType": self.artifact_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "checksPassed": self.checks_passed,
            "metadata": self.metadata,
        }


class RuntimeValidator:
    """
    Validates output formats for Python and TypeScript artifacts.

    Validates that generated artifacts are syntactically correct and
    follow best practices for each runtime.

    Task 2.7.3: Runtime Validator
    Validates: Requirements 5.4, 5.6

    Example:
        >>> validator = RuntimeValidator()
        >>> result = validator.validate_python("print('hello')")
        >>> result.is_valid
        True
    """

    def __init__(
        self,
        *,
        strict_mode: bool = False,
        check_style: bool = True,
    ) -> None:
        """
        Initialize the runtime validator.

        Args:
            strict_mode: Enable stricter validation rules
            check_style: Whether to check code style issues
        """
        self.strict_mode = strict_mode
        self.check_style = check_style

    def validate_python(
        self,
        code: str,
        *,
        check_imports: bool = True,
        check_docstrings: bool = True,
    ) -> RuntimeValidationResult:
        """
        Validate Python artifact code.

        Checks:
        - Syntax validity via AST parsing
        - Import statement correctness
        - Function/class definitions
        - Docstring presence (optional)

        Args:
            code: Python source code to validate
            check_imports: Whether to validate imports
            check_docstrings: Whether to check docstrings

        Returns:
            RuntimeValidationResult with validation status
        """
        result = RuntimeValidationResult(artifact_type="python")
        checks_passed: list[str] = []

        # Syntax check via AST parsing
        try:
            tree = ast.parse(code)
            checks_passed.append("syntax_valid")
        except SyntaxError as e:
            result.errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            result.is_valid = False
            return result

        # Check for required elements
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        if imports:
            checks_passed.append("has_imports")
        if functions:
            checks_passed.append("has_functions")
        if classes:
            checks_passed.append("has_classes")

        # Check imports if requested
        if check_imports:
            import_errors = self._validate_python_imports(imports)
            if import_errors:
                result.warnings.extend(import_errors)
            else:
                checks_passed.append("imports_valid")

        # Check docstrings if requested
        if check_docstrings and self.check_style:
            missing_docstrings = self._check_python_docstrings(tree)
            if missing_docstrings:
                result.warnings.extend(missing_docstrings)
            else:
                checks_passed.append("docstrings_present")

        # Style checks
        if self.check_style:
            style_issues = self._check_python_style(code)
            if style_issues:
                result.warnings.extend(style_issues)

        # Metadata
        result.checks_passed = checks_passed
        result.metadata = {
            "import_count": len(imports),
            "function_count": len(functions),
            "class_count": len(classes),
            "line_count": len(code.splitlines()),
        }

        return result

    def validate_typescript(
        self,
        code: str,
        *,
        check_exports: bool = True,
    ) -> RuntimeValidationResult:
        """
        Validate TypeScript artifact code.

        Checks:
        - Basic syntax patterns
        - Export statements
        - Type annotations (basic check)
        - Common TypeScript patterns

        Args:
            code: TypeScript source code to validate
            check_exports: Whether to check for exports

        Returns:
            RuntimeValidationResult with validation status
        """
        result = RuntimeValidationResult(artifact_type="typescript")
        checks_passed: list[str] = []

        lines = code.splitlines()

        # Basic syntax pattern checks (TypeScript requires a proper parser for full validation)
        # Check for balanced braces
        open_braces = code.count("{")
        close_braces = code.count("}")
        open_parens = code.count("(")
        close_parens = code.count(")")
        open_brackets = code.count("[")
        close_brackets = code.count("]")

        if open_braces != close_braces:
            result.errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
            result.is_valid = False
        else:
            checks_passed.append("braces_balanced")

        if open_parens != close_parens:
            result.errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
            result.is_valid = False
        else:
            checks_passed.append("parentheses_balanced")

        if open_brackets != close_brackets:
            result.errors.append(f"Unbalanced brackets: {open_brackets} open, {close_brackets} close")
            result.is_valid = False
        else:
            checks_passed.append("brackets_balanced")

        if not result.is_valid:
            return result

        # Check for TypeScript-specific patterns
        has_types = bool(re.search(r":\s*(string|number|boolean|any|void|never|object)", code))
        has_interfaces = "interface " in code
        has_generics = "<" in code and ">" in code
        has_async = "async " in code or "await " in code

        if has_types:
            checks_passed.append("has_type_annotations")
        if has_interfaces:
            checks_passed.append("has_interfaces")
        if has_async:
            checks_passed.append("has_async_code")

        # Check exports
        if check_exports:
            has_export = "export " in code
            has_default_export = "export default" in code

            if has_export:
                checks_passed.append("has_exports")
            elif self.strict_mode:
                result.warnings.append("No export statements found")

        # Check for common issues
        if self.check_style:
            # Check for 'any' type usage
            if re.search(r":\s*any\b", code):
                result.warnings.append("Uses 'any' type which reduces type safety")

            # Check for console.log in non-test files
            if "console.log" in code and "test" not in code.lower():
                result.warnings.append("Contains console.log statements")

        # Metadata
        result.checks_passed = checks_passed
        result.metadata = {
            "line_count": len(lines),
            "has_types": has_types,
            "has_interfaces": has_interfaces,
            "has_generics": has_generics,
            "has_async": has_async,
        }

        return result

    def validate_json_schema(
        self,
        schema: dict[str, Any],
    ) -> RuntimeValidationResult:
        """
        Validate a JSON Schema definition.

        Args:
            schema: JSON Schema to validate

        Returns:
            RuntimeValidationResult with validation status
        """
        result = RuntimeValidationResult(artifact_type="json_schema")
        checks_passed: list[str] = []

        # Check required schema elements
        if "$schema" in schema:
            checks_passed.append("has_schema_declaration")
        else:
            result.warnings.append("Missing $schema declaration")

        if "type" in schema:
            checks_passed.append("has_type_definition")
        else:
            if "oneOf" not in schema and "anyOf" not in schema and "allOf" not in schema:
                result.warnings.append("Missing type definition")

        # Validate properties if present
        if "properties" in schema:
            props = schema["properties"]
            if not isinstance(props, dict):
                result.errors.append("properties must be an object")
                result.is_valid = False
            else:
                checks_passed.append("valid_properties")
                for prop_name, prop_def in props.items():
                    if not isinstance(prop_def, dict):
                        result.errors.append(f"Property '{prop_name}' must be an object")
                        result.is_valid = False

        # Validate required array if present
        if "required" in schema:
            required = schema["required"]
            if not isinstance(required, list):
                result.errors.append("required must be an array")
                result.is_valid = False
            else:
                checks_passed.append("valid_required")

        result.checks_passed = checks_passed
        return result

    def _validate_python_imports(
        self,
        imports: list[ast.Import | ast.ImportFrom],
    ) -> list[str]:
        """Validate Python import statements."""
        warnings: list[str] = []

        for imp in imports:
            if isinstance(imp, ast.ImportFrom):
                module = imp.module or ""
                # Check for deprecated modules
                if module in ("pickle", "marshal"):
                    warnings.append(f"Import from '{module}' may have security implications")
                elif module == "typing" and hasattr(imp, "names"):
                    # Check for deprecated typing imports
                    deprecated = {"Text", "StringIO", "BytesIO"}
                    for alias in imp.names:
                        if alias.name in deprecated:
                            warnings.append(f"typing.{alias.name} is deprecated")

        return warnings

    def _check_python_docstrings(
        self,
        tree: ast.Module,
    ) -> list[str]:
        """Check for missing docstrings in functions and classes."""
        warnings: list[str] = []

        # Check module docstring
        if not ast.get_docstring(tree):
            warnings.append("Module missing docstring")

        # Check function/class docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node) and not node.name.startswith("_"):
                    warnings.append(f"Function '{node.name}' missing docstring")
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    warnings.append(f"Class '{node.name}' missing docstring")

        return warnings

    def _check_python_style(
        self,
        code: str,
    ) -> list[str]:
        """Check Python code style issues."""
        warnings: list[str] = []
        lines = code.splitlines()

        for i, line in enumerate(lines, start=1):
            # Check line length
            if len(line) > 100:
                warnings.append(f"Line {i} exceeds 100 characters")

            # Check for tabs
            if "\t" in line:
                warnings.append(f"Line {i} contains tabs instead of spaces")

            # Check for trailing whitespace
            if line.rstrip() != line:
                warnings.append(f"Line {i} has trailing whitespace")

        return warnings


# ============================================================================
# Main Skill Compiler
# ============================================================================

class SkillCompiler:
    """
    Compiles skills to various runtime formats.

    Main entry point for skill compilation, integrating MCP compiler,
    hook compiler, and runtime validator.

    Supported outputs:
    - MCP stdio server (Python)
    - Kiro Agent Hooks (JSON)
    - Kiro Steering documents (Markdown)

    Example:
        >>> compiler = SkillCompiler()
        >>> result = compiler.compile_to_mcp(Path("skills/my-skill/SKILL.md"))
        >>> result.is_successful
        True
    """

    def __init__(
        self,
        *,
        output_dir: Path | None = None,
        python_executable: str = "python3",
    ) -> None:
        """
        Initialize the compiler.

        Args:
            output_dir: Directory to write compiled outputs
            python_executable: Python executable for MCP server shebang
        """
        self.output_dir = output_dir
        self.python_executable = python_executable
        self._mcp_compiler = MCPCompiler()
        self._hook_compiler = HookCompiler()
        self._runtime_validator = RuntimeValidator()

    def compile_to_mcp(
        self,
        skill_path: Path | str,
        *,
        server_name: str | None = None,
    ) -> CompilationResult:
        """
        Compile a skill to an MCP stdio server.

        Args:
            skill_path: Path to SKILL.md file
            server_name: Optional name for the MCP server

        Returns:
            CompilationResult with generated server code
        """
        path = Path(skill_path)
        result = CompilationResult(output_type="mcp_server")

        # Parse skill
        fm = parse_frontmatter_file(path)
        if not fm.is_valid:
            result.is_successful = False
            result.errors.extend(fm.errors)
            return result

        # Extract tool definition
        tool_name = fm.name or path.parent.name
        tool_def = MCPToolDefinition(
            name=tool_name,
            description=fm.description or "",
            input_schema=fm.parameters or {"type": "object", "properties": {}},
        )

        # Generate MCP server code
        result.generated_code = self._generate_mcp_server_code(tool_def, server_name)
        result.metadata["tool_name"] = tool_name
        result.metadata["server_name"] = server_name or f"{tool_name}-server"

        return result

    def compile_to_mcp_content(
        self,
        content: str,
        *,
        server_name: str | None = None,
    ) -> CompilationResult:
        """
        Compile skill content directly to an MCP stdio server.

        Args:
            content: Raw skill content with frontmatter
            server_name: Optional name for the MCP server

        Returns:
            CompilationResult with generated server code
        """
        result = CompilationResult(output_type="mcp_server")

        # Parse skill
        fm = parse_frontmatter(content)
        if not fm.is_valid:
            result.is_successful = False
            result.errors.extend(fm.errors)
            return result

        # Extract tool definition
        tool_name = fm.name or "unknown-skill"
        tool_def = MCPToolDefinition(
            name=tool_name,
            description=fm.description or "",
            input_schema=fm.parameters or {"type": "object", "properties": {}},
        )

        # Generate MCP server code
        result.generated_code = self._generate_mcp_server_code(tool_def, server_name)
        result.metadata["tool_name"] = tool_name
        result.metadata["server_name"] = server_name or f"{tool_name}-server"

        return result

    def compile_to_hook(
        self,
        skill_path: Path | str,
        *,
        trigger: str = "PreToolUse",
        matcher: str | None = None,
    ) -> CompilationResult:
        """
        Compile a skill to a Kiro Agent Hook.

        Args:
            skill_path: Path to SKILL.md file
            trigger: Hook trigger type
            matcher: Optional regex matcher for trigger

        Returns:
            CompilationResult with generated hook JSON
        """
        path = Path(skill_path)
        result = CompilationResult(output_type="kiro_hook")

        # Parse skill
        fm = parse_frontmatter_file(path)
        if not fm.is_valid:
            result.is_successful = False
            result.errors.extend(fm.errors)
            return result

        # Generate hook configuration
        hook_name = fm.name or path.parent.name
        hook_config = {
            "version": "v1",
            "hooks": [
                {
                    "name": f"SkillForge: {hook_name}",
                    "description": fm.description or f"Hook generated from skill: {hook_name}",
                    "trigger": trigger,
                    "matcher": matcher or ".*",
                    "timeout": 60,
                    "enabled": True,
                    "action": {
                        "type": "command",
                        "command": f"skillforge invoke {hook_name}",
                    },
                }
            ],
        }

        # Add parameters from skill
        if fm.parameters:
            hook_config["hooks"][0]["parameters"] = fm.parameters

        result.generated_code = json.dumps(hook_config, indent=2)
        result.metadata["hook_name"] = hook_name
        result.metadata["trigger"] = trigger

        return result

    def compile_to_hook_content(
        self,
        content: str,
        *,
        trigger: str = "PreToolUse",
        matcher: str | None = None,
    ) -> CompilationResult:
        """
        Compile skill content directly to a Kiro Agent Hook.

        Args:
            content: Raw skill content with frontmatter
            trigger: Hook trigger type
            matcher: Optional regex matcher for trigger

        Returns:
            CompilationResult with generated hook JSON
        """
        result = CompilationResult(output_type="kiro_hook")

        # Parse skill
        fm = parse_frontmatter(content)
        if not fm.is_valid:
            result.is_successful = False
            result.errors.extend(fm.errors)
            return result

        # Generate hook configuration
        hook_name = fm.name or "unknown-skill"
        hook_config = {
            "version": "v1",
            "hooks": [
                {
                    "name": f"SkillForge: {hook_name}",
                    "description": fm.description or f"Hook generated from skill: {hook_name}",
                    "trigger": trigger,
                    "matcher": matcher or ".*",
                    "timeout": 60,
                    "enabled": True,
                    "action": {
                        "type": "command",
                        "command": f"skillforge invoke {hook_name}",
                    },
                }
            ],
        }

        # Add parameters from skill
        if fm.parameters:
            hook_config["hooks"][0]["parameters"] = fm.parameters

        result.generated_code = json.dumps(hook_config, indent=2)
        result.metadata["hook_name"] = hook_name
        result.metadata["trigger"] = trigger

        return result

    def compile_to_steering(
        self,
        skill_path: Path | str,
        *,
        inclusion: str = "auto",
    ) -> CompilationResult:
        """
        Compile a skill to a Kiro Steering document.

        Args:
            skill_path: Path to SKILL.md file
            inclusion: Steering inclusion mode

        Returns:
            CompilationResult with generated steering markdown
        """
        path = Path(skill_path)
        result = CompilationResult(output_type="steering")

        # Parse skill
        fm = parse_frontmatter_file(path)
        if not fm.is_valid:
            result.is_successful = False
            result.errors.extend(fm.errors)
            return result

        skill_name = fm.name or path.parent.name
        version = fm.version or "1.0.0"

        # Generate steering document
        lines: list[str] = [
            "---",
            f'inclusion: {inclusion}',
            "---",
            "",
            f"# {skill_name}",
            "",
        ]

        if fm.description:
            lines.append(f"{fm.description}")
            lines.append("")

        if fm.triggers:
            lines.append("## Triggers")
            lines.append("")
            for trigger in fm.triggers:
                lines.append(f"- {trigger}")
            lines.append("")

        if fm.body:
            lines.append("## Skill Content")
            lines.append("")
            lines.append(fm.body)
            lines.append("")

        if fm.parameters:
            lines.append("## Parameters Schema")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(fm.parameters, indent=2))
            lines.append("```")
            lines.append("")

        result.generated_code = "\n".join(lines)
        result.metadata["skill_name"] = skill_name
        result.metadata["version"] = version
        result.metadata["inclusion"] = inclusion

        return result

    def _generate_mcp_server_code(
        self,
        tool: MCPToolDefinition,
        server_name: str | None,
    ) -> str:
        """Generate Python MCP server code for a tool."""
        name = server_name or f"{tool.name}-server"

        return f'''#!/usr/bin/env {self.python_executable}
"""
MCP Server: {name}
Generated by Kiro-SkillForge

This server exposes the '{tool.name}' skill as an MCP tool.
"""

import json
import sys
from typing import Any


def get_tool_definition() -> dict[str, Any]:
    """Return the MCP tool definition."""
    return {{
        "name": "{tool.name}",
        "description": {json.dumps(tool.description)},
        "inputSchema": {json.dumps(tool.input_schema, indent=12)}
    }}


def handle_tool_call(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Handle a tool call with the provided arguments.

    Args:
        arguments: Tool input arguments matching inputSchema

    Returns:
        List of content items (text, image, etc.)
    """
    # TODO: Implement skill logic here
    result = f"Skill '{tool.name}' executed with arguments: {{arguments}}"

    return [
        {{"type": "text", "text": result}}
    ]


def main() -> None:
    """Run the MCP stdio server."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            method = request.get("method", "")
            request_id = request.get("id")

            if method == "initialize":
                response = {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{
                        "protocolVersion": "2024-11-05",
                        "capabilities": {{
                            "tools": {{}}
                        }},
                        "serverInfo": {{
                            "name": "{name}",
                            "version": "1.0.0"
                        }}
                    }}
                }}

            elif method == "tools/list":
                response = {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {{
                        "tools": [get_tool_definition()]
                    }}
                }}

            elif method == "tools/call":
                params = request.get("params", {{}})
                tool_name = params.get("name")

                if tool_name == "{tool.name}":
                    arguments = params.get("arguments", {{}})
                    content = handle_tool_call(arguments)
                    response = {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {{
                            "content": content
                        }}
                    }}
                else:
                    response = {{
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {{
                            "code": -32601,
                            "message": f"Unknown tool: {{tool_name}}"
                        }}
                    }}

            else:
                response = {{
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {{
                        "code": -32601,
                        "message": f"Unknown method: {{method}}"
                    }}
                }}

            sys.stdout.write(json.dumps(response) + "\\n")
            sys.stdout.flush()

        except json.JSONDecodeError as e:
            error_response = {{
                "jsonrpc": "2.0",
                "id": None,
                "error": {{
                    "code": -32700,
                    "message": f"Parse error: {{e}}"
                }}
            }}
            sys.stdout.write(json.dumps(error_response) + "\\n")
            sys.stdout.flush()

        except Exception as e:
            error_response = {{
                "jsonrpc": "2.0",
                "id": None,
                "error": {{
                    "code": -32603,
                    "message": f"Internal error: {{e}}"
                }}
            }}
            sys.stdout.write(json.dumps(error_response) + "\\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
'''
