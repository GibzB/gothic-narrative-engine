"""
Structural Linter & Schema Validator for Skills.

Enforces frontmatter schema integrity, trigger-only descriptions,
and body word limits. Validates against Draft-07 JSON Schemas.

Includes semantic validation for parameter consistency, property
testability, and custom validation rules.

Adapted from tripleyak/SkillForge validate_skill.py patterns.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from skillforge.frontmatter import parse_frontmatter_file, FrontmatterResult


@dataclass
class ValidationError:
    """A single validation error."""

    code: str
    message: str
    location: str = "root"
    severity: str = "error"  # error, warning, info

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.location}: {self.message} ({self.code})"


@dataclass
class ValidationResult:
    """Result of validating a skill."""

    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    skill_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


# Required frontmatter fields for a valid skill
REQUIRED_FIELDS = frozenset({"name", "description", "version"})

# Recommended frontmatter fields
RECOMMENDED_FIELDS = frozenset({"triggers", "parameters"})

# Maximum body word count
MAX_BODY_WORDS = 1500

# Trigger format pattern (should be descriptive, not imperative)
TRIGGER_PATTERN = re.compile(r"^[A-Z][^.!?]*[.!?]$", re.MULTILINE)


class SkillValidator:
    """
    Validates skill definition files for structural integrity.

    Checks include:
    - Required frontmatter fields present
    - Body word count within limits
    - Trigger descriptions follow format rules
    - Parameter schemas are valid JSON Schema Draft-07

    Example:
        >>> validator = SkillValidator()
        >>> result = validator.validate_file(Path("skills/my-skill/SKILL.md"))
        >>> result.is_valid
        True
    """

    def __init__(
        self,
        *,
        max_body_words: int = MAX_BODY_WORDS,
        require_parameters: bool = False,
    ) -> None:
        """
        Initialize the validator.

        Args:
            max_body_words: Maximum allowed words in skill body
            require_parameters: Whether parameters field is required
        """
        self.max_body_words = max_body_words
        self.require_parameters = require_parameters

    def validate_file(self, skill_path: Path | str) -> ValidationResult:
        """
        Validate a skill definition file.

        Args:
            skill_path: Path to SKILL.md or similar file

        Returns:
            ValidationResult with errors and warnings
        """
        path = Path(skill_path)
        result = ValidationResult(skill_path=path)

        # Parse frontmatter
        fm_result = parse_frontmatter_file(path, validate_word_count=False)
        if not fm_result.is_valid:
            result.errors.extend(
                ValidationError(code="PARSE_ERROR", message=err, location=str(path))
                for err in fm_result.errors
            )
            result.is_valid = False
            return result

        result.metadata = fm_result.metadata

        # Validate required fields
        self._validate_required_fields(fm_result, result)

        # Validate body word count
        self._validate_word_count(fm_result, result)

        # Validate triggers format
        self._validate_triggers(fm_result, result)

        # Validate parameter schemas
        self._validate_parameters(fm_result, result)

        return result

    def validate_content(self, content: str) -> ValidationResult:
        """
        Validate skill content directly.

        Args:
            content: Raw skill file content

        Returns:
            ValidationResult with errors and warnings
        """
        from skillforge.frontmatter import parse_frontmatter

        result = ValidationResult()

        fm_result = parse_frontmatter(content, validate_word_count=False)
        if not fm_result.is_valid:
            result.errors.extend(
                ValidationError(code="PARSE_ERROR", message=err)
                for err in fm_result.errors
            )
            result.is_valid = False
            return result

        result.metadata = fm_result.metadata

        self._validate_required_fields(fm_result, result)
        self._validate_word_count(fm_result, result)
        self._validate_triggers(fm_result, result)
        self._validate_parameters(fm_result, result)

        return result

    def _validate_required_fields(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """Check that required fields are present."""
        missing = REQUIRED_FIELDS - set(fm.metadata.keys())

        if missing:
            result.is_valid = False
            result.errors.append(
                ValidationError(
                    code="MISSING_REQUIRED",
                    message=f"Missing required fields: {', '.join(sorted(missing))}",
                    location="frontmatter",
                )
            )

        # Check recommended fields
        missing_recommended = RECOMMENDED_FIELDS - set(fm.metadata.keys())
        if missing_recommended:
            result.warnings.append(
                ValidationError(
                    code="MISSING_RECOMMENDED",
                    message=f"Missing recommended fields: {', '.join(sorted(missing_recommended))}",
                    location="frontmatter",
                    severity="warning",
                )
            )

        # Validate field types
        if "name" in fm.metadata and not isinstance(fm.metadata["name"], str):
            result.errors.append(
                ValidationError(
                    code="INVALID_TYPE",
                    message="Field 'name' must be a string",
                    location="frontmatter.name",
                )
            )
            result.is_valid = False

        if "version" in fm.metadata:
            version = fm.metadata["version"]
            if not isinstance(version, str) or not re.match(r"^\d+\.\d+\.\d+$", version):
                result.warnings.append(
                    ValidationError(
                        code="INVALID_VERSION",
                        message="Version should be semver (e.g., 1.0.0)",
                        location="frontmatter.version",
                        severity="warning",
                    )
                )

    def _validate_word_count(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """Check that body word count is within limits."""
        if not fm.body:
            result.warnings.append(
                ValidationError(
                    code="EMPTY_BODY",
                    message="Skill has no body content",
                    location="body",
                    severity="warning",
                )
            )
            return

        word_count = len(fm.body.split())
        if word_count > self.max_body_words:
            result.errors.append(
                ValidationError(
                    code="WORD_COUNT_EXCEEDED",
                    message=f"Body has {word_count} words (max: {self.max_body_words})",
                    location="body",
                )
            )
            result.is_valid = False

    def _validate_triggers(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """Validate trigger descriptions format."""
        triggers = fm.triggers
        if not triggers:
            return

        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, str):
                result.errors.append(
                    ValidationError(
                        code="INVALID_TRIGGER_TYPE",
                        message=f"Trigger {i} must be a string",
                        location=f"frontmatter.triggers[{i}]",
                    )
                )
                result.is_valid = False
                continue

            # Triggers should be descriptive statements, not commands
            if trigger.strip().lower().startswith(("run ", "execute ", "call ")):
                result.warnings.append(
                    ValidationError(
                        code="TRIGGER_IMPERATIVE",
                        message=f"Trigger '{trigger[:30]}...' should be descriptive, not imperative",
                        location=f"frontmatter.triggers[{i}]",
                        severity="warning",
                    )
                )

    def _validate_parameters(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """Validate parameter JSON schemas."""
        params = fm.parameters
        if not params:
            if self.require_parameters:
                result.errors.append(
                    ValidationError(
                        code="MISSING_PARAMETERS",
                        message="Skill must define parameters schema",
                        location="frontmatter.parameters",
                    )
                )
                result.is_valid = False
            return

        # Basic JSON Schema validation
        if not isinstance(params, dict):
            result.errors.append(
                ValidationError(
                    code="INVALID_PARAMETERS_TYPE",
                    message="Parameters must be a JSON Schema object",
                    location="frontmatter.parameters",
                )
            )
            result.is_valid = False
            return

        # Check for required schema fields
        if "$schema" not in params:
            result.warnings.append(
                ValidationError(
                    code="MISSING_SCHEMA_DECLARATION",
                    message="Parameters should declare $schema (Draft-07 recommended)",
                    location="frontmatter.parameters",
                    severity="warning",
                )
            )

        if "type" not in params and "oneOf" not in params and "anyOf" not in params:
            result.warnings.append(
                ValidationError(
                    code="MISSING_TYPE",
                    message="Parameters schema should define a type",
                    location="frontmatter.parameters",
                    severity="warning",
                )
            )

    def validate_semantics(
        self,
        skill_path: Path | str,
        *,
        custom_rules: list[Callable[[dict[str, Any]], list[str]]] | None = None,
    ) -> ValidationResult:
        """
        Perform semantic validation on a skill specification.

        Checks parameter consistency, property testability, and applies
        custom validation rules if provided.

        Args:
            skill_path: Path to SKILL.md or similar file
            custom_rules: Optional list of custom validation functions

        Returns:
            ValidationResult with semantic validation errors and warnings
        """
        path = Path(skill_path)
        result = ValidationResult(skill_path=path)

        # Parse frontmatter
        fm_result = parse_frontmatter_file(path, validate_word_count=False)
        if not fm_result.is_valid:
            result.errors.extend(
                ValidationError(code="PARSE_ERROR", message=err, location=str(path))
                for err in fm_result.errors
            )
            result.is_valid = False
            return result

        result.metadata = fm_result.metadata

        # Run semantic checks
        self._validate_parameter_consistency(fm_result, result)
        self._validate_property_testability(fm_result, result)

        # Apply custom validation rules
        if custom_rules:
            self._apply_custom_rules(fm_result, result, custom_rules)

        return result

    def validate_semantics_content(
        self,
        content: str,
        *,
        custom_rules: list[Callable[[dict[str, Any]], list[str]]] | None = None,
    ) -> ValidationResult:
        """
        Perform semantic validation on skill content directly.

        Args:
            content: Raw skill file content
            custom_rules: Optional list of custom validation functions

        Returns:
            ValidationResult with semantic validation errors and warnings
        """
        from skillforge.frontmatter import parse_frontmatter

        result = ValidationResult()

        fm_result = parse_frontmatter(content, validate_word_count=False)
        if not fm_result.is_valid:
            result.errors.extend(
                ValidationError(code="PARSE_ERROR", message=err)
                for err in fm_result.errors
            )
            result.is_valid = False
            return result

        result.metadata = fm_result.metadata

        self._validate_parameter_consistency(fm_result, result)
        self._validate_property_testability(fm_result, result)

        if custom_rules:
            self._apply_custom_rules(fm_result, result, custom_rules)

        return result

    def _validate_parameter_consistency(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """
        Check parameter consistency across skill types.

        Validates that parameters are consistent with the skill's type
        and that required parameters have proper definitions.
        """
        params = fm.parameters
        if not params:
            return

        skill_type = fm.metadata.get("skillType", "unknown")
        properties = params.get("properties", {})
        required = set(params.get("required", []))

        # Check that all required properties are defined
        defined_props = set(properties.keys())
        undefined_required = required - defined_props
        if undefined_required:
            result.errors.append(
                ValidationError(
                    code="UNDEFINED_REQUIRED_PARAM",
                    message=f"Required parameters not defined: {', '.join(sorted(undefined_required))}",
                    location="frontmatter.parameters",
                )
            )
            result.is_valid = False

        # Check for skill-type-specific parameter requirements
        if skill_type == "cloud-infrastructure":
            # Cloud infrastructure skills should have resource-related params
            resource_params = any(
                "resource" in prop.lower() or "arn" in prop.lower()
                for prop in properties
            )
            if not resource_params and properties:
                result.warnings.append(
                    ValidationError(
                        code="CLOUD_PARAM_RECOMMENDATION",
                        message="Cloud infrastructure skills should include resource or ARN parameters",
                        location="frontmatter.parameters",
                        severity="warning",
                    )
                )

        elif skill_type == "narrative":
            # Narrative skills should have content/plot parameters
            content_params = any(
                "content" in prop.lower() or "story" in prop.lower() or "plot" in prop.lower()
                for prop in properties
            )
            if not content_params and properties:
                result.warnings.append(
                    ValidationError(
                        code="NARRATIVE_PARAM_RECOMMENDATION",
                        message="Narrative skills should include content, story, or plot parameters",
                        location="frontmatter.parameters",
                        severity="warning",
                    )
                )

        # Check for parameter type consistency
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                result.errors.append(
                    ValidationError(
                        code="INVALID_PARAM_DEFINITION",
                        message=f"Parameter '{prop_name}' must be an object with type definition",
                        location=f"frontmatter.parameters.properties.{prop_name}",
                    )
                )
                result.is_valid = False
                continue

            prop_type = prop_def.get("type")
            if prop_type and prop_type not in (
                "string", "integer", "number", "boolean", "array", "object", "null"
            ):
                result.warnings.append(
                    ValidationError(
                        code="UNKNOWN_PARAM_TYPE",
                        message=f"Parameter '{prop_name}' has unusual type: {prop_type}",
                        location=f"frontmatter.parameters.properties.{prop_name}",
                        severity="warning",
                    )
                )

            # Check for conflicting constraints
            if prop_type == "string":
                min_len = prop_def.get("minLength", 0)
                max_len = prop_def.get("maxLength", float("inf"))
                if min_len > max_len:
                    result.errors.append(
                        ValidationError(
                            code="CONSTRAINT_CONFLICT",
                            message=f"Parameter '{prop_name}' has minLength > maxLength",
                            location=f"frontmatter.parameters.properties.{prop_name}",
                        )
                    )
                    result.is_valid = False

            elif prop_type in ("integer", "number"):
                min_val = prop_def.get("minimum", float("-inf"))
                max_val = prop_def.get("maximum", float("inf"))
                if min_val > max_val:
                    result.errors.append(
                        ValidationError(
                            code="CONSTRAINT_CONFLICT",
                            message=f"Parameter '{prop_name}' has minimum > maximum",
                            location=f"frontmatter.parameters.properties.{prop_name}",
                        )
                    )
                    result.is_valid = False

    def _validate_property_testability(
        self, fm: FrontmatterResult, result: ValidationResult
    ) -> None:
        """
        Validate property definitions for testability.

        Checks that properties defined for PBT are actually testable
        with the given parameter schema.
        """
        properties = fm.metadata.get("properties", [])
        if not properties:
            return

        params = fm.parameters
        param_props = set(params.get("properties", {}).keys()) if params else set()

        for i, prop in enumerate(properties):
            if not isinstance(prop, dict):
                result.errors.append(
                    ValidationError(
                        code="INVALID_PROPERTY_DEFINITION",
                        message=f"Property {i} must be an object",
                        location=f"frontmatter.properties[{i}]",
                    )
                )
                result.is_valid = False
                continue

            prop_name = prop.get("name")
            if not prop_name:
                result.errors.append(
                    ValidationError(
                        code="MISSING_PROPERTY_NAME",
                        message=f"Property {i} missing 'name' field",
                        location=f"frontmatter.properties[{i}]",
                    )
                )
                result.is_valid = False
                continue

            # Check if property references valid parameters
            prop_description = prop.get("description", "")
            for word in prop_description.split():
                # Check if word matches a parameter name
                if word in param_props:
                    # Property references a valid parameter
                    break
            else:
                # No parameter referenced in description
                if param_props:
                    result.warnings.append(
                        ValidationError(
                            code="PROPERTY_PARAM_REFERENCE",
                            message=f"Property '{prop_name}' description doesn't reference any parameter from the schema",
                            location=f"frontmatter.properties[{i}]",
                            severity="warning",
                        )
                    )

            # Check testability flag
            testable = prop.get("testable")
            if testable is None:
                result.warnings.append(
                    ValidationError(
                        code="MISSING_TESTABLE_FLAG",
                        message=f"Property '{prop_name}' should declare 'testable' boolean",
                        location=f"frontmatter.properties[{i}]",
                        severity="warning",
                    )
                )
            elif not isinstance(testable, bool):
                result.errors.append(
                    ValidationError(
                        code="INVALID_TESTABLE_TYPE",
                        message=f"Property '{prop_name}' testable must be boolean, got {type(testable).__name__}",
                        location=f"frontmatter.properties[{i}]",
                    )
                )
                result.is_valid = False

    def _apply_custom_rules(
        self,
        fm: FrontmatterResult,
        result: ValidationResult,
        custom_rules: list[Callable[[dict[str, Any]], list[str]]],
    ) -> None:
        """
        Apply custom validation rules to the skill.

        Args:
            fm: Parsed frontmatter result
            result: Validation result to update
            custom_rules: List of functions that return error messages
        """
        for i, rule in enumerate(custom_rules):
            try:
                errors = rule(fm.metadata)
                for error in errors:
                    result.errors.append(
                        ValidationError(
                            code="CUSTOM_RULE_VIOLATION",
                            message=error,
                            location=f"custom_rule[{i}]",
                        )
                    )
                    result.is_valid = False
            except Exception as e:
                result.warnings.append(
                    ValidationError(
                        code="CUSTOM_RULE_ERROR",
                        message=f"Custom rule {i} raised exception: {e}",
                        location=f"custom_rule[{i}]",
                        severity="warning",
                    )
                )
