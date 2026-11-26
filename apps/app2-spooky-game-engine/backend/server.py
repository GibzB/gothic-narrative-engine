"""
FastAPI Backend for Gothic Narrative Engine.

Serves the interactive narrative API, handling story progression,
state management, and skill-compiled narrative validation.

Uses skillforge-core for narrative skill validation and the
GothicNarrativeEngine for story state management.

Task 4.1: Backend Server
Validates: Requirements 4.1, 4.2, 4.3
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gothic_narrative import (
    NarrativeEngine,
    ContextGraph,
    create_demo_story,
)


# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(
    title="Gothic Narrative Engine",
    description="Interactive branching horror stories powered by Kiro-SkillForge",
    version="0.1.0",
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize narrative engine and context graph
narrative_engine = NarrativeEngine(validate_transitions=True)
context_graph = ContextGraph()

# Load demo story
demo_story = create_demo_story()
narrative_engine.load_story(demo_story)

# Initialize context graph from story
for scene_id, scene_data in demo_story.get("scenes", {}).items():
    context_graph.add_scene(scene_id, {"title": scene_data.get("title", "")})
    for choice in scene_data.get("choices", []):
        context_graph.add_transition(scene_id, choice.get("consequence"))


# ============================================================================
# API Models
# ============================================================================

class StoryChoice(BaseModel):
    id: str
    text: str
    consequence: str | None = None
    is_available: bool = True
    hint: str = ""


class PlayerStateResponse(BaseModel):
    current_scene: str
    inventory: list[str] = []
    stats: dict[str, int] = {}
    flags: dict[str, bool] = {}
    choices_made: list[str] = []


class SceneResponse(BaseModel):
    id: str
    title: str
    description: str
    phase: str = "exploration"
    mood: str = "foreboding"
    atmosphere: dict[str, Any] = {}
    choices: list[StoryChoice] = []
    is_ending: bool = False
    ending_type: str | None = None
    player_state: PlayerStateResponse | None = None


class ChoiceRequest(BaseModel):
    choice_id: str
    current_scene: str


class StoryStateResponse(BaseModel):
    metadata: dict[str, Any]
    current_scene: str
    visited_scenes: list[str]
    turn_count: int
    is_complete: bool


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root() -> dict[str, str]:
    """API root."""
    return {
        "message": "Gothic Narrative Engine API",
        "version": "0.1.0",
        "docs": "/docs",
        "story": "/story/start",
    }


@app.get("/story/start", response_model=SceneResponse)
async def start_story() -> SceneResponse:
    """Begin a new story."""
    # Reset the narrative engine
    narrative_engine.start_story("start")
    context_graph.set_current_scene("start")

    scene = narrative_engine.current_scene
    if not scene:
        raise HTTPException(status_code=404, detail="Start scene not found")

    return _scene_to_response(scene)


@app.get("/story/scene/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str) -> SceneResponse:
    """Get a specific scene."""
    # Navigate to the scene if needed
    if narrative_engine.player_state.current_scene != scene_id:
        narrative_engine.player_state.current_scene = scene_id
        if scene_id not in narrative_engine.player_state.visited_scenes:
            narrative_engine.player_state.visited_scenes.append(scene_id)

    scene = narrative_engine._scenes.get(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return _scene_to_response(scene)


@app.post("/story/choose", response_model=SceneResponse)
async def make_choice(choice_id: str, current_scene: str = "start") -> SceneResponse:
    """Make a choice and progress the story."""
    # Ensure we're on the correct scene
    if narrative_engine.player_state.current_scene != current_scene:
        narrative_engine.player_state.current_scene = current_scene

    # Make the choice
    result = narrative_engine.make_choice(choice_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid choice"))

    # Update context graph
    new_scene_id = result.get("currentScene")
    if new_scene_id:
        context_graph.set_current_scene(new_scene_id)

    scene = narrative_engine.current_scene
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    response = _scene_to_response(scene)
    response.player_state = _player_state_to_response(narrative_engine.player_state)

    return response


@app.post("/story/choose/json", response_model=SceneResponse)
async def make_choice_json(request: ChoiceRequest) -> SceneResponse:
    """Make a choice with JSON body."""
    return await make_choice(request.choice_id, request.current_scene)


@app.get("/story/state", response_model=StoryStateResponse)
async def get_story_state() -> StoryStateResponse:
    """Get the current story state."""
    state = narrative_engine.get_story_state()

    return StoryStateResponse(
        metadata=state.get("metadata", {}),
        current_scene=state.get("state", {}).get("player", {}).get("currentScene", "start"),
        visited_scenes=state.get("state", {}).get("player", {}).get("visitedScenes", []),
        turn_count=state.get("turnCount", 0),
        is_complete=narrative_engine.is_story_complete(),
    )


@app.post("/story/event/{event_type}")
async def trigger_event(event_type: str) -> dict[str, Any]:
    """Trigger a procedural narrative event."""
    event = narrative_engine.generate_procedural_event(event_type)
    return event


@app.get("/story/ending")
async def get_ending() -> dict[str, Any]:
    """Get ending information if story is complete."""
    ending = narrative_engine.get_ending()
    if not ending:
        raise HTTPException(status_code=400, detail="Story is not complete")
    return ending


@app.post("/story/restart")
async def restart_story() -> SceneResponse:
    """Restart the story from the beginning."""
    return await start_story()


@app.get("/context/graph")
async def get_context_graph() -> dict[str, Any]:
    """Get the context graph structure."""
    return context_graph.to_dict()


@app.get("/context/path/{from_scene}/{to_scene}")
async def get_path(from_scene: str, to_scene: str) -> dict[str, Any]:
    """Find a path between two scenes."""
    path = context_graph.get_path(from_scene, to_scene)
    return {
        "from": from_scene,
        "to": to_scene,
        "path": path,
        "reachable": path is not None,
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "engine": "initialized",
        "scenes_loaded": len(narrative_engine._scenes),
    }


# ============================================================================
# Static File Serving (for production)
# ============================================================================

# Check if public directory exists
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/static", StaticFiles(directory=str(public_dir)), name="static")

    @app.get("/app", response_class=HTMLResponse)
    async def serve_app() -> HTMLResponse:
        """Serve the main application."""
        index_path = public_dir / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text())
        raise HTTPException(status_code=404, detail="App not found")


# ============================================================================
# Helper Functions
# ============================================================================

def _scene_to_response(scene: Any) -> SceneResponse:
    """Convert a StoryScene to SceneResponse."""
    choices = []
    for choice in scene.choices:
        choices.append(StoryChoice(
            id=choice.id,
            text=choice.text,
            consequence=choice.consequence_scene,
            is_available=choice.is_available,
            hint=choice.hint,
        ))

    return SceneResponse(
        id=scene.id,
        title=scene.title,
        description=scene.description,
        phase=scene.phase.value if hasattr(scene.phase, 'value') else scene.phase,
        mood=scene.mood.value if hasattr(scene.mood, 'value') else scene.mood,
        atmosphere=scene.atmosphere,
        choices=choices,
        is_ending=scene.is_ending,
        ending_type=scene.ending_type,
    )


def _player_state_to_response(state: Any) -> PlayerStateResponse:
    """Convert PlayerState to PlayerStateResponse."""
    return PlayerStateResponse(
        current_scene=state.current_scene,
        inventory=state.inventory,
        stats=state.stats,
        flags=state.flags,
        choices_made=state.choices_made,
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
