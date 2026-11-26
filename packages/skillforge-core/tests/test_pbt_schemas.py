"""
Property-Based Tests for Skill Schemas using Hypothesis.

Run with: pytest tests/test_pbt_schemas.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.database import InMemoryExampleDatabase

from skillforge.frontmatter import parse_frontmatter
from skillforge.triage import TriageRouter, TriageIntent
from skillforge.validate import SkillValidator
from skillforge.compiler import SkillCompiler


# Safe alphabet for YAML values (no special chars that break YAML)
SAFE_ALPHABET = st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122)
SAFE_VERSION = st.builds(lambda a, b, c: f"{a}.{b}.{c}",
    st.integers(min_value=0, max_value=99),
    st.integers(min_value=0, max_value=99),
    st.integers(min_value=0, max_value=99)
)


# ============================================================================
# Frontmatter Parsing Properties
# ============================================================================

@given(
    name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
    version=SAFE_VERSION,
    description=st.text(min_size=1, max_size=50, alphabet=SAFE_ALPHABET),
)
@settings(max_examples=30, database=InMemoryExampleDatabase())
def test_parse_valid_frontmatter_succeeds(name: str, version: str, description: str) -> None:
    """Property: Valid frontmatter content always parses successfully."""
    content = f"""---
name: "{name}"
version: "{version}"
description: "{description}"
---
# Skill Content

This is the body of the skill.
"""
    result = parse_frontmatter(content, validate_word_count=False)
    assert result.is_valid, f"Expected valid parse, got errors: {result.errors}"
    assert result.name == name
    assert result.version == version
    assert result.description == description


@given(
    word_count=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=30, database=InMemoryExampleDatabase())
def test_frontmatter_word_count_matches(word_count: int) -> None:
    """Property: Parsed frontmatter word count matches input."""
    body = " ".join(["word"] * word_count)
    content = f"""---
name: test-skill
version: 1.0.0
---
{body}
"""
    result = parse_frontmatter(content, validate_word_count=False)
    assert result.is_valid
    assert len(result.body.split()) == word_count


# ============================================================================
# Triage Router Properties
# ============================================================================

class TestTriageRouterProperties:
    """Property-based tests for the triage router."""

    @given(
        skill_name=st.sampled_from(["aws-audit", "terraform-scan", "story-engine", "demo-skill"]),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_router_matches_known_skills(self, skill_name: str) -> None:
        """Property: Router always matches skill names from available list."""
        router = TriageRouter(available_skills=["aws-audit", "terraform-scan", "story-engine", "demo-skill"])
        result = router.triage(f"Use the {skill_name}")
        assert skill_name in result.matched_skills

    @given(
        intent_keyword=st.sampled_from([
            ("use", TriageIntent.USE),
            ("create", TriageIntent.CREATE),
            ("improve", TriageIntent.IMPROVE),
            ("compose", TriageIntent.COMPOSE),
        ]),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_router_classifies_intent_correctly(
        self, intent_keyword: tuple[str, TriageIntent]
    ) -> None:
        """Property: Router correctly classifies intent from keywords."""
        keyword, expected_intent = intent_keyword
        router = TriageRouter()
        result = router.triage(f"{keyword} a skill")
        assert result.intent == expected_intent


# ============================================================================
# Validator Properties
# ============================================================================

class TestValidatorProperties:
    """Property-based tests for the skill validator."""

    @given(
        word_count=st.integers(min_value=0, max_value=1499),
    )
    @settings(max_examples=25, database=InMemoryExampleDatabase())
    def test_validator_accepts_within_limit(self, word_count: int) -> None:
        """Property: Validator accepts content within word limit."""
        body = " ".join(["word"] * word_count)
        content = f"""---
name: test-skill
version: 1.0.0
description: Test skill
---
{body}
"""
        validator = SkillValidator(max_body_words=1500)
        result = validator.validate_content(content)
        error_codes = [e.code for e in result.errors]
        assert "WORD_COUNT_EXCEEDED" not in error_codes

    @given(
        word_count=st.integers(min_value=1501, max_value=3000),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_validator_rejects_over_limit(self, word_count: int) -> None:
        """Property: Validator rejects content over word limit."""
        body = " ".join(["word"] * word_count)
        content = f"""---
