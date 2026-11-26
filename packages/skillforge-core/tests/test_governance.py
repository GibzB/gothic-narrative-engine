"""
Tests for Governance Module and Doctor Enhancements.

Tests for:
- Task 2.10.1: Timestamp Recorder
- Task 2.10.2: Version Tracker
- Task 2.10.3: Permission Enforcer
- Task 2.11.1: Config Validator
- Task 2.11.2: Health Reporter
- Task 2.11.3: Conflict Analyzer
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from skillforge.governance import (
    TimestampRecorder,
    VersionTracker,
    PermissionEnforcer,
    GovernanceModule,
    LifecycleEventType,
    PermissionLevel,
    TimestampRecord,
    VersionSnapshot,
    Permission,
    GovernanceRecord,
)
from skillforge.doctor import (
    ConfigValidator,
    ConfigValidationResult,
    HealthReporter,
    HealthReport,
    EnvironmentStatus,
    ConflictAnalyzer,
    ConflictAnalysisReport,
    IdentifierCollision,
    CircularDependency,
    MissingCredential,
    DiagnosticIssue,
    run_full_diagnostics,
)


# ============================================================================
# Timestamp Recorder Tests (Task 2.10.1)
# ============================================================================

class TestTimestampRecorder:
    """Tests for TimestampRecorder."""

    def test_record_creation_event(self):
        """Test recording a creation event."""
        recorder = TimestampRecorder()
        
        record = recorder.record_creation("my-skill", user="user1")
        
        assert record.skill_id == "my-skill"
        assert record.event_type == LifecycleEventType.CREATED
        assert record.user == "user1"
        assert record.timestamp is not None

    def test_record_modification_event(self):
        """Test recording a modification event."""
        recorder = TimestampRecorder()
        
        record = recorder.record_modification("my-skill", user="user1")
        
        assert record.event_type == LifecycleEventType.MODIFIED

    def test_record_compilation_event(self):
        """Test recording a compilation event."""
        recorder = TimestampRecorder()
        
        record = recorder.record_compilation("my-skill", user="user1")
        
        assert record.event_type == LifecycleEventType.COMPILED

    def test_get_records_by_skill(self):
        """Test getting records by skill ID."""
        recorder = TimestampRecorder()
        
        recorder.record_creation("skill1")
        recorder.record_creation("skill2")
        recorder.record_modification("skill1")
        
        records = recorder.get_records("skill1")
        
        assert len(records) == 2

    def test_get_records_by_event_type(self):
        """Test filtering records by event type."""
        recorder = TimestampRecorder()
        
        recorder.record_creation("my-skill")
        recorder.record_modification("my-skill")
        recorder.record_compilation("my-skill")
        
        records = recorder.get_records("my-skill", event_type=LifecycleEventType.CREATED)
        
        assert len(records) == 1
        assert records[0].event_type == LifecycleEventType.CREATED

    def test_get_latest_record(self):
        """Test getting the most recent record."""
        recorder = TimestampRecorder()
        
        recorder.record("skill1", LifecycleEventType.CREATED, timestamp="2024-01-01T00:00:00")
        recorder.record("skill1", LifecycleEventType.MODIFIED, timestamp="2024-01-02T00:00:00")
        
        latest = recorder.get_latest_record("skill1")
        
        assert latest is not None
        assert latest.event_type == LifecycleEventType.MODIFIED

    def test_total_records(self):
        """Test total record count."""
        recorder = TimestampRecorder()
        
        recorder.record_creation("skill1")
        recorder.record_creation("skill2")
        recorder.record_modification("skill1")
        
        assert recorder.total_records == 3

    def test_clear_records(self):
        """Test clearing records for a skill."""
        recorder = TimestampRecorder()
        
        recorder.record_creation("skill1")
        recorder.record_creation("skill2")
        
        count = recorder.clear_records("skill1")
        
        assert count == 1
        assert recorder.total_records == 1

    def test_persist_and_load(self):
        """Test persisting and loading records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "timestamps.json"
            
            recorder1 = TimestampRecorder(storage_path=storage_path)
            recorder1.record_creation("skill1", user="user1")
            recorder1.persist()
            
            recorder2 = TimestampRecorder(storage_path=storage_path)
            recorder2.load()
            
            assert recorder2.total_records == 1
            records = recorder2.get_records("skill1")
            assert records[0].user == "user1"


# ============================================================================
# Version Tracker Tests (Task 2.10.2)
# ============================================================================

