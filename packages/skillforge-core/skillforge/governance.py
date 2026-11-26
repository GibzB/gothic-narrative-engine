"""
Governance Module for Kiro-SkillForge Pipeline.

Tracks skill lineage, changes, and access control for audit purposes.

Implements:
- Task 2.10.1: Timestamp Recorder - Record creation/modification/compilation timestamps
- Task 2.10.2: Version Tracker - Track version history when version control is enabled
- Task 2.10.3: Permission Enforcer - Enforce access control permissions

Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================

class LifecycleEventType(str, Enum):
    """Types of skill lifecycle events."""
    CREATED = "created"
    MODIFIED = "modified"
    COMPILED = "compiled"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class PermissionLevel(str, Enum):
    """Permission levels for skill access control."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class TimestampRecord:
    """Record of a lifecycle event timestamp."""
    skill_id: str
    event_type: LifecycleEventType
    timestamp: str
    user: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "skill_id": self.skill_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "user": self.user,
            "metadata": self.metadata,
        }


@dataclass
class VersionSnapshot:
    """A snapshot of a skill at a specific version."""
    version: str
    skill_id: str
    content_hash: str
    timestamp: str
    author: str | None = None
    message: str | None = None
    parent_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "version": self.version,
            "skill_id": self.skill_id,
            "content_hash": self.content_hash,
            "timestamp": self.timestamp,
            "author": self.author,
            "message": self.message,
            "parent_version": self.parent_version,
            "metadata": self.metadata,
        }


@dataclass
class Permission:
    """A permission entry for a user or role."""
    skill_id: str
    principal: str  # User ID or role name
    permission_level: PermissionLevel
    granted_by: str | None = None
    granted_at: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "skill_id": self.skill_id,
            "principal": self.principal,
            "permission_level": self.permission_level.value,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at,
            "expires_at": self.expires_at,
        }


@dataclass
class GovernanceRecord:
    """Complete governance record for a skill."""
    skill_id: str
    timestamps: list[TimestampRecord] = field(default_factory=list)
    versions: list[VersionSnapshot] = field(default_factory=list)
    permissions: list[Permission] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "skill_id": self.skill_id,
            "timestamps": [t.to_dict() for t in self.timestamps],
            "versions": [v.to_dict() for v in self.versions],
            "permissions": [p.to_dict() for p in self.permissions],
        }


# ============================================================================
# Timestamp Recorder (Task 2.10.1)
# ============================================================================

