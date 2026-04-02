# langgraph-fabric-m365

Hosted adapter for Teams and Copilot Chat via the M365 Agents SDK.
Bridges the LangGraph agent to the Bot Framework messaging pipeline.

## Modules

| Module | Purpose |
| --- | --- |
| `app.py` | Hosted M365 adapter bridge and route wiring |
| `oauth.py` | Hosted OAuth Adaptive Card flow, magic code handling, and hosted token resolution |
| `runtime.py` | Hosted runtime environment and SDK configuration builders |
| `main.py` | Entrypoint (`langgraph-fabric-m365` script) |

## Run

```bash
uv run langgraph-fabric-m365
```

Expose port `8000` via a dev tunnel and update the Azure Bot messaging endpoint to point at your tunnel URL.

## OAuth flow

The hosted adapter:

1. Sends an Adaptive Card sign-in prompt when the user is not authenticated.
2. Disables the sign-in action after flow initiation to prevent duplicate prompts.
3. Accepts OAuth magic codes pasted back into chat for token redemption.

State helpers in `oauth.py` wrap TurnState access for SDK compatibility.

See the [architecture guide](../../docs/architecture.md), [Teams and Copilot Chat guide](../../docs/m365-guide.md), and [Azure Bot Service guide](../../docs/azure-bot-service.md) for full details.

