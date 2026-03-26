# DripMotion Event Bridge

This folder contains a tiny FastAPI service plus a lightweight HTTP client that
lets any Python producer (face / hand detectors) stream interaction events to
the browser control panel.

## Components

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app exposing `POST /api/events` and a WebSocket endpoint `/ws`. Every HTTP event is broadcast to all WebSocket subscribers. |
| `event_client.py` | Zero-dependency helper that queues events and posts them to the server from a background thread. |

## AI voice planning

`server.py` now exposes `POST /api/ai/voice-plan` for converting a Chinese voice transcript
to a normalized motion plan (`RingA~D + action + durationMs`).

- With `DRIP_AI_API_KEY` configured, it calls an OpenAI-compatible Chat Completions endpoint.
- Without key, it falls back to a built-in rule planner so the pipeline still works offline.

Environment variables:

- `DRIP_AI_API_KEY`: API key for LLM planning (optional).
- `DRIP_AI_MODEL`: chat model name (default `gpt-4o-mini`).
- `DRIP_AI_BASE_URL`: chat completions endpoint (default `https://api.openai.com/v1/chat/completions`).
- `DRIP_AI_TIMEOUT_SEC`: HTTP timeout in seconds (default `10`).

## Quick start

```bash
pip install -r bridge/requirements.txt
uvicorn bridge.server:app --reload --port 5050
```

Then point the web UI (or any WebSocket client) to `ws://127.0.0.1:5050/ws` to
receive live face / hand updates.

## Environment toggles

- `DRIP_EVENT_ENDPOINT`: override the HTTP endpoint (defaults to
  `http://127.0.0.1:5050/api/events`).
- `DRIP_EVENT_ENABLED=0`: disables the client without changing any calling
  code (useful when developing offline).

## Integration pattern

1. Import `EventClient` and create a singleton per channel (e.g. `face`, `hand`).
2. Push events from your detection loop:
   ```python
   from bridge.event_client import EventClient

   face_client = EventClient(channel="face")
   face_client.publish("status", {"direction": "LOOK_LEFT"})
   ```
3. The web UI subscribes to `/ws`, updates its status cards, and optionally calls
   back into the control layer via `window.DripCommandHub`.

Need help wiring new sensors or commands into the bridge? Ping me and I will
extend the schema plus UI bindings.
