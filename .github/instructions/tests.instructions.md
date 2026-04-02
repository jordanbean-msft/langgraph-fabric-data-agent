---
description: Test standards for this repository
applyTo: "packages/**/tests/**/*.py"
---

## Test Standards

* Cover happy paths and key failure paths.
* Mock external dependencies: MCP endpoints, Azure token acquisition, and M365 Agents SDK surface.
* Keep tests deterministic and independent.
* Use clear arrange-act-assert structure.
* Use async tests for async behavior.

## Expected scope

* Unit tests for config, auth, MCP client, tools, graph transitions, and API contract.
* Integration tests that run locally without cloud credentials by using fake services.
