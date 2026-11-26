"""
YAML Frontmatter Parser for SKILL.md files.

Parses and validates YAML frontmatter blocks from skill definition files,
enforcing schema integrity and extraction of metadata fields.

Adapted from tripleyak/SkillForge frontmatter.py patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FrontmatterResult:
    """Result of parsing a frontmatter block."""

    metadata: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    raw_frontmatter: str = ""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str | None:
        """Get skill name from metadata."""
        return self.metadata.get("name")

    @property
    def version(self) -> str | None:
        """Get skill version from metadata."""
        return self.metadata.get("version")

    @property
    def description(self) -> str | None:
        """Get skill description from metadata."""
        return self.metadata.get("description")

    @property
    def triggers(self) -> list[str]:
        """Get skill triggers from metadata."""
        triggers = self.metadata.get("triggers", [])
        return triggers if isinstance(triggers, list) else []

    @property
    def parameters(self) -> dict[str, Any]:
        """Get skill parameters schema from metadata."""
        params = self.metadata.get("parameters", {})
        return params if isinstance(params, dict) else {}


FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)
MAX_BODY_WORDS = 1500


def parse_frontmatter(content: str, *, validate_word_count: bool = True) -> FrontmatterResult:
    """
    Parse YAML frontmatter from a string.

    Args:
        content: Raw content string with optional YAML frontmatter
        validate_word_count: Whether to validate body word count (default: True)

    Returns:
        FrontmatterResult with parsed metadata and body content

    Example:
        >>> result = parse_frontmatter("---\\nname: my-skill\\n---\\nBody text")
        >>> result.name
        'my-skill'
    """
    errors: list[str] = []

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        # No frontmatter found - treat entire content as body
        return FrontmatterResult(
            metadata={},
            body=content.strip(),
            is_valid=False,
            errors=["No valid frontmatter block found"],
        )

    raw_yaml = match.group(1)
    body = match.group(2).strip()

    try:
        metadata = yaml.safe_load(raw_yaml)
        if not isinstance(metadata, dict):
            errors.append("Frontmatter must be a YAML mapping")
            metadata = {}
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {e}")
        metadata = {}

    # Validate word count
    if validate_word_count and body:
        word_count = len(body.split())
        if word_count > MAX_BODY_WORDS:
            errors.append(f"Body exceeds {MAX_BODY_WORDS} words ({word_count} words)")

    return FrontmatterResult(
        metadata=metadata,
        body=body,
        raw_frontmatter=raw_yaml,
        is_valid=len(errors) == 0,
        errors=errors,
    )


def parse_frontmatter_file(
    file_path: Path | str, *, validate_word_count: bool = True
) -> FrontmatterResult:
    """
    Parse YAML frontmatter from a file.

    Args:
        file_path: Path to the file to parse
        validate_word_count: Whether to validate body word count (default: True)

    Returns:
        FrontmatterResult with parsed metadata and body content
    """
    path = Path(file_path)
    if not path.exists():
        return FrontmatterResult(
            is_valid=False,
            errors=[f"File not found: {file_path}"],
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return FrontmatterResult(
            is_valid=False,
            errors=[f"Error reading file: {e}"],
        )

    return parse_frontmatter(content, validate_word_count=validate_word_count)
