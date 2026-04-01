---
title: VS Code Tasks
description: VS Code task reference for the LangGraph Fabric Data Agent sample
ms.date: 2026-04-01
---

# VS Code Tasks

This repository includes workspace tasks in [.vscode/tasks.json](../.vscode/tasks.json) so you can run the common development and hosted-adapter flows directly from VS Code.

Open the task picker with **Terminal: Run Task** in VS Code, then choose one of these tasks:

| Task | Purpose |
| --- | --- |
| `sync-venv` | Install and sync the project and dev dependencies with `uv sync --extra dev`. |
| `lint` | Run Ruff across the repository. |
| `test-unit` | Run the unit test suite with verbose output. |
| `test-integration` | Run the integration test suite with verbose output. |
| `test-all` | Run the full test suite. |
| `run-api` | Start the FastAPI surface on the configured port as a background task. |
| `run-console` | Start the interactive console surface. |
| `run-hosted` | Start the hosted M365 adapter as a background task in a new terminal panel. |
| `devtunnel-login` | Sign in to the Dev Tunnel CLI. |
| `devtunnel-create` | Create or reuse a named dev tunnel for the hosted adapter. |
| `devtunnel-show` | Show the current dev tunnel configuration. |
| `devtunnel-port-configure` | Recreate the HTTP port mapping for the hosted adapter port. |
| `devtunnel-host` | Start hosting the dev tunnel as a background task in a new panel. |
| `run-hosted-and-devtunnel-host` | Start the hosted adapter and the dev tunnel host in parallel. |
| `run-hosted-with-devtunnel` | Configure the tunnel port first, then start both the hosted adapter and the tunnel host. |
| `build-m365-app-package` | Build the Microsoft 365 app zip from the manifest and icon assets. |

## Task inputs

The dev tunnel tasks prompt for these inputs:

| Input | Default | Purpose |
| --- | --- | --- |
| `devTunnelId` | `langgraph-fabric-data-agent-m365` | Reusable dev tunnel name for the hosted endpoint. |
| `hostedPort` | `8000` | Local port exposed by the hosted adapter. |
| `devTunnelExpiration` | `7d` | Lifetime of the dev tunnel. Available choices are `4h`, `1d`, and `7d`. |

## Recommended task flows

For a normal first-time local setup in VS Code:

1. Run `sync-venv`.
2. Run `lint` and `test-unit`.
3. Run `run-console`, `run-api`, or `run-hosted` depending on the surface you want to test.

For hosted Microsoft 365 testing with a dev tunnel:

1. Run `devtunnel-login` once on your machine.
2. Run `devtunnel-create` if you have not created the named tunnel yet.
3. Run `run-hosted-with-devtunnel` to configure port `8000`, start the hosted adapter, and host the tunnel.
4. Copy the public dev tunnel URL into the Azure Bot endpoint with `az bot update` as described in the [Azure Bot Service guide](azure-bot-service.md).

> [!NOTE]
> `run-api`, `run-hosted`, and `devtunnel-host` are background tasks. Stop them from the VS Code terminal panel when you are finished.
