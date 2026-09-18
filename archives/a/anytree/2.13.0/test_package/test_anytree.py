#!/usr/bin/env python3
"""Consumer-side check for the packaged anytree 2.13.0 (R34: real API).

Builds real trees, walks them, searches, resolves and renders — no print-only
stub, no import-only check.

Two upstream facts are pinned deliberately:

* ``anytree.__version__`` is the stale string ``"2.12.1"`` even though the
  distribution is **2.13.0** (measured: PKG-INFO says 2.13.0, the module says
  2.12.1). Asserting the real module value documents the mismatch instead of
  hiding it — see notes.md.
* ``anytree`` has **sub-packages** (``node`` / ``iterators`` / ``exporter`` /
  ``importer`` / ``util``); the test imports across them so a packaging mistake
  that dropped a sub-package would fail here.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import anytree
from anytree import (AnyNode, LevelOrderIter, Node, PreOrderIter, RenderTree,
                     Resolver, find, find_by_attr, findall, findall_by_attr)
from anytree.exporter import DictExporter
from anytree.importer import DictImporter
from anytree.iterators import PostOrderIter, ZigZagGroupIter

pkg_root = os.path.abspath(os.path.dirname(anytree.__file__))
assert os.path.basename(pkg_root) == "anytree", pkg_root

# Upstream reports the stale 2.12.1 in the module while the dist is 2.13.0.
assert anytree.__version__ == "2.12.1", anytree.__version__
assert len(anytree.__all__) == 33, len(anytree.__all__)
assert "Node" in anytree.__all__ and "RenderTree" in anytree.__all__

# --- build a real tree ------------------------------------------------------
#   root
#   ├── a
#   │   ├── a1
#   │   └── a2
#   └── b
root = Node("root")
a = Node("a", parent=root)
a1 = Node("a1", parent=a)
a2 = Node("a2", parent=a)
b = Node("b", parent=root)

assert root.is_root is True
assert root.parent is None
assert a.parent is root
assert [c.name for c in root.children] == ["a", "b"]
assert root.height == 2          # root -> a -> a1
assert root.depth == 0
assert a1.depth == 2

# --- path / descendants -----------------------------------------------------
assert root.path == (root,)
assert a1.path == (root, a, a1)
assert root.descendants[0] in (a, b)
assert len(root.descendants) == 4
assert {n.name for n in root.leaves} == {"a1", "a2", "b"}

# --- pre-order / level-order traversal order --------------------------------
assert [n.name for n in PreOrderIter(root)] == ["root", "a", "a1", "a2", "b"]
assert [n.name for n in LevelOrderIter(root)] == ["root", "a", "b", "a1", "a2"]
assert [n.name for n in PostOrderIter(root)] == ["a1", "a2", "a", "b", "root"]
# ZigZagGroupIter yields level groups, alternating direction
groups = [[n.name for n in g] for g in ZigZagGroupIter(root)]
assert groups[0] == ["root"], groups
assert sorted(groups[1]) == ["a", "b"], groups

# --- search helpers ---------------------------------------------------------
assert find(root, lambda n: n.name == "a2") is a2
assert [n.name for n in findall(root, lambda n: n.name.startswith("a"))] == ["a", "a1", "a2"]
assert find_by_attr(root, "a1") is a1
assert [n.name for n in findall_by_attr(root, "a")] == ["a"]

# --- Resolver ---------------------------------------------------------------
# Relative paths are resolved against the given node; an absolute path must
# start with the ROOT node's own name (measured: "/root/b" works while "/b"
# raises "unknown root node '/b'. root is '/root'."), and "root/b" is treated
# as a child lookup and raises ChildResolverError.
resolver = Resolver("name")
assert resolver.get(root, "a/a1") is a1
assert resolver.get(root, "b") is b
assert resolver.get(root, "/root/b") is b
for bad in ("/b", "root/b"):
    try:
        resolver.get(root, bad)
        raise SystemExit(f"FAIL: ResolverError expected for {bad!r}")
    except Exception as e:
        assert type(e).__name__ in ("ResolverError", "ChildResolverError"), \
            f"{bad!r} -> {type(e).__name__}: {e}"

# --- anynode (dict-backed) --------------------------------------------------
aroot = AnyNode(name="aroot")
AnyNode(name="achild", parent=aroot, value=7)
assert len(aroot.children) == 1
assert aroot.children[0].value == 7

# --- exporter / importer round-trip ----------------------------------------
exported = DictExporter().export(root)
assert exported["name"] == "root", exported
assert [c["name"] for c in exported["children"]] == ["a", "b"]
restored = DictImporter().import_(exported)
assert restored.name == "root"
assert [n.name for n in PreOrderIter(restored)] == ["root", "a", "a1", "a2", "b"]

# --- rendering --------------------------------------------------------------
lines = [f"{pre}{node.name}" for pre, _, node in RenderTree(root)]
assert lines[0] == "root", lines
assert "a1" in "\n".join(lines)
assert len(lines) == 5

# --- errors -----------------------------------------------------------------
try:
    Node("child", parent=None)  # no parent -> fine
    from anytree import LoopError
    bad = Node("x")
    Node("y", parent=bad)
    bad.parent = bad  # would create a loop
    raise SystemExit("FAIL: LoopError not raised when creating a loop")
except Exception as e:
    assert type(e).__name__ in ("LoopError", "TreeError"), f"{type(e).__name__}: {e}"

print(f"anytree {anytree.__version__} consumer API: PASS ({pkg_root})")