class TestVersionTracker:
    """Tests for VersionTracker."""

    def test_create_snapshot(self):
        """Test creating a version snapshot."""
        tracker = VersionTracker()
        
        snapshot = tracker.create_snapshot("my-skill", {"name": "My Skill"})
        
        assert snapshot is not None
        assert snapshot.skill_id == "my-skill"
        assert snapshot.version == "1.0.0"
        assert snapshot.content_hash is not None

    def test_version_increment(self):
        """Test version number incrementing."""
        tracker = VersionTracker()
        
        snapshot1 = tracker.create_snapshot("my-skill", {"v": 1})
        snapshot2 = tracker.create_snapshot("my-skill", {"v": 2})
        
        assert snapshot1.version != snapshot2.version

    def test_version_tracking_disabled(self):
        """Test that no snapshot is created when disabled."""
        tracker = VersionTracker(enabled=False)
        
        snapshot = tracker.create_snapshot("my-skill", {"name": "Test"})
        
        assert snapshot is None

    def test_get_history(self):
        """Test getting version history."""
        tracker = VersionTracker()
        
        tracker.create_snapshot("skill1", {"v": 1})
        tracker.create_snapshot("skill1", {"v": 2})
        tracker.create_snapshot("skill2", {"v": 1})
        
        history = tracker.get_history("skill1")
        
        assert len(history) == 2

    def test_get_specific_version(self):
        """Test getting a specific version."""
        tracker = VersionTracker()
        
        tracker.create_snapshot("my-skill", {"name": "v1"})
        snapshot = tracker.create_snapshot("my-skill", {"name": "v2"})
        
        found = tracker.get_version("my-skill", snapshot.version)
        
        assert found is not None
        assert found.version == snapshot.version

    def test_get_latest_version(self):
        """Test getting the latest version."""
        tracker = VersionTracker()
        
        tracker.create_snapshot("my-skill", {"v": 1})
        tracker.create_snapshot("my-skill", {"v": 2})
        
        latest = tracker.get_latest_version("my-skill")
        
        assert latest is not None
        assert latest.version == "1.1.0"  # Second version

    def test_parent_version_tracking(self):
        """Test that parent version is tracked."""
        tracker = VersionTracker()
        
        snapshot1 = tracker.create_snapshot("my-skill", {"v": 1})
        snapshot2 = tracker.create_snapshot("my-skill", {"v": 2})
        
        assert snapshot2.parent_version == snapshot1.version

    def test_clear_history(self):
        """Test clearing version history."""
        tracker = VersionTracker()
        
        tracker.create_snapshot("skill1", {"v": 1})
        tracker.create_snapshot("skill1", {"v": 2})
        
        count = tracker.clear_history("skill1")
        
        assert count == 2
        assert tracker.total_versions == 0


# ============================================================================
# Permission Enforcer Tests (Task 2.10.3)
# ============================================================================

class TestPermissionEnforcer:
    """Tests for PermissionEnforcer."""

    def test_grant_permission(self):
        """Test granting a permission."""
        enforcer = PermissionEnforcer()
        
        permission = enforcer.grant_permission(
            "my-skill", "user1", PermissionLevel.WRITE
        )
        
        assert permission.skill_id == "my-skill"
        assert permission.principal == "user1"
        assert permission.permission_level == PermissionLevel.WRITE

    def test_check_permission_granted(self):
        """Test checking a granted permission."""
        enforcer = PermissionEnforcer()
        
        enforcer.grant_permission("my-skill", "user1", PermissionLevel.WRITE)
        
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.WRITE)
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.READ)

    def test_check_permission_denied(self):
        """Test checking a denied permission."""
        enforcer = PermissionEnforcer()
        
        enforcer.grant_permission("my-skill", "user1", PermissionLevel.READ)
        
        assert not enforcer.check_permission("my-skill", "user1", PermissionLevel.WRITE)

    def test_check_permission_disabled(self):
        """Test that all permissions allowed when disabled."""
        enforcer = PermissionEnforcer(enabled=False)
        
        # No permissions granted, but should still pass
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.ADMIN)

    def test_permission_hierarchy(self):
        """Test permission hierarchy (admin > execute > write > read)."""
        enforcer = PermissionEnforcer()
        
        enforcer.grant_permission("my-skill", "user1", PermissionLevel.ADMIN)
        
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.READ)
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.WRITE)
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.EXECUTE)
        assert enforcer.check_permission("my-skill", "user1", PermissionLevel.ADMIN)

    def test_revoke_permission(self):
        """Test revoking a permission."""
        enforcer = PermissionEnforcer()
        
        enforcer.grant_permission("my-skill", "user1", PermissionLevel.WRITE)
        result = enforcer.revoke_permission("my-skill", "user1")
        
        assert result is True
        assert not enforcer.check_permission("my-skill", "user1", PermissionLevel.WRITE)

    def test_validate_operation(self):
        """Test validating an operation."""
        enforcer = PermissionEnforcer()
        
        enforcer.grant_permission("my-skill", "user1", PermissionLevel.WRITE)
        
        allowed, message = enforcer.validate_operation("my-skill", "user1", "write")
        assert allowed is True
        
        allowed, message = enforcer.validate_operation("my-skill", "user1", "delete")
        assert allowed is False

    def test_default_permission(self):
        """Test default permission for unlisted users."""
        enforcer = PermissionEnforcer(default_permission=PermissionLevel.READ)
        
        # No permission granted, should get default READ
        assert enforcer.check_permission("my-skill", "unknown-user", PermissionLevel.READ)
        assert not enforcer.check_permission("my-skill", "unknown-user", PermissionLevel.WRITE)