class TimestampRecorder:
    """
    Records timestamps for skill lifecycle events.

    Tracks creation, modification, and compilation events for audit
    and lineage purposes. Records are stored in memory and optionally
    persisted to a file.

    Task 2.10.1: Timestamp Recorder
    Validates: Requirements 14.1, 14.2, 14.3

    Example:
        >>> recorder = TimestampRecorder()
        >>> recorder.record("my-skill", LifecycleEventType.CREATED)
        >>> recorder.record("my-skill", LifecycleEventType.COMPILED)
        >>> records = recorder.get_records("my-skill")
        >>> len(records)
        2
    """

    def __init__(
        self,
        *,
        storage_path: Path | str | None = None,
        auto_persist: bool = False,
    ) -> None:
        """
        Initialize the timestamp recorder.

        Args:
            storage_path: Optional path to persist records
            auto_persist: Whether to automatically persist after each record
        """
        self._records: dict[str, list[TimestampRecord]] = {}
        self._storage_path = Path(storage_path) if storage_path else None
        self._auto_persist = auto_persist

    def record(
        self,
        skill_id: str,
        event_type: LifecycleEventType,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> TimestampRecord:
        """
        Record a lifecycle event timestamp.

        Args:
            skill_id: ID of the skill
            event_type: Type of lifecycle event
            user: Optional user who triggered the event
            metadata: Optional additional metadata
            timestamp: Optional specific timestamp (defaults to now)

        Returns:
            The created TimestampRecord
        """
        record = TimestampRecord(
            skill_id=skill_id,
            event_type=event_type,
            timestamp=timestamp or datetime.utcnow().isoformat(),
            user=user,
            metadata=metadata or {},
        )

        if skill_id not in self._records:
            self._records[skill_id] = []
        self._records[skill_id].append(record)

        logger.debug(
            f"Recorded {event_type.value} event for skill '{skill_id}' at {record.timestamp}"
        )

        if self._auto_persist and self._storage_path:
            self._persist_records()

        return record

    def record_creation(
        self,
        skill_id: str,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimestampRecord:
        """
        Record a skill creation event.

        Validates: Requirement 14.1
        """
        return self.record(skill_id, LifecycleEventType.CREATED, user=user, metadata=metadata)

    def record_modification(
        self,
        skill_id: str,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimestampRecord:
        """
        Record a skill modification event.

        Validates: Requirement 14.2
        """
        return self.record(skill_id, LifecycleEventType.MODIFIED, user=user, metadata=metadata)

    def record_compilation(
        self,
        skill_id: str,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimestampRecord:
        """
        Record a skill compilation event.

        Validates: Requirement 14.3
        """
        return self.record(skill_id, LifecycleEventType.COMPILED, user=user, metadata=metadata)

    def get_records(
        self,
        skill_id: str,
        *,
        event_type: LifecycleEventType | None = None,
    ) -> list[TimestampRecord]:
        """
        Get timestamp records for a skill.

        Args:
            skill_id: ID of the skill
            event_type: Optional filter by event type

        Returns:
            List of timestamp records
        """
        records = self._records.get(skill_id, [])
        if event_type:
            records = [r for r in records if r.event_type == event_type]
        return records.copy()

    def get_latest_record(
        self,
        skill_id: str,
        event_type: LifecycleEventType | None = None,
    ) -> TimestampRecord | None:
        """
        Get the most recent timestamp record for a skill.

        Args:
            skill_id: ID of the skill
            event_type: Optional filter by event type

        Returns:
            Most recent record or None if no records exist
        """
        records = self.get_records(skill_id, event_type=event_type)
        if not records:
            return None
        return max(records, key=lambda r: r.timestamp)

    def get_all_skill_ids(self) -> list[str]:
        """Get all skill IDs that have records."""
        return list(self._records.keys())

    def clear_records(self, skill_id: str) -> int:
        """
        Clear all records for a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            Number of records cleared
        """
        count = len(self._records.get(skill_id, []))
        self._records.pop(skill_id, None)
        return count

    def persist(self) -> bool:
        """
        Persist all records to storage.

        Returns:
            True if persistence succeeded
        """
        if not self._storage_path:
            logger.warning("No storage path configured for persistence")
            return False
        return self._persist_records()

    def _persist_records(self) -> bool:
        """Internal method to persist records."""
        if not self._storage_path:
            return False

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                skill_id: [r.to_dict() for r in records]
                for skill_id, records in self._records.items()
            }
            self._storage_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Persisted records to {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist records: {e}")
            return False

    def load(self) -> bool:
        """
        Load records from storage.

        Returns:
            True if loading succeeded
        """
        if not self._storage_path or not self._storage_path.exists():
            return False

        try:
            data = json.loads(self._storage_path.read_text())
            self._records.clear()

            for skill_id, records_data in data.items():
                self._records[skill_id] = [
                    TimestampRecord(
                        skill_id=r["skill_id"],
                        event_type=LifecycleEventType(r["event_type"]),
                        timestamp=r["timestamp"],
                        user=r.get("user"),
                        metadata=r.get("metadata", {}),
                    )
                    for r in records_data
                ]

            logger.debug(f"Loaded records from {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load records: {e}")
            return False

    @property
    def total_records(self) -> int:
        """Total number of records across all skills."""
        return sum(len(records) for records in self._records.values())


# ============================================================================
# Version Tracker (Task 2.10.2)
# ============================================================================

class VersionTracker:
    """
    Tracks version history for skills.

    Generates version snapshots and maintains a version chain for each
    skill when version control is enabled.

    Task 2.10.2: Version Tracker
    Validates: Requirement 14.4

    Example:
        >>> tracker = VersionTracker()
        >>> snapshot = tracker.create_snapshot("my-skill", {"name": "My Skill"})
        >>> snapshot.version
        '1.0.0'
        >>> history = tracker.get_history("my-skill")
        >>> len(history)
        1
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        storage_path: Path | str | None = None,
        auto_persist: bool = False,
    ) -> None:
        """
        Initialize the version tracker.

        Args:
            enabled: Whether version tracking is enabled
            storage_path: Optional path to persist version history
            auto_persist: Whether to automatically persist after each snapshot
        """
        self._enabled = enabled
        self._versions: dict[str, list[VersionSnapshot]] = {}
        self._storage_path = Path(storage_path) if storage_path else None
        self._auto_persist = auto_persist
        self._version_counters: dict[str, int] = {}

    @property
    def enabled(self) -> bool:
        """Whether version tracking is enabled."""
        return self._enabled

    def create_snapshot(
        self,
        skill_id: str,
        content: dict[str, Any] | str,
        *,
        author: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VersionSnapshot | None:
        """
        Create a version snapshot for a skill.

        Args:
            skill_id: ID of the skill
            content: Skill content (dict or string)
            author: Optional author of this version
            message: Optional commit message
            metadata: Optional additional metadata

        Returns:
            VersionSnapshot if tracking is enabled, None otherwise

        Validates: Requirement 14.4
        """
        if not self._enabled:
            logger.debug(f"Version tracking disabled, skipping snapshot for {skill_id}")
            return None

        # Generate content hash
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True)
        else:
            content_str = content
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        # Get previous version
        previous_versions = self._versions.get(skill_id, [])
        parent_version = previous_versions[-1].version if previous_versions else None

        # Generate new version number
        version = self._generate_version(skill_id)

        snapshot = VersionSnapshot(
            version=version,
            skill_id=skill_id,
            content_hash=content_hash,
            timestamp=datetime.utcnow().isoformat(),
            author=author,
            message=message,
            parent_version=parent_version,
            metadata=metadata or {},
        )

        if skill_id not in self._versions:
            self._versions[skill_id] = []
        self._versions[skill_id].append(snapshot)

        logger.info(
            f"Created version {version} for skill '{skill_id}' "
            f"(hash: {content_hash})"
        )

        if self._auto_persist and self._storage_path:
            self._persist_versions()

        return snapshot

    def _generate_version(self, skill_id: str) -> str:
        """Generate a new version number for a skill."""
        if skill_id not in self._version_counters:
            self._version_counters[skill_id] = 0

        self._version_counters[skill_id] += 1
        counter = self._version_counters[skill_id]

        # Simple semantic versioning: major.minor
        major = (counter - 1) // 10 + 1
        minor = (counter - 1) % 10
        return f"{major}.{minor}.0"

    def get_history(
        self,
        skill_id: str,
        *,
        limit: int = 100,
    ) -> list[VersionSnapshot]:
        """
        Get version history for a skill.

        Args:
            skill_id: ID of the skill
            limit: Maximum number of versions to return

        Returns:
            List of version snapshots, most recent last
        """
        versions = self._versions.get(skill_id, [])
        return versions[-limit:]

    def get_version(
        self,
        skill_id: str,
        version: str,
    ) -> VersionSnapshot | None:
        """
        Get a specific version of a skill.

        Args:
            skill_id: ID of the skill
            version: Version string to find

        Returns:
            VersionSnapshot or None if not found
        """
        for snapshot in self._versions.get(skill_id, []):
            if snapshot.version == version:
                return snapshot
        return None

    def get_latest_version(self, skill_id: str) -> VersionSnapshot | None:
        """
        Get the latest version of a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            Latest VersionSnapshot or None if no versions exist
        """
        versions = self._versions.get(skill_id, [])
        if not versions:
            return None
        return versions[-1]

    def rollback(
        self,
        skill_id: str,
        target_version: str,
    ) -> VersionSnapshot | None:
        """
        Rollback to a specific version (creates a new snapshot with the old content hash).

        Args:
            skill_id: ID of the skill
            target_version: Version to rollback to

        Returns:
            New VersionSnapshot for the rollback, or None if target not found
        """
        target = self.get_version(skill_id, target_version)
        if not target:
            logger.warning(f"Version {target_version} not found for skill {skill_id}")
            return None

        # Create a new snapshot marking it as a rollback
        return self.create_snapshot(
            skill_id,
            {"_rollback_from": target_version, "_content_hash": target.content_hash},
            message=f"Rollback to version {target_version}",
            metadata={"rollback": True, "rollback_from": target_version},
        )

    def clear_history(self, skill_id: str) -> int:
        """
        Clear version history for a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            Number of versions cleared
        """
        count = len(self._versions.get(skill_id, []))
        self._versions.pop(skill_id, None)
        self._version_counters.pop(skill_id, None)
        return count

    def persist(self) -> bool:
        """Persist version history to storage."""
        if not self._storage_path:
            logger.warning("No storage path configured for persistence")
            return False
        return self._persist_versions()

    def _persist_versions(self) -> bool:
        """Internal method to persist versions."""
        if not self._storage_path:
            return False

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "versions": {
                    skill_id: [v.to_dict() for v in versions]
                    for skill_id, versions in self._versions.items()
                },
                "counters": self._version_counters,
            }
            self._storage_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Persisted versions to {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist versions: {e}")
            return False

    def load(self) -> bool:
        """Load version history from storage."""
        if not self._storage_path or not self._storage_path.exists():
            return False

        try:
            data = json.loads(self._storage_path.read_text())
            self._versions.clear()
            self._version_counters.clear()

            for skill_id, versions_data in data.get("versions", {}).items():
                self._versions[skill_id] = [
                    VersionSnapshot(
                        version=v["version"],
                        skill_id=v["skill_id"],
                        content_hash=v["content_hash"],
                        timestamp=v["timestamp"],
                        author=v.get("author"),
                        message=v.get("message"),
                        parent_version=v.get("parent_version"),
                        metadata=v.get("metadata", {}),
                    )
                    for v in versions_data
                ]

            self._version_counters.update(data.get("counters", {}))
            logger.debug(f"Loaded versions from {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load versions: {e}")
            return False

    @property
    def total_versions(self) -> int:
        """Total number of versions across all skills."""
        return sum(len(versions) for versions in self._versions.values())


# ============================================================================
# Permission Enforcer (Task 2.10.3)
# ============================================================================

class PermissionEnforcer:
    """
    Enforces access control permissions for skills.

    Validates user permissions before allowing modification operations
    and maintains a permission registry.

    Task 2.10.3: Permission Enforcer
    Validates: Requirement 14.5

    Example:
        >>> enforcer = PermissionEnforcer()
        >>> enforcer.grant_permission("my-skill", "user1", PermissionLevel.WRITE)
        >>> enforcer.check_permission("my-skill", "user1", PermissionLevel.WRITE)
        True
        >>> enforcer.check_permission("my-skill", "user2", PermissionLevel.WRITE)
        False
    """

    # Permission hierarchy: higher values include lower ones
    PERMISSION_HIERARCHY: dict[PermissionLevel, int] = {
        PermissionLevel.READ: 1,
        PermissionLevel.WRITE: 2,
        PermissionLevel.EXECUTE: 3,
        PermissionLevel.ADMIN: 4,
    }

    def __init__(
        self,
        *,
        enabled: bool = True,
        default_permission: PermissionLevel = PermissionLevel.READ,
        storage_path: Path | str | None = None,
        auto_persist: bool = False,
    ) -> None:
        """
        Initialize the permission enforcer.

        Args:
            enabled: Whether access control is enabled
            default_permission: Default permission level for unlisted users
            storage_path: Optional path to persist permissions
            auto_persist: Whether to automatically persist after changes
        """
        self._enabled = enabled
        self._default_permission = default_permission
        self._permissions: dict[str, list[Permission]] = {}  # skill_id -> permissions
        self._storage_path = Path(storage_path) if storage_path else None
        self._auto_persist = auto_persist

    @property
    def enabled(self) -> bool:
        """Whether access control is enabled."""
        return self._enabled

    def grant_permission(
        self,
        skill_id: str,
        principal: str,
        permission_level: PermissionLevel,
        *,
        granted_by: str | None = None,
        expires_at: str | None = None,
    ) -> Permission:
        """
        Grant a permission to a user or role.

        Args:
            skill_id: ID of the skill
            principal: User ID or role name
            permission_level: Permission level to grant
            granted_by: ID of user who granted the permission
            expires_at: Optional expiration timestamp

        Returns:
            The created Permission
        """
        # Remove existing permission for this principal
        self._revoke_permission_internal(skill_id, principal)

        permission = Permission(
            skill_id=skill_id,
            principal=principal,
            permission_level=permission_level,
            granted_by=granted_by,
            granted_at=datetime.utcnow().isoformat(),
            expires_at=expires_at,
        )

        if skill_id not in self._permissions:
            self._permissions[skill_id] = []
        self._permissions[skill_id].append(permission)

        logger.info(
            f"Granted {permission_level.value} permission on '{skill_id}' to '{principal}'"
        )

        if self._auto_persist and self._storage_path:
            self._persist_permissions()

        return permission

    def revoke_permission(
        self,
        skill_id: str,
        principal: str,
    ) -> bool:
        """
        Revoke a permission from a user or role.

        Args:
            skill_id: ID of the skill
            principal: User ID or role name

        Returns:
            True if permission was revoked
        """
        result = self._revoke_permission_internal(skill_id, principal)
        if result and self._auto_persist and self._storage_path:
            self._persist_permissions()
        return result

    def _revoke_permission_internal(
        self,
        skill_id: str,
        principal: str,
    ) -> bool:
        """Internal method to revoke permission without auto-persist."""
        permissions = self._permissions.get(skill_id, [])
        original_count = len(permissions)
        self._permissions[skill_id] = [
            p for p in permissions if p.principal != principal
        ]
        return len(self._permissions[skill_id]) < original_count

    def check_permission(
        self,
        skill_id: str,
        principal: str,
        required_permission: PermissionLevel,
    ) -> bool:
        """
        Check if a principal has a required permission.

        Args:
            skill_id: ID of the skill
            principal: User ID or role name
            required_permission: Required permission level

        Returns:
            True if the principal has the required permission
        """
        if not self._enabled:
            logger.debug(f"Access control disabled, allowing {principal}")
            return True

        # Get principal's permission level
        permission = self._get_permission(skill_id, principal)

        # Check expiration
        if permission and permission.expires_at:
            if datetime.utcnow().isoformat() > permission.expires_at:
                logger.warning(
                    f"Permission for '{principal}' on '{skill_id}' has expired"
                )
                return False

        # Determine effective permission level
        if permission:
            level = permission.permission_level
        else:
            level = self._default_permission

        # Check hierarchy
        required_level = self.PERMISSION_HIERARCHY.get(required_permission, 0)
        actual_level = self.PERMISSION_HIERARCHY.get(level, 0)

        has_permission = actual_level >= required_level

        if not has_permission:
            logger.warning(
                f"Permission denied: '{principal}' needs {required_permission.value} "
                f"on '{skill_id}' but has {level.value}"
            )

        return has_permission

    def _get_permission(
        self,
        skill_id: str,
        principal: str,
    ) -> Permission | None:
        """Get permission for a principal on a skill."""
        for permission in self._permissions.get(skill_id, []):
            if permission.principal == principal:
                return permission
        return None

    def get_permissions(
        self,
        skill_id: str,
        *,
        principal: str | None = None,
    ) -> list[Permission]:
        """
        Get permissions for a skill.

        Args:
            skill_id: ID of the skill
            principal: Optional filter by principal

        Returns:
            List of permissions
        """
        permissions = self._permissions.get(skill_id, [])
        if principal:
            permissions = [p for p in permissions if p.principal == principal]
        return permissions.copy()

    def validate_operation(
        self,
        skill_id: str,
        principal: str,
        operation: str,
    ) -> tuple[bool, str]:
        """
        Validate if an operation is allowed.

        Args:
            skill_id: ID of the skill
            principal: User ID performing the operation
            operation: Operation name (read, write, execute, admin)

        Returns:
            Tuple of (is_allowed, message)

        Validates: Requirement 14.5
        """
        # Map operations to permission levels
        operation_map = {
            "read": PermissionLevel.READ,
            "write": PermissionLevel.WRITE,
            "execute": PermissionLevel.EXECUTE,
            "admin": PermissionLevel.ADMIN,
            "modify": PermissionLevel.WRITE,
            "compile": PermissionLevel.WRITE,
            "delete": PermissionLevel.ADMIN,
        }

        required = operation_map.get(operation.lower())
        if not required:
            return (False, f"Unknown operation: {operation}")

        if self.check_permission(skill_id, principal, required):
            return (True, f"Operation '{operation}' allowed for '{principal}'")
        else:
            return (
                False,
                f"Permission denied: '{principal}' cannot perform '{operation}' on '{skill_id}'",
            )

    def clear_permissions(self, skill_id: str) -> int:
        """
        Clear all permissions for a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            Number of permissions cleared
        """
        count = len(self._permissions.get(skill_id, []))
        self._permissions.pop(skill_id, None)
        if self._auto_persist and self._storage_path:
            self._persist_permissions()
        return count

    def persist(self) -> bool:
        """Persist permissions to storage."""
        if not self._storage_path:
            logger.warning("No storage path configured for persistence")
            return False
        return self._persist_permissions()

    def _persist_permissions(self) -> bool:
        """Internal method to persist permissions."""
        if not self._storage_path:
            return False

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                skill_id: [p.to_dict() for p in permissions]
                for skill_id, permissions in self._permissions.items()
            }
            self._storage_path.write_text(json.dumps(data, indent=2))
            logger.debug(f"Persisted permissions to {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist permissions: {e}")
            return False

    def load(self) -> bool:
        """Load permissions from storage."""
        if not self._storage_path or not self._storage_path.exists():
            return False

        try:
            data = json.loads(self._storage_path.read_text())
            self._permissions.clear()

            for skill_id, perms_data in data.items():
                self._permissions[skill_id] = [
                    Permission(
                        skill_id=p["skill_id"],
                        principal=p["principal"],
                        permission_level=PermissionLevel(p["permission_level"]),
                        granted_by=p.get("granted_by"),
                        granted_at=p.get("granted_at"),
                        expires_at=p.get("expires_at"),
                    )
                    for p in perms_data
                ]

            logger.debug(f"Loaded permissions from {self._storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")
            return False

    @property
    def total_permissions(self) -> int:
        """Total number of permissions across all skills."""
        return sum(len(perms) for perms in self._permissions.values())


# ============================================================================
# Combined Governance Module
# ============================================================================

class GovernanceModule:
    """
    Combined governance module providing timestamp recording, version tracking,
    and permission enforcement.

    Provides a unified interface for all governance operations.

    Example:
        >>> governance = GovernanceModule()
        >>> governance.record_creation("my-skill", user="user1")
        >>> governance.create_version("my-skill", {"name": "My Skill"})
        >>> governance.check_permission("my-skill", "user1", PermissionLevel.READ)
    """

    def __init__(
        self,
        *,
        version_control_enabled: bool = True,
        access_control_enabled: bool = True,
        storage_dir: Path | str | None = None,
        auto_persist: bool = False,
    ) -> None:
        """
        Initialize the governance module.

        Args:
            version_control_enabled: Whether version tracking is enabled
            access_control_enabled: Whether access control is enabled
            storage_dir: Directory for persistent storage
            auto_persist: Whether to automatically persist changes
        """
        storage_path = Path(storage_dir) if storage_dir else None

        self._timestamp_recorder = TimestampRecorder(
            storage_path=storage_path / "timestamps.json" if storage_path else None,
            auto_persist=auto_persist,
        )

        self._version_tracker = VersionTracker(
            enabled=version_control_enabled,
            storage_path=storage_path / "versions.json" if storage_path else None,
            auto_persist=auto_persist,
        )

        self._permission_enforcer = PermissionEnforcer(
            enabled=access_control_enabled,
            storage_path=storage_path / "permissions.json" if storage_path else None,
            auto_persist=auto_persist,
        )

    @property
    def timestamps(self) -> TimestampRecorder:
        """Get the timestamp recorder."""
        return self._timestamp_recorder

    @property
    def versions(self) -> VersionTracker:
        """Get the version tracker."""
        return self._version_tracker

    @property
    def permissions(self) -> PermissionEnforcer:
        """Get the permission enforcer."""
        return self._permission_enforcer

    # Convenience methods

    def record_creation(
        self,
        skill_id: str,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimestampRecord:
        """Record skill creation and create initial version."""
        record = self._timestamp_recorder.record_creation(
            skill_id, user=user, metadata=metadata
        )
        return record

    def record_modification(
        self,
        skill_id: str,
        content: dict[str, Any] | str | None = None,
        *,
        user: str | None = None,
        message: str | None = None,
    ) -> tuple[TimestampRecord, VersionSnapshot | None]:
        """
        Record a skill modification with version snapshot.

        Args:
            skill_id: ID of the skill
            content: New skill content for versioning
            user: User who made the modification
            message: Commit message

        Returns:
            Tuple of (timestamp record, version snapshot or None)
        """
        timestamp_record = self._timestamp_recorder.record_modification(
            skill_id, user=user
        )

        version_snapshot = None
        if content is not None:
            version_snapshot = self._version_tracker.create_snapshot(
                skill_id, content, author=user, message=message
            )

        return (timestamp_record, version_snapshot)

    def record_compilation(
        self,
        skill_id: str,
        *,
        user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimestampRecord:
        """Record skill compilation."""
        return self._timestamp_recorder.record_compilation(
            skill_id, user=user, metadata=metadata
        )

    def create_version(
        self,
        skill_id: str,
        content: dict[str, Any] | str,
        *,
        author: str | None = None,
        message: str | None = None,
    ) -> VersionSnapshot | None:
        """Create a version snapshot."""
        return self._version_tracker.create_snapshot(
            skill_id, content, author=author, message=message
        )

    def check_permission(
        self,
        skill_id: str,
        principal: str,
        required_permission: PermissionLevel,
    ) -> bool:
        """Check if a principal has a required permission."""
        return self._permission_enforcer.check_permission(
            skill_id, principal, required_permission
        )

    def grant_permission(
        self,
        skill_id: str,
        principal: str,
        permission_level: PermissionLevel,
        *,
        granted_by: str | None = None,
    ) -> Permission:
        """Grant a permission to a principal."""
        return self._permission_enforcer.grant_permission(
            skill_id, principal, permission_level, granted_by=granted_by
        )

    def get_governance_record(self, skill_id: str) -> GovernanceRecord:
        """
        Get the complete governance record for a skill.

        Args:
            skill_id: ID of the skill

        Returns:
            GovernanceRecord with all timestamps, versions, and permissions
        """
        return GovernanceRecord(
            skill_id=skill_id,
            timestamps=self._timestamp_recorder.get_records(skill_id),
            versions=self._version_tracker.get_history(skill_id),
            permissions=self._permission_enforcer.get_permissions(skill_id),
        )

    def persist_all(self) -> dict[str, bool]:
        """
        Persist all governance data.

        Returns:
            Dictionary with persistence status for each component
        """
        return {
            "timestamps": self._timestamp_recorder.persist(),
            "versions": self._version_tracker.persist(),
            "permissions": self._permission_enforcer.persist(),
        }

    def load_all(self) -> dict[str, bool]:
        """
        Load all governance data.

        Returns:
            Dictionary with load status for each component
        """
        return {
            "timestamps": self._timestamp_recorder.load(),
            "versions": self._version_tracker.load(),
            "permissions": self._permission_enforcer.load(),
        }
