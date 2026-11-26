"""
Event Dispatcher for Kiro-SkillForge Pipeline.

Manages event hooks for automation, providing event registry, dispatching,
and async queue functionality.

Implements:
- Task 2.8.1: Event Registry - Store hook definitions for registered events
- Task 2.8.2: Event Dispatcher - Trigger hooks on phase completion/failure
- Task 2.8.3: Async Queue - Queue asynchronous hooks for background execution

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# Event Types
# ============================================================================

class PhaseEventType(str, Enum):
    """Types of phase events in the pipeline."""
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    SYNTHESIS_FAILURE = "synthesis_failure"
    PBT_START = "pbt_start"
    PBT_COMPLETE = "pbt_complete"
    PBT_FAILURE = "pbt_failure"
    DIAGNOSTICS_START = "diagnostics_start"
    DIAGNOSTICS_COMPLETE = "diagnostics_complete"
    DIAGNOSTICS_FAILURE = "diagnostics_failure"
    MCP_COMPILE_START = "mcp_compile_start"
    MCP_COMPILE_COMPLETE = "mcp_compile_complete"
    MCP_COMPILE_FAILURE = "mcp_compile_failure"
    PIPELINE_START = "pipeline_start"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILURE = "pipeline_failure"


class HookExecutionStatus(str, Enum):
    """Status of hook execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


# ============================================================================
# Hook Definitions (Task 2.8.1)
# ============================================================================

@dataclass
class RegisteredHook:
    """A hook registered with the event system."""
    hook_id: str
    event_type: PhaseEventType
    name: str
    action: Callable[[dict[str, Any]], None] | str  # Function or command string
    priority: int = 100  # Lower = earlier execution
    enabled: bool = True
    async_execution: bool = False
    timeout: float = 30.0
    max_retries: int = 0
    retry_delay: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: RegisteredHook) -> bool:
        """Compare by priority for sorting."""
        return self.priority < other.priority


@dataclass
class HookExecutionResult:
    """Result of executing a hook."""
    hook_id: str
    status: HookExecutionStatus
    started_at: str
    completed_at: str
    duration_ms: float
    output: str | None = None
    error: str | None = None
    retry_count: int = 0


