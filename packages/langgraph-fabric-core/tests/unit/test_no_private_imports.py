"""Prevent private cross-module imports in source packages."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_GLOB = "packages/*/src/**/*.py"


def _is_internal_import(node: ast.ImportFrom) -> bool:
    if node.level > 0:
        return True
    return bool(node.module and node.module.startswith("langgraph_fabric_"))


def test_source_modules_do_not_import_private_members() -> None:
    violations: list[str] = []

    for file_path in sorted(REPO_ROOT.glob(SOURCE_GLOB)):
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not _is_internal_import(node):
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    rel_path = file_path.relative_to(REPO_ROOT)
                    violations.append(
                        f"{rel_path}:{node.lineno} imports private symbol '{alias.name}'"
                    )

    assert not violations, "\n".join(violations)
