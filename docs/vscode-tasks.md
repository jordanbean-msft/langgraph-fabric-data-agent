---
title: VS Code Tasks
description: VS Code task reference for the LangGraph Fabric Data Agent sample
ms.date: 2026-04-01
---

# VS Code Tasks

This repository includes workspace tasks in [.vscode/tasks.json](../.vscode/tasks.json) so you can run the common development and M365 adapter flows directly from VS Code.

Open the task picker with **Terminal: Run Task** in VS Code, then choose one of these tasks:

| Task | Purpose |
| --- | --- |
| `sync-venv` | Install and sync the project and dev dependencies with `uv sync --all-packages --extra dev`. |
| `lint` | Run Ruff across the repository. |
| `test-core` | Run the `langgraph-fabric-core` test suite with verbose output. |
| `test-api` | Run the `langgraph-fabric-api` test suite with verbose output. |
| `test-console` | Run the `langgraph-fabric-console` test suite with verbose output. |
| `test-m365` | Run the `langgraph-fabric-m365` test suite with verbose output. |
| `test-all` | Run the full test suite across all packages. |
| `run-api` | Start the FastAPI surface on the configured port as a background task. |
| `run-console` | Start the interactive console surface. |
| `run-m365` | Start the M365 adapter as a background task in a new terminal panel. |
| `devtunnel-login` | Sign in to the Dev Tunnel CLI. |
| `devtunnel-create` | Create or reuse a named dev tunnel for the M365 adapter. |
| `devtunnel-show` | Show the current dev tunnel configuration. |
| `devtunnel-port-configure` | Recreate the HTTP port mapping for the M365 adapter port. |
| `devtunnel-host` | Start hosting the dev tunnel as a background task in a new panel. |
| `run-m365-and-devtunnel-host` | Start the M365 adapter and the dev tunnel host in parallel. |
| `run-m365-with-devtunnel` | Configure the tunnel port first, then start both the M365 adapter and the tunnel host. |
| `build-m365-app-package` | Build the Microsoft 365 app zip from the manifest and icon assets. |

## Task inputs

The dev tunnel tasks prompt for these inputs:

| Input | Default | Purpose |
| --- | --- | --- |
| `devTunnelId` | `langgraph-fabric-data-agent-m365` | Reusable dev tunnel name for the M365 adapter endpoint. |
| `m365Port` | `8000` | Local port exposed by the M365 adapter. |
| `devTunnelExpiration` | `7d` | Lifetime of the dev tunnel. Available choices are `4h`, `1d`, and `7d`. |

## Recommended task flows

For a normal first-time local setup in VS Code:

1. Run `sync-venv`.
2. Install the local Git hooks so commits run Ruff and pushes run the full test suite:

```bash
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

3. Run `lint` and `test-all` (or individual package tasks such as `test-core`, `test-api`).
4. Run `run-console`, `run-api`, or `run-m365` depending on the surface you want to test.

> [!IMPORTANT]
> The hook configuration lives in `.pre-commit-config.yaml`, but Git does not activate hooks automatically for a fresh clone. You must run `uv run pre-commit install --hook-type pre-commit --hook-type pre-push` once per local clone.

For Microsoft 365 testing with a dev tunnel:

1. Run `devtunnel-login` once on your machine.
2. Run `devtunnel-create` if you have not created the named tunnel yet.
3. Run `run-m365-with-devtunnel` to configure port `8000`, start the M365 adapter, and host the tunnel.
4. Copy the public dev tunnel URL into the Azure Bot endpoint with `az bot update` as described in the [Azure Bot Service guide](azure-bot-service.md).

> [!NOTE]
> `run-api`, `run-m365`, and `devtunnel-host` are background tasks. Stop them from the VS Code terminal panel when you are finished.