class EventRegistry:
    """
    Stores hook definitions for registered events.

    Supports registration of phase completion hooks and phase failure hooks,
    with priority-based ordering and enable/disable functionality.

    Task 2.8.1: Event Registry
    Validates: Requirements 7.3

    Example:
        >>> registry = EventRegistry()
        >>> registry.register_hook("hook-1", PhaseEventType.SYNTHESIS_COMPLETE, my_callback)
        >>> hooks = registry.get_hooks(PhaseEventType.SYNTHESIS_COMPLETE)
        >>> len(hooks)
        1
    """

    def __init__(
        self,
        *,
        max_hooks_per_event: int = 100,
    ) -> None:
        """
        Initialize the event registry.

        Args:
            max_hooks_per_event: Maximum hooks allowed per event type
        """
        self._hooks: dict[PhaseEventType, list[RegisteredHook]] = defaultdict(list)
        self._hook_index: dict[str, RegisteredHook] = {}
        self._max_hooks_per_event = max_hooks_per_event

    def register_hook(
        self,
        hook_id: str,
        event_type: PhaseEventType,
        action: Callable[[dict[str, Any]], None] | str,
        *,
        name: str | None = None,
        priority: int = 100,
        enabled: bool = True,
        async_execution: bool = False,
        timeout: float = 30.0,
        max_retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Register a hook for an event type.

        Args:
            hook_id: Unique identifier for the hook
            event_type: Event type to hook
            action: Callback function or command string
            name: Human-readable name
            priority: Execution priority (lower = earlier)
            enabled: Whether hook is active
            async_execution: Whether to execute asynchronously
            timeout: Execution timeout in seconds
            max_retries: Maximum retry attempts on failure
            metadata: Additional hook metadata

        Returns:
            True if registration succeeded, False otherwise
        """
        # Check for duplicate ID
        if hook_id in self._hook_index:
            logger.warning(f"Hook ID '{hook_id}' already registered")
            return False

        # Check max hooks limit
        if len(self._hooks[event_type]) >= self._max_hooks_per_event:
            logger.warning(f"Max hooks reached for event {event_type}")
            return False

        hook = RegisteredHook(
            hook_id=hook_id,
            event_type=event_type,
            name=name or f"Hook-{hook_id}",
            action=action,
            priority=priority,
            enabled=enabled,
            async_execution=async_execution,
            timeout=timeout,
            max_retries=max_retries,
            metadata=metadata or {},
        )

        self._hooks[event_type].append(hook)
        self._hooks[event_type].sort()  # Sort by priority
        self._hook_index[hook_id] = hook

        logger.debug(f"Registered hook '{hook_id}' for event {event_type}")
        return True

    def unregister_hook(self, hook_id: str) -> bool:
        """
        Unregister a hook by ID.

        Args:
            hook_id: ID of hook to remove

        Returns:
            True if hook was removed, False if not found
        """
        if hook_id not in self._hook_index:
            return False

        hook = self._hook_index.pop(hook_id)
        self._hooks[hook.event_type] = [
            h for h in self._hooks[hook.event_type] if h.hook_id != hook_id
        ]
        logger.debug(f"Unregistered hook '{hook_id}'")
        return True

    def get_hooks(
        self,
        event_type: PhaseEventType,
        *,
        enabled_only: bool = True,
    ) -> list[RegisteredHook]:
        """
        Get all hooks for an event type.

        Args:
            event_type: Event type to query
            enabled_only: Only return enabled hooks

        Returns:
            List of registered hooks, sorted by priority
        """
        hooks = self._hooks.get(event_type, [])
        if enabled_only:
            hooks = [h for h in hooks if h.enabled]
        return hooks.copy()

    def get_hook(self, hook_id: str) -> RegisteredHook | None:
        """
        Get a specific hook by ID.

        Args:
            hook_id: Hook ID to look up

        Returns:
            RegisteredHook or None if not found
        """
        return self._hook_index.get(hook_id)

    def enable_hook(self, hook_id: str) -> bool:
        """Enable a hook by ID."""
        hook = self._hook_index.get(hook_id)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable_hook(self, hook_id: str) -> bool:
        """Disable a hook by ID."""
        hook = self._hook_index.get(hook_id)
        if hook:
            hook.enabled = False
            return True
        return False

    def clear_event(self, event_type: PhaseEventType) -> int:
        """
        Remove all hooks for an event type.

        Args:
            event_type: Event type to clear

        Returns:
            Number of hooks removed
        """
        hooks = self._hooks.pop(event_type, [])
        for hook in hooks:
            self._hook_index.pop(hook.hook_id, None)
        return len(hooks)

    def clear_all(self) -> int:
        """
        Remove all registered hooks.

        Returns:
            Total number of hooks removed
        """
        count = len(self._hook_index)
        self._hooks.clear()
        self._hook_index.clear()
        return count

    @property
    def total_hooks(self) -> int:
        """Total number of registered hooks."""
        return len(self._hook_index)


# ============================================================================
# Event Dispatcher (Task 2.8.2)
# ============================================================================

@runtime_checkable
class HookExecutor(Protocol):
    """Protocol for hook execution."""

    def execute(
        self,
        hook: RegisteredHook,
        event_data: dict[str, Any],
    ) -> HookExecutionResult:
        """Execute a hook with event data."""
        ...


class DefaultHookExecutor:
    """Default executor for hook actions."""

    def execute(
        self,
        hook: RegisteredHook,
        event_data: dict[str, Any],
    ) -> HookExecutionResult:
        """
        Execute a hook action.

        Supports both callable and command string actions.

        Args:
            hook: The hook to execute
            event_data: Data to pass to the hook

        Returns:
            HookExecutionResult with execution status
        """
        started_at = datetime.utcnow().isoformat()
        start_time = datetime.utcnow()

        try:
            if callable(hook.action):
                # Execute callable
                hook.action(event_data)
                output = None
            else:
                # Execute command
                result = subprocess.run(
                    hook.action,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=hook.timeout,
                    input=json.dumps(event_data),
                )
                output = result.stdout
                if result.returncode != 0:
                    raise RuntimeError(f"Command failed with code {result.returncode}: {result.stderr}")

            status = HookExecutionStatus.SUCCESS

        except subprocess.TimeoutExpired:
            status = HookExecutionStatus.TIMEOUT
            output = None

        except Exception as e:
            status = HookExecutionStatus.FAILED
            output = None
            logger.error(f"Hook '{hook.hook_id}' failed: {e}")

        completed_at = datetime.utcnow().isoformat()
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return HookExecutionResult(
            hook_id=hook.hook_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            output=output,
        )


class EventDispatcher:
    """
    Dispatches events to registered hooks.

    Triggers hooks on phase completion and failure, executing registered
    hooks in order and handling errors gracefully.

    Task 2.8.2: Event Dispatcher
    Validates: Requirements 7.1, 7.2, 7.4, 7.5

    Example:
        >>> registry = EventRegistry()
        >>> dispatcher = EventDispatcher(registry)
        >>> dispatcher.dispatch(PhaseEventType.SYNTHESIS_COMPLETE, {"skill": "my-skill"})
    """

    def __init__(
        self,
        registry: EventRegistry,
        *,
        executor: HookExecutor | None = None,
        continue_on_error: bool = True,
        log_errors: bool = True,
    ) -> None:
        """
        Initialize the event dispatcher.

        Args:
            registry: Event registry to use
            executor: Custom hook executor (uses default if None)
            continue_on_error: Continue dispatching if a hook fails
            log_errors: Log hook execution errors
        """
        self.registry = registry
        self.executor = executor or DefaultHookExecutor()
        self.continue_on_error = continue_on_error
        self.log_errors = log_errors
        self._execution_history: list[HookExecutionResult] = []

    def dispatch(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> list[HookExecutionResult]:
        """
        Dispatch an event to all registered hooks.

        Hooks are executed in priority order. Errors are logged but
        other hooks continue execution (unless configured otherwise).

        Args:
            event_type: Type of event to dispatch
            event_data: Data to pass to hooks

        Returns:
            List of execution results for all hooks
        """
        hooks = self.registry.get_hooks(event_type, enabled_only=True)
        results: list[HookExecutionResult] = []

        if not hooks:
            logger.debug(f"No hooks registered for event {event_type}")
            return results

        logger.info(f"Dispatching event {event_type} to {len(hooks)} hook(s)")

        # Add event metadata
        event_data["_event_type"] = event_type.value
        event_data["_timestamp"] = datetime.utcnow().isoformat()

        for hook in hooks:
            result = self._execute_with_retries(hook, event_data)
            results.append(result)
            self._execution_history.append(result)

            # Handle failure
            if result.status != HookExecutionStatus.SUCCESS:
                if self.log_errors:
                    logger.error(
                        f"Hook '{hook.hook_id}' failed with status {result.status}: "
                        f"{result.error or 'no error message'}"
                    )

                if not self.continue_on_error:
                    break

        return results

    def dispatch_sync(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> list[HookExecutionResult]:
        """
        Synchronously dispatch an event (alias for dispatch).

        All hooks complete before returning.

        Args:
            event_type: Type of event to dispatch
            event_data: Data to pass to hooks

        Returns:
            List of execution results
        """
        return self.dispatch(event_type, event_data)

    def _execute_with_retries(
        self,
        hook: RegisteredHook,
        event_data: dict[str, Any],
    ) -> HookExecutionResult:
        """Execute a hook with retry logic."""
        attempts = 0
        max_attempts = hook.max_retries + 1
        last_result: HookExecutionResult | None = None

        while attempts < max_attempts:
            result = self.executor.execute(hook, event_data)
            result.retry_count = attempts

            if result.status == HookExecutionStatus.SUCCESS:
                return result

            last_result = result
            attempts += 1

            if attempts < max_attempts:
                import time
                time.sleep(hook.retry_delay)

        return last_result or HookExecutionResult(
            hook_id=hook.hook_id,
            status=HookExecutionStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            duration_ms=0,
            error="No execution attempts made",
        )

    def get_execution_history(
        self,
        *,
        hook_id: str | None = None,
        status: HookExecutionStatus | None = None,
        limit: int = 100,
    ) -> list[HookExecutionResult]:
        """
        Get hook execution history.

        Args:
            hook_id: Filter by hook ID
            status: Filter by execution status
            limit: Maximum results to return

        Returns:
            List of matching execution results
        """
        results = self._execution_history

        if hook_id:
            results = [r for r in results if r.hook_id == hook_id]
        if status:
            results = [r for r in results if r.status == status]

        return results[-limit:]

    def clear_history(self) -> int:
        """Clear execution history. Returns count cleared."""
        count = len(self._execution_history)
        self._execution_history.clear()
        return count


# ============================================================================
# Async Queue (Task 2.8.3)
# ============================================================================

@dataclass
class QueuedHook:
    """A hook queued for async execution."""
    hook: RegisteredHook
    event_data: dict[str, Any]
    queued_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: HookExecutionResult | None = None


class AsyncHookQueue:
    """
    Queue for asynchronous hook execution.

    Queues hooks for background execution without blocking the main pipeline.
    Uses a background thread to process the queue.

    Task 2.8.3: Async Queue
    Validates: Requirements 7.6

    Example:
        >>> queue = AsyncHookQueue()
        >>> queue.start()
        >>> queue.enqueue(hook, event_data)
        >>> queue.stop()
    """

    def __init__(
        self,
        *,
        max_size: int = 1000,
        worker_count: int = 1,
        poll_interval: float = 0.1,
    ) -> None:
        """
        Initialize the async queue.

        Args:
            max_size: Maximum queue size
            worker_count: Number of worker threads (currently 1 supported)
            poll_interval: Seconds to wait between queue polls
        """
        self._queue: list[QueuedHook] = []
        self._max_size = max_size
        self._poll_interval = poll_interval
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._completed: list[QueuedHook] = []

    def start(self) -> None:
        """Start the queue processor."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        logger.info("Async hook queue started")

    def stop(self, *, wait: bool = True, timeout: float = 5.0) -> None:
        """
        Stop the queue processor.

        Args:
            wait: Wait for current processing to complete
            timeout: Maximum seconds to wait
        """
        if not self._running:
            return

        self._running = False

        with self._condition:
            self._condition.notify_all()

        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)

        logger.info("Async hook queue stopped")

    def enqueue(
        self,
        hook: RegisteredHook,
        event_data: dict[str, Any],
    ) -> bool:
        """
        Enqueue a hook for background execution.

        Args:
            hook: Hook to execute
            event_data: Event data to pass

        Returns:
            True if enqueued, False if queue is full
        """
        with self._lock:
            if len(self._queue) >= self._max_size:
                logger.warning("Async hook queue is full")
                return False

            queued = QueuedHook(
                hook=hook,
                event_data=event_data,
                queued_at=datetime.utcnow().isoformat(),
            )
            self._queue.append(queued)

        with self._condition:
            self._condition.notify()

        logger.debug(f"Enqueued hook '{hook.hook_id}' for async execution")
        return True

    def get_queue_size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._queue)

    def get_completed(
        self,
        *,
        limit: int = 100,
    ) -> list[QueuedHook]:
        """
        Get completed hook executions.

        Args:
            limit: Maximum results to return

        Returns:
            List of completed queued hooks
        """
        with self._lock:
            return self._completed[-limit:]

    def clear_completed(self) -> int:
        """Clear completed hook history. Returns count cleared."""
        with self._lock:
            count = len(self._completed)
            self._completed.clear()
            return count

    def _process_queue(self) -> None:
        """Background thread that processes the queue."""
        executor = DefaultHookExecutor()

        while self._running:
            queued_item: QueuedHook | None = None

            with self._lock:
                if self._queue:
                    queued_item = self._queue.pop(0)

            if queued_item:
                queued_item.started_at = datetime.utcnow().isoformat()

                try:
                    result = executor.execute(
                        queued_item.hook,
                        queued_item.event_data,
                    )
                    queued_item.result = result
                    queued_item.completed_at = datetime.utcnow().isoformat()

                    if result.status != HookExecutionStatus.SUCCESS:
                        logger.warning(
                            f"Async hook '{queued_item.hook.hook_id}' failed: {result.error}"
                        )

                except Exception as e:
                    queued_item.result = HookExecutionResult(
                        hook_id=queued_item.hook.hook_id,
                        status=HookExecutionStatus.FAILED,
                        started_at=queued_item.started_at,
                        completed_at=datetime.utcnow().isoformat(),
                        duration_ms=0,
                        error=str(e),
                    )
                    queued_item.completed_at = datetime.utcnow().isoformat()
                    logger.error(f"Async hook '{queued_item.hook.hook_id}' error: {e}")

                with self._lock:
                    self._completed.append(queued_item)

            else:
                with self._condition:
                    self._condition.wait(self._poll_interval)


