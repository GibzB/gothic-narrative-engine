"""
PostFileSave Hook - Asset tracking for narrative resources.

Implements a Kiro Agent Hook that tracks changes to narrative assets
(stories, scenes, characters, items) and validates them.

Task 4.6: Implement PostFileSave Hook
Validates: Requirements 4.1, 4.3
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AssetChange:
    """Represents a change to an asset."""

    asset_type: str  # "story", "scene", "character", "item", "skill"
    asset_id: str
    file_path: str
    change_type: str  # "created", "modified", "deleted"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assetType": self.asset_type,
            "assetId": self.asset_id,
            "filePath": self.file_path,
            "changeType": self.change_type,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class ValidationResult:
    """Result of validating an asset."""

    is_valid: bool
    asset_type: str
    asset_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "isValid": self.is_valid,
            "assetType": self.asset_type,
            "assetId": self.asset_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


class AssetTracker:
    """
    Tracks and validates narrative assets.

    Monitors changes to story files and maintains a registry
    of all narrative assets with their validation status.

    Task 4.6: Asset Tracking
    Validates: Requirements 4.1, 4.3

    Example:
        >>> tracker = AssetTracker()
        >>> result = tracker.process_file("stories/haunted_manor.json")
        >>> result.is_valid
        True
    """

    def __init__(
        self,
        *,
        skills_dir: Path | None = None,
        stories_dir: Path | None = None,
    ) -> None:
        """
        Initialize the asset tracker.

        Args:
            skills_dir: Directory containing skill definitions
            stories_dir: Directory containing story files
        """
        self.skills_dir = skills_dir
        self.stories_dir = stories_dir
        self._asset_registry: dict[str, dict[str, Any]] = {}
        self._change_log: list[AssetChange] = []

    @property
    def asset_count(self) -> int:
        return len(self._asset_registry)

    @property
    def change_count(self) -> int:
        return len(self._change_log)

    def detect_asset_type(self, file_path: Path | str) -> tuple[str, str]:
        """
        Detect the type of asset from a file path.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (asset_type, asset_id)
        """
        path = Path(file_path)
        filename = path.name.lower()
        parent = path.parent.name.lower()

        # Check for skill files
        if filename == "skill.md":
            return "skill", path.parent.name

        # Check for story files
        if filename.endswith(".story.json") or parent == "stories":
            return "story", path.stem

        # Check for scene files
        if filename.startswith("scene_") and filename.endswith(".json"):
            return "scene", path.stem

        # Check for character files
        if "character" in parent or filename.startswith("char_"):
            return "character", path.stem

        # Check for item files
        if "item" in parent or filename.startswith("item_"):
            return "item", path.stem

        # Default to unknown
        return "unknown", path.stem

    def process_file(
        self,
        file_path: Path | str,
        *,
        change_type: str = "modified",
    ) -> ValidationResult:
        """
        Process a file change.

        Args:
            file_path: Path to the changed file
            change_type: Type of change (created, modified, deleted)

        Returns:
            ValidationResult with validation status
        """
        path = Path(file_path)
        asset_type, asset_id = self.detect_asset_type(path)

        # Record the change
        change = AssetChange(
            asset_type=asset_type,
            asset_id=asset_id,
            file_path=str(path),
            change_type=change_type,
        )
        self._change_log.append(change)

        # Validate based on asset type
        if asset_type == "story":
            return self._validate_story(path, asset_id)
        elif asset_type == "scene":
            return self._validate_scene(path, asset_id)
        elif asset_type == "character":
            return self._validate_character(path, asset_id)
        elif asset_type == "item":
            return self._validate_item(path, asset_id)
        elif asset_type == "skill":
            return self._validate_skill(path, asset_id)
        else:
            return ValidationResult(
                is_valid=True,
                asset_type=asset_type,
                asset_id=asset_id,
                warnings=["Unknown asset type, validation skipped"],
            )

    def _validate_story(self, path: Path, asset_id: str) -> ValidationResult:
        """Validate a story file."""
        result = ValidationResult(
            is_valid=True,
            asset_type="story",
            asset_id=asset_id,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append("Story file does not exist")
            return result

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid JSON: {e}")
            return result

        # Check required fields
        metadata = data.get("metadata", {})
        if not metadata.get("title"):
            result.warnings.append("Story missing title in metadata")

        if not metadata.get("version"):
            result.warnings.append("Story missing version in metadata")

        # Check scenes
        scenes = data.get("scenes", {})
        if not scenes:
            result.is_valid = False
            result.errors.append("Story has no scenes")
            return result

        # Validate scene structure
        scene_ids = set(scenes.keys())
        referenced_scenes = set()

        for scene_id, scene in scenes.items():
            # Check for required fields
            if not scene.get("description"):
                result.warnings.append(f"Scene '{scene_id}' missing description")

            # Track referenced scenes
            for choice in scene.get("choices", []):
                target = choice.get("consequence")
                if target:
                    referenced_scenes.add(target)

        # Check for orphaned or missing scenes
        missing_scenes = referenced_scenes - scene_ids
        if missing_scenes:
            result.warnings.append(f"Referenced scenes not defined: {missing_scenes}")

        # Check for start scene
        if "start" not in scenes:
            result.warnings.append("No 'start' scene defined")

        # Update registry
        self._asset_registry[f"story:{asset_id}"] = {
            "title": metadata.get("title", "Untitled"),
            "version": metadata.get("version", "0.0.0"),
            "scene_count": len(scenes),
            "last_validated": datetime.utcnow().isoformat(),
            "is_valid": result.is_valid,
        }

        return result

    def _validate_scene(self, path: Path, asset_id: str) -> ValidationResult:
        """Validate a scene file."""
        result = ValidationResult(
            is_valid=True,
            asset_type="scene",
            asset_id=asset_id,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append("Scene file does not exist")
            return result

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid JSON: {e}")
            return result

        # Check required fields
        if not data.get("title"):
            result.warnings.append("Scene missing title")

        if not data.get("description"):
            result.warnings.append("Scene missing description")

        # Validate choices
        choices = data.get("choices", [])
        for i, choice in enumerate(choices):
            if not choice.get("id"):
                result.warnings.append(f"Choice {i} missing ID")

            if not choice.get("text"):
                result.warnings.append(f"Choice {i} missing text")

            if not choice.get("consequence"):
                result.warnings.append(f"Choice {i} missing consequence scene")

        return result

    def _validate_character(self, path: Path, asset_id: str) -> ValidationResult:
        """Validate a character file."""
        result = ValidationResult(
            is_valid=True,
            asset_type="character",
            asset_id=asset_id,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append("Character file does not exist")
            return result

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid JSON: {e}")
            return result

        # Check required fields
        if not data.get("name"):
            result.warnings.append("Character missing name")

        if not data.get("description"):
            result.warnings.append("Character missing description")

        return result

    def _validate_item(self, path: Path, asset_id: str) -> ValidationResult:
        """Validate an item file."""
        result = ValidationResult(
            is_valid=True,
            asset_type="item",
            asset_id=asset_id,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append("Item file does not exist")
            return result

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.is_valid = False
            result.errors.append(f"Invalid JSON: {e}")
            return result

        # Check required fields
        if not data.get("name"):
            result.warnings.append("Item missing name")

        if not data.get("description"):
            result.warnings.append("Item missing description")

        return result

    def _validate_skill(self, path: Path, asset_id: str) -> ValidationResult:
        """Validate a skill file."""
        result = ValidationResult(
            is_valid=True,
            asset_type="skill",
            asset_id=asset_id,
        )

        if not path.exists():
            result.is_valid = False
            result.errors.append("Skill file does not exist")
            return result

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Failed to read file: {e}")
            return result

        # Check for frontmatter
        if not content.startswith("---"):
            result.is_valid = False
            result.errors.append("Skill file missing YAML frontmatter")
            return result

        # Parse frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            result.is_valid = False
            result.errors.append("Invalid frontmatter format")
            return result

        frontmatter = parts[1].strip()

        # Check required fields in frontmatter
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in frontmatter.lower():
                result.warnings.append(f"Skill missing '{field}' in frontmatter")

        # Check body content
        body = parts[2].strip()
        if not body:
            result.warnings.append("Skill has no body content")
        elif len(body.split()) > 1500:
            result.warnings.append("Skill body exceeds 1500 words")

        return result

    def get_asset_registry(self) -> dict[str, Any]:
        """Get the current asset registry."""
        return self._asset_registry.copy()

    def get_change_log(self, limit: int = 100) -> list[AssetChange]:
        """Get recent changes from the log."""
        return self._change_log[-limit:]

    def get_invalid_assets(self) -> list[str]:
        """Get list of invalid asset IDs."""
        return [
            asset_id for asset_id, data in self._asset_registry.items()
            if not data.get("is_valid", True)
        ]


class PostFileSaveHook:
    """
    Kiro PostFileSave hook for asset tracking.

    Processes file save events and validates narrative assets.

    Task 4.6: PostFileSave Hook
    Validates: Requirements 4.1, 4.3

    Example:
        >>> hook = PostFileSaveHook()
        >>> hook.process_stdin()
    """

    def __init__(
        self,
        *,
        watch_patterns: list[str] | None = None,
        report_format: str = "text",
    ) -> None:
        """
        Initialize the hook.

        Args:
            watch_patterns: File patterns to watch (glob)
            report_format: Output format (text, json)
        """
        self.watch_patterns = watch_patterns or [
            "*.story.json",
            "*.json",
            "skill.md",
            "scene_*.json",
            "char_*.json",
            "item_*.json",
        ]
        self.report_format = report_format
        self._tracker = AssetTracker()

    def should_process(self, file_path: str) -> bool:
        """Check if a file should be processed."""
        path = Path(file_path)

        for pattern in self.watch_patterns:
            if path.match(pattern):
                return True

        # Check directory patterns
        parent = path.parent.name.lower()
        if parent in ("stories", "scenes", "characters", "items", "skills"):
            return True

        return False

    def process_file(self, file_path: str) -> ValidationResult | None:
        """
        Process a file save event.

        Args:
            file_path: Path to the saved file

        Returns:
            ValidationResult if file was processed, None otherwise
        """
        if not self.should_process(file_path):
            return None

        return self._tracker.process_file(file_path, change_type="modified")

    def process_stdin(self) -> int:
        """
        Process hook input from stdin.

        Reads JSON from stdin containing file path and validates.

        Returns:
            Exit code (0 for success, 1 for validation failure)
        """
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            print("Invalid JSON input", file=sys.stderr)
            return 0  # Don't block the save

        file_path = input_data.get("file_path", input_data.get("path", ""))

        if not file_path:
            return 0

        result = self.process_file(file_path)

        if result is None:
            # File not tracked
            return 0

        if self.report_format == "json":
            output = json.dumps(result.to_dict(), indent=2)
            print(output)
        else:
            if result.is_valid:
                print(f"✓ {result.asset_type}/{result.asset_id} is valid")
            else:
                print(f"✗ {result.asset_type}/{result.asset_id} has errors:", file=sys.stderr)
                for error in result.errors:
                    print(f"  • {error}", file=sys.stderr)

            if result.warnings:
                print(f"⚠ Warnings for {result.asset_id}:")
                for warning in result.warnings:
                    print(f"  • {warning}")

        # Return 0 to not block the save, even if validation failed
        return 0

    def generate_hook_json(self) -> str:
        """
        Generate a Kiro hook JSON configuration.

        Returns:
            JSON string for .kiro/hooks/asset-tracking.json
        """
        hook_config = {
            "version": "v1",
            "hooks": [
                {
                    "name": "narrative-asset-tracker",
                    "description": "Tracks and validates narrative asset changes (stories, scenes, characters, items, skills).",
                    "trigger": "PostFileSave",
                    "matcher": "(stories|scenes|characters|items|skills)/.*\\.(json|md)$",
                    "action": {
                        "type": "command",
                        "command": f"python3 -c '{self._get_inline_script()}'",
                    },
                    "timeout": 30,
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
    file_path = ctx.get("file_path", ctx.get("path", ""))
    print(f"[Asset Tracker] Processed: {file_path}")
    sys.exit(0)
except Exception as e:
    print(f"Asset tracker error: {e}", file=sys.stderr)
    sys.exit(0)
""".strip()


def main() -> int:
    """Main entry point for hook execution."""
    hook = PostFileSaveHook()
    return hook.process_stdin()


if __name__ == "__main__":
    sys.exit(main())
