# langgraph-fabric-api

FastAPI streaming endpoint for the LangGraph Fabric Data Agent sample.

## Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | `GET` | Liveness check |
| `/chat/stream` | `POST` | Stream agent responses as Server-Sent Events |

## Modules

| Module | Purpose |
| --- | --- |
| `app.py` | FastAPI application with `/health` and `/chat/stream` |
| `main.py` | Entrypoint (`langgraph-fabric-api` script) |

## Run

```bash
uv run langgraph-fabric-api
```

> [!NOTE]
> Endpoints are intentionally unauthenticated in this sample. Fabric tool calls always require user authentication.

See the [API guide](../../docs/api-guide.md) for detailed authentication setup and streaming client examples.
See the [architecture guide](../../docs/architecture.md) for full package details.

