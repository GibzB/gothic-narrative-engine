"""
Tests for Wave 5 Compiler enhancements.

Tests for:
- Task 2.7.1: MCP Compiler
- Task 2.7.2: Hook Compiler
- Task 2.7.3: Runtime Validator
"""

import json
import pytest
from pathlib import Path

from skillforge.compiler import (
    MCPCompiler,
    MCPToolDefinition,
    HookCompiler,
    HookDefinition,
    HookTrigger,
    HookActionType,
    RuntimeValidator,
    RuntimeValidationResult,
    SkillCompiler,
    CompilationResult,
)
from skillforge.frontmatter import FrontmatterResult


# ============================================================================
# MCP Compiler Tests (Task 2.7.1)
# ============================================================================

class TestMCPCompiler:
    """Tests for MCPCompiler."""

    def test_compile_tool_definition_basic(self):
        """Test basic tool definition compilation."""
        compiler = MCPCompiler()
        
        skill_metadata = {
            "name": "test-skill",
            "description": "A test skill",
            "parameters": {},
        }
        
        tool_def = compiler.compile_tool_definition(skill_metadata)
        
        assert tool_def.name == "test-skill"
        assert tool_def.description == "A test skill"
        assert "type" in tool_def.input_schema
        assert tool_def.input_schema["type"] == "object"

    def test_compile_tool_definition_with_parameters(self):
        """Test tool definition with parameters."""
        compiler = MCPCompiler()
        
        skill_metadata = {
            "name": "my-skill",
            "description": "Skill with params",
            "parameters": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results"},
            },
        }
        
        tool_def = compiler.compile_tool_definition(skill_metadata)
        
        assert tool_def.name == "my-skill"
        assert "properties" in tool_def.input_schema
        assert "query" in tool_def.input_schema["properties"]
        assert "limit" in tool_def.input_schema["properties"]

    def test_compile_tool_definition_sanitizes_name(self):
        """Test that tool names are sanitized."""
        compiler = MCPCompiler()
        
        skill_metadata = {
            "name": "My Complex Skill Name!",
            "description": "Test",
        }
        
        tool_def = compiler.compile_tool_definition(skill_metadata)
        
        assert tool_def.name == "my-complex-skill-name"
        assert "!" not in tool_def.name
        assert " " not in tool_def.name

    def test_compile_from_frontmatter(self):
        """Test compilation from FrontmatterResult."""
        compiler = MCPCompiler()
        
        fm = FrontmatterResult(
            metadata={"name": "fm-skill", "description": "From frontmatter"},
            body="Test body",
            is_valid=True,
        )
        
        tool_def = compiler.compile_from_frontmatter(fm)
        
        assert tool_def.name == "fm-skill"
        assert tool_def.description == "From frontmatter"

    def test_build_input_schema_complete(self):
        """Test building complete input schema."""
        compiler = MCPCompiler()
        
        parameters = {
            "username": {"type": "string", "minLength": 3},
            "age": {"type": "integer", "minimum": 0},
        }
        
        schema = compiler._build_input_schema(parameters)
        
        assert "$schema" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "username" in schema["properties"]
        assert "age" in schema["properties"]

    def test_build_input_schema_with_existing_schema(self):
        """Test handling existing schema."""
        compiler = MCPCompiler()
        
        parameters = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }
        
        schema = compiler._build_input_schema(parameters)
        
        assert "$schema" in schema
        assert "properties" in schema

    def test_tool_definition_to_dict(self):
        """Test MCPToolDefinition.to_dict()."""
        tool_def = MCPToolDefinition(
            name="test-tool",
            description="Test description",
            input_schema={"type": "object"},
        )
        
        result = tool_def.to_dict()
        
        assert result["name"] == "test-tool"
        assert result["description"] == "Test description"
        assert "inputSchema" in result


# ============================================================================
# Hook Compiler Tests (Task 2.7.2)
# ============================================================================

