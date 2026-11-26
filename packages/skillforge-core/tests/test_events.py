"""
Tests for Event Dispatcher module.

Tests for:
- Task 2.8.1: Event Registry
- Task 2.8.2: Event Dispatcher
- Task 2.8.3: Async Queue
"""

import pytest
import threading
import time
from unittest.mock import MagicMock, patch

from skillforge.events import (
    EventRegistry,
    EventDispatcher,
    AsyncHookQueue,
    AsyncEventDispatcher,
    PhaseEventType,
    HookExecutionStatus,
    RegisteredHook,
    HookExecutionResult,
    DefaultHookExecutor,
)


# ============================================================================
# Event Registry Tests (Task 2.8.1)
# ============================================================================

class TestEventRegistry:
    """Tests for EventRegistry."""

    def test_register_hook_basic(self):
        """Test basic hook registration."""
        registry = EventRegistry()
        
        callback = lambda data: None
        
        result = registry.register_hook(
            "hook-1",
            PhaseEventType.SYNTHESIS_COMPLETE,
            callback,
        )
        
        assert result is True
        assert registry.total_hooks == 1

    def test_register_hook_with_options(self):
        """Test hook registration with options."""
        registry = EventRegistry()
        
        registry.register_hook(
            "hook-1",
            PhaseEventType.PBT_COMPLETE,
            "echo 'test'",
            name="Test Hook",
            priority=50,
            async_execution=True,
        )
        
        hook = registry.get_hook("hook-1")
        
        assert hook is not None
        assert hook.name == "Test Hook"
        assert hook.priority == 50
        assert hook.async_execution is True

    def test_register_duplicate_hook(self):
        """Test that duplicate hook IDs are rejected."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        result = registry.register_hook("hook-1", PhaseEventType.PBT_COMPLETE, lambda x: None)
        
        assert result is False
        assert registry.total_hooks == 1

    def test_unregister_hook(self):
        """Test hook unregistration."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        result = registry.unregister_hook("hook-1")
        
        assert result is True
        assert registry.total_hooks == 0

    def test_unregister_nonexistent_hook(self):
        """Test unregistering nonexistent hook."""
        registry = EventRegistry()
        
        result = registry.unregister_hook("nonexistent")
        
        assert result is False

    def test_get_hooks_by_event_type(self):
        """Test getting hooks by event type."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        registry.register_hook("hook-2", PhaseEventType.PBT_COMPLETE, lambda x: None)
        registry.register_hook("hook-3", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        
        hooks = registry.get_hooks(PhaseEventType.SYNTHESIS_COMPLETE)
        
        assert len(hooks) == 2

    def test_get_hooks_enabled_only(self):
        """Test getting only enabled hooks."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        registry.register_hook("hook-2", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None, enabled=False)
        
        hooks = registry.get_hooks(PhaseEventType.SYNTHESIS_COMPLETE, enabled_only=True)
        
        assert len(hooks) == 1
        assert hooks[0].hook_id == "hook-1"

    def test_enable_disable_hook(self):
        """Test enabling and disabling hooks."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        
        registry.disable_hook("hook-1")
        hook = registry.get_hook("hook-1")
        assert hook.enabled is False
        
        registry.enable_hook("hook-1")
        hook = registry.get_hook("hook-1")
        assert hook.enabled is True

    def test_hooks_sorted_by_priority(self):
        """Test that hooks are sorted by priority."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None, priority=100)
        registry.register_hook("hook-2", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None, priority=10)
        registry.register_hook("hook-3", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None, priority=50)
        
        hooks = registry.get_hooks(PhaseEventType.SYNTHESIS_COMPLETE)
        
        assert hooks[0].hook_id == "hook-2"  # priority 10
        assert hooks[1].hook_id == "hook-3"  # priority 50
        assert hooks[2].hook_id == "hook-1"  # priority 100

    def test_clear_event(self):
        """Test clearing all hooks for an event."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        registry.register_hook("hook-2", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        registry.register_hook("hook-3", PhaseEventType.PBT_COMPLETE, lambda x: None)
        
        count = registry.clear_event(PhaseEventType.SYNTHESIS_COMPLETE)
        
        assert count == 2
        assert registry.total_hooks == 1

    def test_clear_all(self):
        """Test clearing all hooks."""
        registry = EventRegistry()
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        registry.register_hook("hook-2", PhaseEventType.PBT_COMPLETE, lambda x: None)
        
        count = registry.clear_all()
        
        assert count == 2
        assert registry.total_hooks == 0


# ============================================================================
# Event Dispatcher Tests (Task 2.8.2)
# ============================================================================

class TestEventDispatcher:
    """Tests for EventDispatcher."""

    def test_dispatch_to_hooks(self):
        """Test dispatching event to hooks."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        call_log = []
        
        def hook_callback(data):
            call_log.append(data)
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, hook_callback)
        
        results = dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {"skill": "test"})
        
        assert len(call_log) == 1
        assert call_log[0]["skill"] == "test"
        assert len(results) == 1
        assert results[0].status == HookExecutionStatus.SUCCESS

    def test_dispatch_to_multiple_hooks_in_order(self):
        """Test dispatching to multiple hooks in priority order."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        call_order = []
        
        def hook1(data):
            call_order.append(1)
        
        def hook2(data):
            call_order.append(2)
        
        def hook3(data):
            call_order.append(3)
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, hook1, priority=30)
        registry.register_hook("hook-2", PhaseEventType.SYNTHESIS_COMPLETE, hook2, priority=10)
        registry.register_hook("hook-3", PhaseEventType.SYNTHESIS_COMPLETE, hook3, priority=20)
        
        dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        
        assert call_order == [2, 3, 1]  # Sorted by priority

    def test_dispatch_continues_on_error(self):
        """Test that dispatching continues even if a hook fails."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry, continue_on_error=True)
        
        call_log = []
        
        def failing_hook(data):
            raise RuntimeError("Hook failed")
        
        def success_hook(data):
            call_log.append("success")
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, failing_hook)
        registry.register_hook("hook-2", PhaseEventType.SYNTHESIS_COMPLETE, success_hook)
        
        results = dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        
        assert len(results) == 2
        assert results[0].status == HookExecutionStatus.FAILED
        assert results[1].status == HookExecutionStatus.SUCCESS
        assert "success" in call_log

    def test_dispatch_no_hooks(self):
        """Test dispatching when no hooks registered."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        results = dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        
        assert len(results) == 0

    def test_execution_history(self):
        """Test getting execution history."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        
        dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        
        history = dispatcher.get_execution_history()
        
        assert len(history) == 2

    def test_clear_history(self):
        """Test clearing execution history."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, lambda x: None)
        
        dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {})
        count = dispatcher.clear_history()
        
        assert count == 1
        assert len(dispatcher.get_execution_history()) == 0

    def test_hook_result_metadata(self):
        """Test that hook results include event metadata."""
        registry = EventRegistry()
        dispatcher = EventDispatcher(registry)
        
        received_data = {}
        
        def capture_hook(data):
            received_data.update(data)
        
        registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, capture_hook)
        
        dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {"skill": "test"})
        
        assert "_event_type" in received_data
        assert received_data["_event_type"] == "synthesis_complete"
        assert "_timestamp" in received_data


# ============================================================================
# Async Queue Tests (Task 2.8.3)
# ============================================================================

class TestAsyncHookQueue:
    """Tests for AsyncHookQueue."""

    def test_enqueue_and_process(self):
        """Test enqueuing and processing hooks."""
        queue = AsyncHookQueue()
        queue.start()
        
        try:
            hook = RegisteredHook(
                hook_id="test-hook",
                event_type=PhaseEventType.SYNTHESIS_COMPLETE,
                name="Test",
                action="echo 'test'",
            )
            
            result = queue.enqueue(hook, {"test": "data"})
            assert result is True
            
            # Wait for processing
            time.sleep(0.5)
            
            completed = queue.get_completed()
            assert len(completed) == 1
            assert completed[0].hook.hook_id == "test-hook"
        finally:
            queue.stop()

    def test_queue_size_limit(self):
        """Test queue size limit."""
        queue = AsyncHookQueue(max_size=2)
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action="echo 'test'",
        )
        
        assert queue.enqueue(hook, {}) is True
        assert queue.enqueue(hook, {}) is True
        assert queue.enqueue(hook, {}) is False  # Queue full

    def test_get_queue_size(self):
        """Test getting queue size."""
        queue = AsyncHookQueue()
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action="echo 'test'",
        )
        
        queue.enqueue(hook, {})
        queue.enqueue(hook, {})
        
        assert queue.get_queue_size() == 2

    def test_clear_completed(self):
        """Test clearing completed hooks."""
        queue = AsyncHookQueue()
        queue.start()
        
        try:
            hook = RegisteredHook(
                hook_id="test",
                event_type=PhaseEventType.SYNTHESIS_COMPLETE,
                name="Test",
                action="echo 'test'",
            )
            
            queue.enqueue(hook, {})
            time.sleep(0.3)
            
            count = queue.clear_completed()
            assert count == 1
        finally:
            queue.stop()


class TestAsyncEventDispatcher:
    """Tests for AsyncEventDispatcher."""

    def test_dispatch_async(self):
        """Test async dispatching."""
        registry = EventRegistry()
        dispatcher = AsyncEventDispatcher(registry)
        dispatcher.start()
        
        try:
            # Register sync hook
            registry.register_hook(
                "sync-hook",
                PhaseEventType.SYNTHESIS_COMPLETE,
                lambda x: None,
                async_execution=False,
            )
            
            # Register async hook
            registry.register_hook(
                "async-hook",
                PhaseEventType.SYNTHESIS_COMPLETE,
                "echo 'async'",
                async_execution=True,
            )
            
            results, async_count = dispatcher.dispatch_async(
                PhaseEventType.SYNTHESIS_COMPLETE,
                {"test": "data"},
            )
            
            assert len(results) == 1  # Only sync result
            assert async_count == 1  # One async hook queued
        finally:
            dispatcher.stop()

    def test_dispatch_all_async(self):
        """Test dispatching all hooks asynchronously."""
        registry = EventRegistry()
        dispatcher = AsyncEventDispatcher(registry)
        dispatcher.start()
        
        try:
            registry.register_hook(
                "hook-1",
                PhaseEventType.SYNTHESIS_COMPLETE,
                "echo 'test1'",
            )
            registry.register_hook(
                "hook-2",
                PhaseEventType.SYNTHESIS_COMPLETE,
                "echo 'test2'",
            )
            
            count = dispatcher.dispatch_all_async(
                PhaseEventType.SYNTHESIS_COMPLETE,
                {},
            )
            
            assert count == 2
        finally:
            dispatcher.stop()

    def test_get_queue_size(self):
        """Test getting queue size from dispatcher."""
        registry = EventRegistry()
        dispatcher = AsyncEventDispatcher(registry)
        
        assert dispatcher.get_queue_size() == 0


# ============================================================================
# Hook Executor Tests
# ============================================================================

class TestDefaultHookExecutor:
    """Tests for DefaultHookExecutor."""

    def test_execute_callable(self):
        """Test executing a callable hook."""
        executor = DefaultHookExecutor()
        
        call_log = []
        
        def callback(data):
            call_log.append(data)
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action=callback,
        )
        
        result = executor.execute(hook, {"test": "data"})
        
        assert result.status == HookExecutionStatus.SUCCESS
        assert len(call_log) == 1

    def test_execute_command_success(self):
        """Test executing a command that succeeds."""
        executor = DefaultHookExecutor()
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action="echo 'test output'",
            timeout=5,
        )
        
        result = executor.execute(hook, {})
        
        assert result.status == HookExecutionStatus.SUCCESS
        assert "test output" in result.output

    def test_execute_command_timeout(self):
        """Test command timeout."""
        executor = DefaultHookExecutor()
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action="sleep 10",  # Long-running command
            timeout=0.5,  # Short timeout
        )
        
        result = executor.execute(hook, {})
        
        assert result.status == HookExecutionStatus.TIMEOUT

    def test_execution_timing(self):
        """Test that execution timing is recorded."""
        executor = DefaultHookExecutor()
        
        hook = RegisteredHook(
            hook_id="test",
            event_type=PhaseEventType.SYNTHESIS_COMPLETE,
            name="Test",
            action="echo 'test'",
        )
        
        result = executor.execute(hook, {})
        
        assert result.duration_ms >= 0
        assert result.started_at != ""
        assert result.completed_at != ""


# ============================================================================
# Phase Event Types Tests
# ============================================================================

class TestPhaseEventType:
    """Tests for PhaseEventType enum."""

    def test_all_event_types_exist(self):
        """Test that all expected event types exist."""
        expected = [
            "synthesis_start",
            "synthesis_complete",
            "synthesis_failure",
            "pbt_start",
            "pbt_complete",
            "pbt_failure",
            "diagnostics_start",
            "diagnostics_complete",
            "diagnostics_failure",
            "mcp_compile_start",
            "mcp_compile_complete",
            "mcp_compile_failure",
            "pipeline_start",
            "pipeline_complete",
            "pipeline_failure",
        ]
        
        for event_name in expected:
            event = PhaseEventType(event_name)
            assert event.value == event_name

    def test_event_type_string_conversion(self):
        """Test converting event type to string."""
        event = PhaseEventType.SYNTHESIS_COMPLETE
        assert event.value == "synthesis_complete"