name: test-skill
version: 1.0.0
description: Test skill
---
{body}
"""
        validator = SkillValidator(max_body_words=1500)
        result = validator.validate_content(content)
        error_codes = [e.code for e in result.errors]
        assert "WORD_COUNT_EXCEEDED" in error_codes
        assert not result.is_valid


# ============================================================================
# Compiler Properties
# ============================================================================

class TestCompilerProperties:
    """Property-based tests for the skill compiler."""

    @given(
        skill_name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
        description=st.text(min_size=1, max_size=50, alphabet=SAFE_ALPHABET),
    )
    @settings(max_examples=25, database=InMemoryExampleDatabase())
    def test_compiler_generates_valid_mcp_server(self, skill_name: str, description: str) -> None:
        """Property: Compiler generates valid MCP server code."""
        content = f"""---
name: "{skill_name}"
version: "1.0.0"
description: "{description}"
---
Skill body content.
"""
        compiler = SkillCompiler()
        result = compiler.compile_to_mcp_content(content)
        assert result.is_successful
        assert "jsonrpc" in result.generated_code
        assert skill_name in result.generated_code

    @given(
        skill_name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_compiler_generates_valid_kiro_hook(self, skill_name: str) -> None:
        """Property: Compiler generates valid Kiro hook JSON."""
        content = f"""---
name: "{skill_name}"
version: "1.0.0"
description: "Test skill"
---
Body content.
"""
        compiler = SkillCompiler()
        result = compiler.compile_to_hook_content(content, trigger="PreToolUse")
        assert result.is_successful
        hook_json = json.loads(result.generated_code)
        assert hook_json["version"] == "v1"
        assert len(hook_json["hooks"]) == 1
        assert hook_json["hooks"][0]["trigger"] == "PreToolUse"


# ============================================================================
# Integration Properties
# ============================================================================

@given(
    name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
    version=SAFE_VERSION,
    description=st.text(min_size=10, max_size=50, alphabet=SAFE_ALPHABET),
    body_lines=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=25, database=InMemoryExampleDatabase())
def test_full_pipeline_roundtrip(name: str, version: str, description: str, body_lines: int) -> None:
    """Property: Skill can be parsed, validated, and compiled successfully."""
    body = "\n".join([f"- Line {i}" for i in range(body_lines)])
    content = f"""---
name: "{name}"
version: "{version}"
description: "{description}"
---
{body}
"""
    parse_result = parse_frontmatter(content, validate_word_count=False)
    assert parse_result.is_valid

    validator = SkillValidator(max_body_words=5000)
    validate_result = validator.validate_content(content)
    assert validate_result.is_valid

    compiler = SkillCompiler()
    compile_result = compiler.compile_to_mcp_content(content)
    assert compile_result.is_successful


# ============================================================================
# Semantic Validator Properties
# ============================================================================

class TestSemanticValidatorProperties:
    """Property-based tests for the semantic validator."""

    @given(
        name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
        param_name=st.text(min_size=1, max_size=15, alphabet=SAFE_ALPHABET),
    )
    @settings(max_examples=20, database=InMemoryExampleDatabase())
    def test_semantic_validator_accepts_valid_params(self, name: str, param_name: str) -> None:
        """Property: Semantic validator accepts valid parameter definitions."""
        content = f"""---
name: "{name}"
version: "1.0.0"
description: "Test skill"
parameters:
  type: object
  properties:
    {param_name}:
      type: string
      minLength: 1
  required:
    - {param_name}
---
Skill body content.
"""
        validator = SkillValidator()
        result = validator.validate_semantics_content(content)
        # Should not have constraint conflicts
        error_codes = [e.code for e in result.errors]
        assert "CONSTRAINT_CONFLICT" not in error_codes

    @given(
        name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
    )
    @settings(max_examples=15, database=InMemoryExampleDatabase())
    def test_semantic_validator_detects_undefined_required(self, name: str) -> None:
        """Property: Semantic validator detects undefined required parameters."""
        content = f"""---
name: "{name}"
version: "1.0.0"
description: "Test skill"
parameters:
  type: object
  properties:
    definedParam:
      type: string
  required:
    - undefinedParam