class TestHookCompiler:
    """Tests for HookCompiler."""

    def test_compile_hook_basic(self):
        """Test basic hook compilation."""
        compiler = HookCompiler()
        
        skill_metadata = {
            "name": "test-skill",
            "description": "Test hook",
        }
        
        hook = compiler.compile_hook(skill_metadata)
        
        assert hook.name == "SkillForge: test-skill"
        assert hook.trigger == HookTrigger.PRE_TOOL_USE
        assert hook.action_type == HookActionType.COMMAND
        assert hook.enabled is True

    def test_compile_hook_with_trigger(self):
        """Test hook with specific trigger."""
        compiler = HookCompiler()
        
        skill_metadata = {"name": "my-skill", "description": "Test"}
        
        hook = compiler.compile_hook(
            skill_metadata,
            trigger=HookTrigger.POST_FILE_SAVE,
        )
        
        assert hook.trigger == HookTrigger.POST_FILE_SAVE

    def test_compile_hook_with_matcher(self):
        """Test hook with matcher pattern."""
        compiler = HookCompiler()
        
        skill_metadata = {"name": "my-skill", "description": "Test"}
        
        hook = compiler.compile_hook(
            skill_metadata,
            matcher=r".*\.py$",
        )
        
        assert hook.matcher == r".*\.py$"

    def test_compile_hook_agent_type(self):
        """Test hook with agent action type."""
        compiler = HookCompiler()
        
        skill_metadata = {"name": "agent-skill", "description": "Test"}
        
        hook = compiler.compile_hook(
            skill_metadata,
            action_type=HookActionType.AGENT,
            prompt="Load workspace rules",
        )
        
        assert hook.action_type == HookActionType.AGENT
        assert hook.prompt == "Load workspace rules"

    def test_compile_hook_json(self):
        """Test JSON hook compilation."""
        compiler = HookCompiler()
        
        skill_metadata = {"name": "json-skill", "description": "Test"}
        
        json_output = compiler.compile_hook_json(skill_metadata)
        
        # Verify it's valid JSON
        hook_config = json.loads(json_output)
        
        assert hook_config["version"] == "v1"
        assert len(hook_config["hooks"]) == 1
        assert hook_config["hooks"][0]["name"] == "SkillForge: json-skill"

    def test_compile_multiple_hooks(self):
        """Test compiling multiple hooks."""
        compiler = HookCompiler()
        
        hooks = [
            HookDefinition(
                name="Hook 1",
                trigger=HookTrigger.PRE_TOOL_USE,
                action_type=HookActionType.COMMAND,
                command="echo 'pre'",
            ),
            HookDefinition(
                name="Hook 2",
                trigger=HookTrigger.POST_FILE_SAVE,
                action_type=HookActionType.COMMAND,
                command="echo 'post'",
            ),
        ]
        
        json_output = compiler.compile_multiple_hooks(hooks)
        hook_config = json.loads(json_output)
        
        assert len(hook_config["hooks"]) == 2

    def test_hook_definition_to_dict(self):
        """Test HookDefinition.to_dict()."""
        hook = HookDefinition(
            name="test-hook",
            trigger=HookTrigger.PRE_TOOL_USE,
            action_type=HookActionType.COMMAND,
            description="Test hook",
            command="test --flag",
            matcher=".*",
            timeout=30,
        )
        
        result = hook.to_dict()
        
        assert result["name"] == "test-hook"
        assert result["trigger"] == "PreToolUse"
        assert result["action"]["type"] == "command"
        assert result["action"]["command"] == "test --flag"

    def test_all_trigger_types(self):
        """Test all hook trigger types are valid."""
        triggers = [
            HookTrigger.PRE_TOOL_USE,
            HookTrigger.POST_TOOL_USE,
            HookTrigger.POST_FILE_SAVE,
            HookTrigger.POST_FILE_CREATE,
            HookTrigger.POST_FILE_DELETE,
            HookTrigger.AGENT_SPAWN,
            HookTrigger.SESSION_START,
            HookTrigger.STOP,
        ]
        
        compiler = HookCompiler()
        skill_metadata = {"name": "test", "description": "Test"}
        
        for trigger in triggers:
            hook = compiler.compile_hook(skill_metadata, trigger=trigger)
            assert hook.trigger == trigger


# ============================================================================
# Runtime Validator Tests (Task 2.7.3)
# ============================================================================

