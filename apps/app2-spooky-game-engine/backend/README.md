# Gothic Narrative Engine - Backend

FastAPI backend for the Spooky Gothic Narrative Engine.

## Running

```bash
pip install -e .
uvicorn server:app --reload
```

## API Endpoints

- `GET /` - API info
- `GET /story/start` - Begin a new story
- `POST /story/choose` - Make a choice and progress
- `GET /story/scene/{scene_id}` - Get a specific scene
- `GET /health` - Health check

## Integration with skillforge-core

Narrative skills are compiled using skillforge-core and validated
with property-based testing to ensure story consistency.
