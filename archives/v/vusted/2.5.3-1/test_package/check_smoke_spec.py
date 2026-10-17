#!/usr/bin/env python3
"""Static guard for the Vusted smoke spec used by test_package."""

import sys
from pathlib import Path


if len(sys.argv) != 2:
    raise SystemExit("usage: check_smoke_spec.py <smoke_spec.lua>")

spec = Path(sys.argv[1])
if not spec.is_file():
    raise SystemExit(f"smoke spec not found: {spec}")

text = spec.read_text(encoding="utf-8")
required = [
    'describe("vusted smoke"',
    'it("runs inside Neovim"',
    'it("exposes lfs.dir entry types"',
    'it("returns nil and an error for missing lfs.dir paths"',
    'vim.fn.has("nvim")',
    'require("vusted.helper")',
    'require("lfs")',
    "lfs.dir(root)",
    "pcall(lfs.dir, missing)",
    "assert.is.equal(nil, iterator)",
    "entry_type",
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit("missing Vusted smoke spec token(s): " + ", ".join(missing))

print("vusted smoke spec is present")