class TestRuntimeValidator:
    """Tests for RuntimeValidator."""

    def test_validate_python_syntax_valid(self):
        """Test validating valid Python code."""
        validator = RuntimeValidator()
        
        code = '''
def hello():
    """Say hello."""
    print("Hello, World!")
'''
        
        result = validator.validate_python(code)
        
        assert result.is_valid
        assert "syntax_valid" in result.checks_passed

    def test_validate_python_syntax_invalid(self):
        """Test detecting invalid Python syntax."""
        validator = RuntimeValidator()
        
        code = "def broken(:\n    print('missing paren'"
        
        result = validator.validate_python(code)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Syntax error" in result.errors[0]

    def test_validate_python_with_imports(self):
        """Test Python code with imports."""
        validator = RuntimeValidator()
        
        code = '''
import os
from pathlib import Path

def get_cwd():
    return os.getcwd()
'''
        
        result = validator.validate_python(code)
        
        assert result.is_valid
        assert "has_imports" in result.checks_passed

    def test_validate_python_metadata(self):
        """Test Python validation metadata."""
        validator = RuntimeValidator()
        
        code = '''
def func1():
    pass

def func2():
    pass

class MyClass:
    pass
'''
        
        result = validator.validate_python(code)
        
        assert result.metadata["function_count"] == 2
        assert result.metadata["class_count"] == 1

    def test_validate_typescript_balanced(self):
        """Test validating balanced TypeScript code."""
        validator = RuntimeValidator()
        
        code = '''
interface User {
    name: string;
    age: number;
}

export function greet(user: User): string {
    return `Hello, ${user.name}!`;
}
'''
        
        result = validator.validate_typescript(code)
        
        assert result.is_valid
        assert "braces_balanced" in result.checks_passed
        assert "parentheses_balanced" in result.checks_passed

    def test_validate_typescript_unbalanced_braces(self):
        """Test detecting unbalanced braces in TypeScript."""
        validator = RuntimeValidator()
        
        code = '''
function broken() {
    return {
        x: 1
    // missing closing brace
'''
        
        result = validator.validate_typescript(code)
        
        assert not result.is_valid
        assert any("Unbalanced braces" in e for e in result.errors)

    def test_validate_typescript_type_annotations(self):
        """Test detecting TypeScript type annotations."""
        validator = RuntimeValidator()
        
        code = '''
export function add(a: number, b: number): number {
    return a + b;
}
'''
        
        result = validator.validate_typescript(code)
        
        assert "has_type_annotations" in result.checks_passed

    def test_validate_json_schema_valid(self):
        """Test validating valid JSON Schema."""
        validator = RuntimeValidator()
        
        schema = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        
        result = validator.validate_json_schema(schema)
        
        assert result.is_valid
        assert "has_schema_declaration" in result.checks_passed
        assert "has_type_definition" in result.checks_passed

    def test_validate_json_schema_missing_type(self):
        """Test JSON Schema missing type definition."""
        validator = RuntimeValidator()
        
        schema = {
            "$schema": "https://json-schema.org/draft-07/schema#",
            "properties": {"x": {"type": "string"}},
        }
        
        result = validator.validate_json_schema(schema)
        
        # Should have warning but still be valid
        assert "Missing type definition" in result.warnings[0]

    def test_validation_result_to_dict(self):
        """Test RuntimeValidationResult.to_dict()."""
        result = RuntimeValidationResult(
            is_valid=True,
            artifact_type="python",
            checks_passed=["syntax_valid"],
            metadata={"line_count": 10},
        )
        
        d = result.to_dict()
        
        assert d["isValid"] is True
        assert d["artifactType"] == "python"
        assert "syntax_valid" in d["checksPassed"]


# ============================================================================
# Skill Compiler Integration Tests
# ============================================================================

class TestSkillCompilerIntegration:
    """Integration tests for SkillCompiler."""

    def test_compile_to_mcp(self, tmp_path):
        """Test compiling skill to MCP server."""
        compiler = SkillCompiler(output_dir=tmp_path)
        
        # Create a test skill file
        skill_file = tmp_path / "test-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text("""---
name: test-skill
description: A test skill
version: 1.0.0
parameters:
  input:
    type: string
    description: Input to process
---

This is the skill body.
""")
        
        result = compiler.compile_to_mcp(skill_file)
        
        assert result.is_successful
        assert result.output_type == "mcp_server"
        assert "def get_tool_definition" in result.generated_code
        assert "test-skill" in result.generated_code

    def test_compile_to_hook(self, tmp_path):
        """Test compiling skill to hook."""
        compiler = SkillCompiler(output_dir=tmp_path)
        
        skill_file = tmp_path / "hook-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text("""---
name: hook-skill
description: A hook skill
version: 1.0.0
---

Skill body.
""")
        
        result = compiler.compile_to_hook(skill_file, trigger="PreToolUse")
        
        assert result.is_successful
        assert result.output_type == "kiro_hook"
        
        # Verify JSON is valid
        hook_config = json.loads(result.generated_code)
        assert hook_config["version"] == "v1"

    def test_compile_to_steering(self, tmp_path):
        """Test compiling skill to steering document."""
        compiler = SkillCompiler(output_dir=tmp_path)
        
        skill_file = tmp_path / "steering-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text("""---
name: steering-skill
description: A steering skill
version: 1.0.0
triggers:
  - When user asks about testing
---

This is steering content.
""")
        
        result = compiler.compile_to_steering(skill_file)
        
        assert result.is_successful
        assert result.output_type == "steering"
        assert "---" in result.generated_code  # YAML frontmatter
        assert "steering-skill" in result.generated_code
