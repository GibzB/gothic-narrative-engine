"""
Tests for Gothic Narrative Engine.

Unit and property-based tests for narrative engine, context graph,
and asset tracking.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from gothic_narrative.narrative_engine import (
    NarrativeEngine,
    StoryPhase,
    Mood,
    create_demo_story,
)
from gothic_narrative.context_graph import (
    ContextGraph,
    EdgeType,
)
from gothic_narrative.postfilesave_hook import (
    AssetTracker,
    PostFileSaveHook,
)


# =========================================================================
# Narrative Engine Tests
# =========================================================================

class TestNarrativeEngine:
    """Tests for the narrative engine."""

    def test_load_demo_story(self) -> None:
        """Test loading the demo story."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)

        assert engine.current_scene is None  # Not started yet

    def test_start_story(self) -> None:
        """Test starting a story."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)

        scene = engine.start_story("start")

        assert scene is not None
        assert scene.id == "start"
        assert engine.player_state.current_scene == "start"

    def test_make_choice(self) -> None:
        """Test making a choice."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        result = engine.make_choice("enter_front")

        assert result["success"]
        assert result["currentScene"] == "foyer"

    def test_get_available_choices(self) -> None:
        """Test getting available choices."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        choices = engine.get_available_choices()

        assert len(choices) > 0
        assert all(c.is_visible for c in choices)

    def test_story_state_tracking(self) -> None:
        """Test that story state is tracked."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        # Make some choices
        engine.make_choice("enter_front")

        state = engine.get_story_state()

        assert state["turnCount"] == 1
        assert len(state["state"]["player"]["visitedScenes"]) == 2

    def test_procedural_event_generation(self) -> None:
        """Test generating procedural events."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        event = engine.generate_procedural_event("whisper")

        assert "text" in event
        assert event["mood"] in [m.value for m in Mood]

    def test_is_story_complete(self) -> None:
        """Test checking if story is complete."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        assert not engine.is_story_complete()

        # Navigate to an ending
        engine.player_state.current_scene = "ending_escape"

        assert engine.is_story_complete()


# =========================================================================
# Context Graph Tests
# =========================================================================

