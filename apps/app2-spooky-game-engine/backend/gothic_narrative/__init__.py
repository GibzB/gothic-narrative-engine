"""
Gothic Narrative Engine - Interactive branching horror stories.

A web-based interactive narrative engine featuring:
- Branching gothic horror stories
- State-machine based narrative logic
- WebGL atmospheric effects
- Dark-mode gothic UI

Implements:
- Task 4.4: Narrative Engine - Branching horror stories
- Task 4.5: Context Graph - Story state management
- Task 4.6: PostFileSave Hook - Asset tracking
"""

__version__ = "0.1.0"

from gothic_narrative.narrative_engine import (
    NarrativeEngine,
    StoryScene,
    StoryChoice,
    PlayerState,
    NarrativeState,
    StoryPhase,
    Mood,
    create_demo_story,
)

from gothic_narrative.context_graph import (
    ContextGraph,
    GraphNode,
    GraphEdge,
    EdgeType,
    ContextSnapshot,
)

from gothic_narrative.postfilesave_hook import (
    PostFileSaveHook,
    AssetTracker,
    AssetChange,
    ValidationResult,
)

__all__ = [
    # Narrative Engine
    "NarrativeEngine",
    "StoryScene",
    "StoryChoice",
    "PlayerState",
    "NarrativeState",
    "StoryPhase",
    "Mood",
    "create_demo_story",
    # Context Graph
    "ContextGraph",
    "GraphNode",
    "GraphEdge",
    "EdgeType",
    "ContextSnapshot",
    # Asset Tracking
    "PostFileSaveHook",
    "AssetTracker",
    "AssetChange",
    "ValidationResult",
]
