#!/usr/bin/env python3
"""Detect whether a Conan recipe declares non-empty binary directories."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _contains_cpp_info(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Attribute) and item.attr == "cpp_info"
        for item in ast.walk(node)
    )


def _is_bindirs_target(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == "bindirs" and _contains_cpp_info(node.value)
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_is_bindirs_target(item) for item in node.elts)
    return False


def _is_statically_empty(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return not node.elts
    if isinstance(node, ast.Dict):
        return not node.keys
    return False


def source_declares_nonempty_bindirs(source: str) -> bool:
    """Return true for non-empty or dynamic cpp_info.bindirs declarations."""
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(_is_bindirs_target(target) for target in node.targets):
                if not _is_statically_empty(node.value):
                    return True
        elif isinstance(node, ast.AnnAssign):
            if _is_bindirs_target(node.target):
                if node.value is None or not _is_statically_empty(node.value):
                    return True
        elif isinstance(node, ast.AugAssign):
            if _is_bindirs_target(node.target):
                if not _is_statically_empty(node.value):
                    return True
        elif isinstance(node, ast.Call):
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and _is_bindirs_target(function.value)
                and function.attr in {"append", "extend", "insert"}
            ):
                if (
                    function.attr == "extend"
                    and node.args
                    and _is_statically_empty(node.args[0])
                ):
                    continue
                return True
            if (
                isinstance(function, ast.Name)
                and function.id == "setattr"
                and len(node.args) >= 3
                and _contains_cpp_info(node.args[0])
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "bindirs"
                and not _is_statically_empty(node.args[2])
            ):
                return True

    return False


def recipe_declares_nonempty_bindirs(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
        return source_declares_nonempty_bindirs(source)
    except (OSError, SyntaxError, UnicodeError):
        # L0a reports malformed recipes; L0k remains conservative meanwhile.
        return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <conanfile.py>", file=sys.stderr)
        return 2
    print(int(recipe_declares_nonempty_bindirs(Path(argv[1]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