class AsyncEventDispatcher:
    """
    Event dispatcher with async queue support.

    Combines synchronous dispatch for critical hooks with async queuing
    for non-blocking hooks.

    Example:
        >>> registry = EventRegistry()
        >>> dispatcher = AsyncEventDispatcher(registry)
        >>> dispatcher.start()
        >>> dispatcher.dispatch_async(PhaseEventType.SYNTHESIS_COMPLETE, data)
    """

    def __init__(
        self,
        registry: EventRegistry,
        *,
        queue_size: int = 1000,
    ) -> None:
        """
        Initialize the async dispatcher.

        Args:
            registry: Event registry to use
            queue_size: Maximum async queue size
        """
        self.registry = registry
        self._sync_dispatcher = EventDispatcher(registry)
        self._async_queue = AsyncHookQueue(max_size=queue_size)

    def start(self) -> None:
        """Start the async queue processor."""
        self._async_queue.start()

    def stop(self, *, wait: bool = True) -> None:
        """Stop the async queue processor."""
        self._async_queue.stop(wait=wait)

    def dispatch(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> list[HookExecutionResult]:
        """
        Dispatch event to sync hooks only.

        Args:
            event_type: Event type to dispatch
            event_data: Event data

        Returns:
            Execution results from sync hooks
        """
        return self._sync_dispatcher.dispatch(event_type, event_data)

    def dispatch_async(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> tuple[list[HookExecutionResult], int]:
        """
        Dispatch event to sync hooks and queue async hooks.

        Args:
            event_type: Event type to dispatch
            event_data: Event data

        Returns:
            Tuple of (sync results, async hooks queued count)
        """
        hooks = self.registry.get_hooks(event_type, enabled_only=True)

        sync_hooks = [h for h in hooks if not h.async_execution]
        async_hooks = [h for h in hooks if h.async_execution]

        # Execute sync hooks
        results: list[HookExecutionResult] = []
        event_data_copy = event_data.copy()

        for hook in sync_hooks:
            result = self._sync_dispatcher._execute_with_retries(hook, event_data_copy)
            results.append(result)

        # Queue async hooks
        async_count = 0
        for hook in async_hooks:
            if self._async_queue.enqueue(hook, event_data.copy()):
                async_count += 1

        return (results, async_count)

    def dispatch_all_async(
        self,
        event_type: PhaseEventType,
        event_data: dict[str, Any],
    ) -> int:
        """
        Dispatch event entirely through async queue.

        Args:
            event_type: Event type to dispatch
            event_data: Event data

        Returns:
            Number of hooks queued
        """
        hooks = self.registry.get_hooks(event_type, enabled_only=True)
        count = 0

        for hook in hooks:
            if self._async_queue.enqueue(hook, event_data.copy()):
                count += 1

        return count

    def get_queue_size(self) -> int:
        """Get current async queue size."""
        return self._async_queue.get_queue_size()
