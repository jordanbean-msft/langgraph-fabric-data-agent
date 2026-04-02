---
description: Python coding standards for this repository
applyTo: "packages/**/*.py"
---

## Python Standards

* Use Python 3.12-compatible syntax and typing.
* Keep imports at file top, grouped and sorted.
* Avoid broad except blocks unless translating errors with clear context.
* Prefer explicit type hints on public functions and class methods.
* Keep functions small and composable.
* Use dependency injection for external services.

## Runtime behavior

* Route all environment reads through the package-specific settings model (e.g., `ApiSettings`, `ConsoleSettings`, `M365Settings`).
* Emit logs with stable structured context.
* Favor async interfaces for network-bound operations.
* For this sample, avoid persistence or background schedulers.