# ============================================================================
# Governance Module Tests
# ============================================================================

class TestGovernanceModule:
    """Tests for combined GovernanceModule."""

    def test_record_creation_convenience(self):
        """Test convenience method for recording creation."""
        governance = GovernanceModule()
        
        record = governance.record_creation("my-skill", user="user1")
        
        assert record.event_type == LifecycleEventType.CREATED

    def test_record_modification_with_version(self):
        """Test recording modification with version snapshot."""
        governance = GovernanceModule()
        
        record, snapshot = governance.record_modification(
            "my-skill",
            content={"name": "My Skill"},
            user="user1",
            message="Updated skill",
        )
        
        assert record.event_type == LifecycleEventType.MODIFIED
        assert snapshot is not None

    def test_get_governance_record(self):
        """Test getting complete governance record."""
        governance = GovernanceModule()
        
        governance.record_creation("my-skill")
        governance.create_version("my-skill", {"name": "Test"})
        governance.grant_permission("my-skill", "user1", PermissionLevel.WRITE)
        
        record = governance.get_governance_record("my-skill")
        
        assert len(record.timestamps) == 1
        assert len(record.versions) == 1
        assert len(record.permissions) == 1


# ============================================================================
# Config Validator Tests (Task 2.11.1)
# ============================================================================

class TestConfigValidator:
    """Tests for ConfigValidator."""

    def test_validate_valid_hook_config(self):
        """Test validating a valid hook configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "test-hook.json"
            hook_file.write_text(json.dumps({
                "version": "v1",
                "hooks": [
                    {
                        "name": "Test Hook",
                        "trigger": "PostFileSave",
                        "action": {"type": "command", "command": "echo test"}
                    }
                ]
            }))
            
            validator = ConfigValidator()
            result = validator.validate_file(hook_file)
            
            assert result.is_valid is True
            assert len(result.errors) == 0

    def test_validate_invalid_json(self):
        """Test validating invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "bad-hook.json"
            hook_file.write_text("{ invalid json }")
            
            validator = ConfigValidator()
            result = validator.validate_file(hook_file)
            
            assert result.is_valid is False
            assert any(e.code == "INVALID_JSON_SYNTAX" for e in result.errors)

    def test_validate_missing_hook_fields(self):
        """Test validating hook with missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = Path(tmpdir) / "incomplete-hook.json"
            hook_file.write_text(json.dumps({
                "version": "v1",
                "hooks": [
                    {"name": "Incomplete Hook"}  # Missing trigger and action
                ]
            }))
            
            validator = ConfigValidator()
            result = validator.validate_file(hook_file)
            
            assert result.is_valid is False
            assert any(e.code == "MISSING_HOOK_FIELD" for e in result.errors)

    def test_validate_hooks_directory(self):
        """Test validating a hooks directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hooks_dir = Path(tmpdir) / "hooks"
            hooks_dir.mkdir()
            
            # Valid hook
            (hooks_dir / "valid.json").write_text(json.dumps({
                "version": "v1",
                "hooks": [{"name": "Test", "trigger": "PostFileSave", "action": {"type": "command", "command": "echo test"}}]
            }))
            
            # Invalid hook
            (hooks_dir / "invalid.json").write_text("{ bad json }")
            
            validator = ConfigValidator()
            results = validator.validate_hooks_directory(hooks_dir)
            
            assert len(results) == 2
            assert any(r.is_valid for r in results)
            assert any(not r.is_valid for r in results)

    def test_validate_mcp_config(self):
        """Test validating MCP configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_file = Path(tmpdir) / "mcp.json"
            mcp_file.write_text(json.dumps({
                "mcpServers": {
                    "server1": {
                        "command": "node",
                        "args": ["server.js"]
                    }
                }
            }))
            
            validator = ConfigValidator()
            result = validator.validate_file(mcp_file)
            
            assert result.is_valid is True


# ============================================================================
# Health Reporter Tests (Task 2.11.2)
# ============================================================================

class TestHealthReporter:
    """Tests for HealthReporter."""

    def test_generate_report_basic(self):
        """Test generating a basic health report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = HealthReporter()
            report = reporter.generate_report(tmpdir)
            
            assert report.generated_at is not None
            assert report.workspace_root == tmpdir
            assert report.overall_status in ("healthy", "degraded", "unhealthy")

    def test_check_python_environment(self):
        """Test checking Python environment."""
        reporter = HealthReporter()
        
        python_status = reporter._check_python()
        
        assert python_status.available is True
        assert python_status.version is not None

    def test_health_report_with_kiro_directory(self):
        """Test health report with .kiro directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kiro_dir = Path(tmpdir) / ".kiro"
            hooks_dir = kiro_dir / "hooks"
            hooks_dir.mkdir(parents=True)
            
            reporter = HealthReporter()
            report = reporter.generate_report(tmpdir)
            
            assert report.configuration_status.get("kiro_directory_exists") is True
            assert report.configuration_status.get("hooks_directory_exists") is True

    def test_health_recommendations(self):
        """Test health recommendations generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = HealthReporter()
            report = reporter.generate_report(tmpdir)
            
            # Should recommend creating .kiro directory
            assert any(".kiro" in r for r in report.recommendations)