class TestContextGraph:
    """Tests for context graph."""

    def test_add_scene(self) -> None:
        """Test adding a scene node."""
        graph = ContextGraph()
        node = graph.add_scene("start", {"title": "The Gates"})

        assert graph.node_count == 1
        assert node.id == "start"
        assert node.node_type == "scene"

    def test_add_transition(self) -> None:
        """Test adding a scene transition."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.add_scene("foyer")
        graph.add_transition("start", "foyer")

        assert graph.edge_count == 1

    def test_can_reach(self) -> None:
        """Test reachability check."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.add_scene("foyer")
        graph.add_scene("library")
        graph.add_transition("start", "foyer")
        graph.add_transition("foyer", "library")

        assert graph.can_reach("start", "library")
        assert not graph.can_reach("library", "start")

    def test_get_path(self) -> None:
        """Test path finding."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.add_scene("foyer")
        graph.add_scene("library")
        graph.add_transition("start", "foyer")
        graph.add_transition("foyer", "library")

        path = graph.get_path("start", "library")

        assert path is not None
        assert path[0] == "start"
        assert path[-1] == "library"

    def test_flags(self) -> None:
        """Test flag management."""
        graph = ContextGraph()

        graph.set_flag("visited_foyer", True)
        assert graph.get_flag("visited_foyer")
        assert not graph.get_flag("visited_library")

    def test_variables(self) -> None:
        """Test variable management."""
        graph = ContextGraph()

        graph.set_variable("sanity", 100)
        assert graph.get_variable("sanity") == 100
        assert graph.get_variable("nonexistent", "default") == "default"

    def test_dependencies(self) -> None:
        """Test dependency tracking."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.add_scene("locked_door")
        graph.add_scene("treasure_room")
        graph.add_transition("start", "locked_door")
        graph.add_transition("locked_door", "treasure_room")
        graph.add_dependency("treasure_room", "locked_door", dependency_type="requires_key")

        deps = graph.get_dependencies("treasure_room")
        assert "locked_door" in deps

    def test_item_location(self) -> None:
        """Test item location tracking."""
        graph = ContextGraph()
        graph.add_item("rusty_key")
        graph.add_scene("foyer")
        graph.add_item_location("rusty_key", "foyer")

        location = graph.get_item_location("rusty_key")
        assert location == "foyer"

    def test_move_item(self) -> None:
        """Test moving items."""
        graph = ContextGraph()
        graph.add_item("rusty_key")
        graph.add_scene("foyer")
        graph.add_scene("library")
        graph.add_item_location("rusty_key", "foyer")

        graph.move_item("rusty_key", "library")

        assert graph.get_item_location("rusty_key") == "library"

    def test_snapshot(self) -> None:
        """Test creating and restoring snapshots."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.set_flag("test", True)

        snapshot = graph.create_snapshot()
        graph.set_flag("test", False)

        assert not graph.get_flag("test")

        graph.restore_snapshot(snapshot)
        assert graph.get_flag("test")

    def test_serialization(self) -> None:
        """Test JSON serialization."""
        graph = ContextGraph()
        graph.add_scene("start")
        graph.add_scene("foyer")
        graph.add_transition("start", "foyer")
        graph.set_flag("visited", True)

        data = graph.to_dict()
        restored = ContextGraph.from_dict(data)

        assert restored.node_count == graph.node_count
        assert restored.edge_count == graph.edge_count
        assert restored.get_flag("visited")


# =========================================================================
# Asset Tracker Tests
# =========================================================================

class TestAssetTracker:
    """Tests for asset tracker."""

    def test_detect_story_type(self, tmp_path: Path) -> None:
        """Test detecting story asset type."""
        tracker = AssetTracker()

        story_file = tmp_path / "haunted_manor.story.json"
        story_file.touch()

        asset_type, asset_id = tracker.detect_asset_type(story_file)
        assert asset_type == "story"

    def test_detect_skill_type(self, tmp_path: Path) -> None:
        """Test detecting skill asset type."""
        tracker = AssetTracker()

        skill_dir = tmp_path / "my_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.touch()

        asset_type, asset_id = tracker.detect_asset_type(skill_file)
        assert asset_type == "skill"

    def test_validate_story(self, tmp_path: Path) -> None:
        """Test validating a story file."""
        tracker = AssetTracker()

        story_file = tmp_path / "test.story.json"
        story_file.write_text(json.dumps({
            "metadata": {
                "title": "Test Story",
                "version": "1.0.0"
            },
            "scenes": {
                "start": {
                    "title": "Start",
                    "description": "You begin.",
                    "choices": []
                }
            }
        }))

        result = tracker.process_file(story_file)

        assert result.is_valid
        assert result.asset_type == "story"

    def test_validate_invalid_json(self, tmp_path: Path) -> None:
        """Test validating invalid JSON."""
        tracker = AssetTracker()

        story_file = tmp_path / "invalid.story.json"
        story_file.write_text("not valid json {")

        result = tracker.process_file(story_file)

        assert not result.is_valid
        assert "json" in result.errors[0].lower()

    def test_validate_skill(self, tmp_path: Path) -> None:
        """Test validating a skill file."""
        tracker = AssetTracker()

        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text('''
---
name: test-skill
description: A test skill
---

This is the skill body.
''')

        result = tracker.process_file(skill_file)

        assert result.is_valid
        assert result.asset_type == "skill"

    def test_asset_registry(self, tmp_path: Path) -> None:
        """Test asset registry tracking."""
        tracker = AssetTracker()

        story_file = tmp_path / "test.story.json"
        story_file.write_text(json.dumps({
            "metadata": {"title": "Test"},
            "scenes": {"start": {"title": "Start", "choices": []}}
        }))

        tracker.process_file(story_file)

        registry = tracker.get_asset_registry()
        assert "story:test" in registry

    def test_change_log(self, tmp_path: Path) -> None:
        """Test change logging."""
        tracker = AssetTracker()

        story_file = tmp_path / "test.story.json"
        story_file.write_text(json.dumps({
            "metadata": {"title": "Test"},
            "scenes": {"start": {"title": "Start"}}
        }))

        tracker.process_file(story_file)

        assert tracker.change_count == 1
        changes = tracker.get_change_log()
        assert changes[0].asset_type == "story"


# =========================================================================
# PostFileSave Hook Tests
# =========================================================================

class TestPostFileSaveHook:
    """Tests for PostFileSave hook."""

    def test_should_process_story_file(self) -> None:
        """Test checking if story files should be processed."""
        hook = PostFileSaveHook()

        assert hook.should_process("stories/test.story.json")
        assert hook.should_process("scenes/scene_intro.json")

    def test_should_not_process_random_file(self) -> None:
        """Test that random files are not processed."""
        hook = PostFileSaveHook()

        assert not hook.should_process("random_file.txt")
        assert not hook.should_process("package.json")

    def test_generate_hook_json(self) -> None:
        """Test hook JSON generation."""
        hook = PostFileSaveHook()
        hook_json = hook.generate_hook_json()

        data = json.loads(hook_json)
        assert data["version"] == "v1"
        assert len(data["hooks"]) == 1
        assert data["hooks"][0]["trigger"] == "PostFileSave"


# =========================================================================
# Property-Based Tests
# =========================================================================

class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz_"))
    def test_scene_id_handling(self, scene_id: str) -> None:
        """Test handling of various scene IDs."""
        graph = ContextGraph()
        node = graph.add_scene(scene_id)

        assert node.id == scene_id
        assert graph.get_node(scene_id) == node

    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.integers(min_value=0, max_value=100),
        min_size=0, max_size=5
    ))
    def test_variable_handling(self, variables: dict) -> None:
        """Test handling various variable dictionaries."""
        graph = ContextGraph()

        for key, value in variables.items():
            graph.set_variable(key, value)

        for key, value in variables.items():
            assert graph.get_variable(key) == value

    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=10, alphabet="abc"),
            st.text(min_size=1, max_size=10, alphabet="xyz")
        ),
        min_size=0, max_size=10
    ))
    def test_transition_handling(self, transitions: list) -> None:
        """Test handling various transition combinations."""
        graph = ContextGraph()

        # Add all scenes
        scenes = set()
        for src, dst in transitions:
            scenes.add(src)
            scenes.add(dst)

        for scene in scenes:
            graph.add_scene(scene)

        # Add transitions
        for src, dst in transitions:
            graph.add_transition(src, dst)

        # Verify transitions exist
        for src, dst in transitions:
            edges = graph.get_edges_from(src)
            assert any(e.target_id == dst for e in edges if e.edge_type == EdgeType.LEADS_TO)


# =========================================================================
# Integration Tests
# =========================================================================

class TestIntegration:
    """Integration tests for the narrative system."""

    def test_full_story_playthrough(self) -> None:
        """Test a complete story playthrough."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)

        # Start the story
        scene = engine.start_story("start")
        assert scene.id == "start"

        # Make a choice
        result = engine.make_choice("enter_front")
        assert result["success"]

        # Check state
        state = engine.player_state
        assert "foyer" in state.visited_scenes

    def test_graph_integration_with_story(self) -> None:
        """Test context graph integration with narrative engine."""
        graph = ContextGraph()
        story = create_demo_story()

        # Build graph from story
        for scene_id, scene_data in story.get("scenes", {}).items():
            graph.add_scene(scene_id, {"title": scene_data.get("title")})

            for choice in scene_data.get("choices", []):
                graph.add_transition(scene_id, choice.get("consequence"))

        # Test reachability
        assert graph.can_reach("start", "foyer")
        assert graph.can_reach("start", "library")

    def test_story_serialization(self, tmp_path: Path) -> None:
        """Test saving and loading story state."""
        engine = NarrativeEngine()
        story = create_demo_story()
        engine.load_story(story)
        engine.start_story("start")

        # Make some choices
        engine.make_choice("enter_front")

        # Save state
        state = engine.get_story_state()

        # Write to file
        state_file = tmp_path / "story_state.json"
        state_file.write_text(json.dumps(state, indent=2))

        # Read back
        loaded_state = json.loads(state_file.read_text())

        assert loaded_state["turnCount"] == state["turnCount"]