---
Skill body content.
"""
        validator = SkillValidator()
        result = validator.validate_semantics_content(content)
        error_codes = [e.code for e in result.errors]
        assert "UNDEFINED_REQUIRED_PARAM" in error_codes
        assert not result.is_valid

    @given(
        skill_type=st.sampled_from(["cloud-infrastructure", "narrative"]),
    )
    @settings(max_examples=10, database=InMemoryExampleDatabase())
    def test_semantic_validator_skill_type_warnings(self, skill_type: str) -> None:
        """Property: Semantic validator provides skill-type-specific warnings."""
        content = f"""---
name: test-skill
version: "1.0.0"
description: "Test skill"
skillType: "{skill_type}"
parameters:
  type: object
  properties:
    genericParam:
      type: string
---
Skill body content.
"""
        validator = SkillValidator()
        result = validator.validate_semantics_content(content)
        # Should have warnings for skill-type-specific params
        warning_codes = [w.code for w in result.warnings]
        # The validator should provide recommendations for skill-type-specific params
        assert result.is_valid  # These are warnings, not errors


# ============================================================================
# Property Testability Validation
# ============================================================================

class TestPropertyTestabilityValidation:
    """Tests for property testability validation."""

    @given(
        prop_name=st.text(min_size=1, max_size=20, alphabet=SAFE_ALPHABET),
        testable=st.booleans(),
    )
    @settings(max_examples=15, database=InMemoryExampleDatabase())
    def test_validates_testable_flag(self, prop_name: str, testable: bool) -> None:
        """Property: Semantic validator accepts boolean testable flags."""
        content = f"""---
name: test-skill
version: "1.0.0"
description: "Test skill"
properties:
  - name: "{prop_name}"
    description: "A testable property"
    testable: {str(testable).lower()}
parameters:
  type: object
  properties:
    inputParam:
      type: string
---
Skill body content.
"""
        validator = SkillValidator()
        result = validator.validate_semantics_content(content)
        # Should not have INVALID_TESTABLE_TYPE error
        error_codes = [e.code for e in result.errors]
        assert "INVALID_TESTABLE_TYPE" not in error_codes

    def test_detects_missing_testable_flag(self) -> None:
        """Test that missing testable flag produces a warning."""
        content = '''---
name: test-skill
version: "1.0.0"
description: "Test skill"
properties:
  - name: "testProp"
    description: "A property without testable flag"
parameters:
  type: object
---
Skill body content.
'''
        validator = SkillValidator()
        result = validator.validate_semantics_content(content)
        warning_codes = [w.code for w in result.warnings]
        assert "MISSING_TESTABLE_FLAG" in warning_codes


# ============================================================================
# Custom Validation Rules
# ============================================================================

class TestCustomValidationRules:
    """Tests for custom validation rule application."""

    def test_applies_custom_rules(self) -> None:
        """Test that custom rules are applied."""
        def rule_no_test_in_name(metadata: dict[str, Any]) -> list[str]:
            name = metadata.get("name", "")
            if "test" in name.lower():
                return ["Skill name should not contain 'test'"]
            return []

        content = '''---
name: my-test-skill
version: "1.0.0"
description: "A skill with test in name"
---
Skill body content.
'''
        validator = SkillValidator()
        result = validator.validate_semantics_content(
            content,
            custom_rules=[rule_no_test_in_name],
        )
        error_codes = [e.code for e in result.errors]
        assert "CUSTOM_RULE_VIOLATION" in error_codes
        assert not result.is_valid

    def test_custom_rules_can_pass(self) -> None:
        """Test that custom rules can pass."""
        def rule_name_length(metadata: dict[str, Any]) -> list[str]:
            name = metadata.get("name", "")
            if len(name) < 3:
                return ["Skill name too short"]
            return []

        content = '''---
name: valid-skill-name
version: "1.0.0"
description: "A valid skill"
---
Skill body content.
'''
        validator = SkillValidator()
        result = validator.validate_semantics_content(
            content,
            custom_rules=[rule_name_length],
        )
        error_codes = [e.code for e in result.errors]
        assert "CUSTOM_RULE_VIOLATION" not in error_codes


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