# ============================================================================
# Conflict Analyzer Tests (Task 2.11.3)
# ============================================================================

class TestConflictAnalyzer:
    """Tests for ConflictAnalyzer."""

    def test_analyze_empty_workspace(self):
        """Test analyzing empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = ConflictAnalyzer()
            report = analyzer.analyze(tmpdir)
            
            assert report.has_issues is False
            assert len(report.identifier_collisions) == 0

    def test_detect_identifier_collision(self):
        """Test detecting identifier collisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kiro_dir = Path(tmpdir) / ".kiro" / "hooks"
            kiro_dir.mkdir(parents=True)
            
            # Create two hook files with the same hook name
            (kiro_dir / "hook1.json").write_text(json.dumps({
                "version": "v1",
                "hooks": [{"name": "duplicate-name", "trigger": "PostFileSave", "action": {"type": "command", "command": "echo 1"}}]
            }))
            (kiro_dir / "hook2.json").write_text(json.dumps({
                "version": "v1",
                "hooks": [{"name": "duplicate-name", "trigger": "PreToolUse", "action": {"type": "command", "command": "echo 2"}}]
            }))
            
            analyzer = ConflictAnalyzer()
            report = analyzer.analyze(tmpdir)
            
            assert len(report.identifier_collisions) == 1
            assert report.identifier_collisions[0].identifier == "duplicate-name"

    def test_detect_missing_credentials(self):
        """Test detecting missing credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kiro_dir = Path(tmpdir) / ".kiro" / "hooks"
            kiro_dir.mkdir(parents=True)
            
            # Create hook referencing non-existent env var
            (kiro_dir / "hook.json").write_text(json.dumps({
                "version": "v1",
                "hooks": [{
                    "name": "test",
                    "trigger": "PostFileSave",
                    "action": {"type": "command", "command": "echo ${NONEXISTENT_VAR}"}
                }]
            }))
            
            analyzer = ConflictAnalyzer()
            report = analyzer.analyze(tmpdir)
            
            # Should detect missing env var (unless it's set in the environment)
            assert any(m.credential_name == "NONEXISTENT_VAR" for m in report.missing_credentials) or \
                   os.environ.get("NONEXISTENT_VAR") is not None

    def test_analyze_mcp_server_names(self):
        """Test analyzing MCP server names for collisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_dir = Path(tmpdir) / ".kiro" / "settings"
            settings_dir.mkdir(parents=True)
            
            (settings_dir / "mcp.json").write_text(json.dumps({
                "mcpServers": {
                    "my-server": {"command": "node", "args": ["server1.js"]},
                    "another-server": {"command": "node", "args": ["server2.js"]}
                }
            }))
            
            analyzer = ConflictAnalyzer()
            report = analyzer.analyze(tmpdir)
            
            # Should have scanned the identifiers
            assert report.stats.get("identifiers_scanned", 0) >= 2


# ============================================================================
# Full Diagnostics Tests
# ============================================================================

class TestFullDiagnostics:
    """Tests for run_full_diagnostics function."""

    def test_run_full_diagnostics(self):
        """Test running all diagnostics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kiro_dir = Path(tmpdir) / ".kiro"
            hooks_dir = kiro_dir / "hooks"
            hooks_dir.mkdir(parents=True)
            
            (hooks_dir / "test.json").write_text(json.dumps({
                "version": "v1",
                "hooks": [{"name": "Test", "trigger": "PostFileSave", "action": {"type": "command", "command": "echo test"}}]
            }))
            
            results = run_full_diagnostics(tmpdir)
            
            assert "timestamp" in results
            assert "workspace_root" in results
            assert "health_report" in results
            assert "overall_healthy" in results
