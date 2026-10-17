#!/usr/bin/env bash
# test_package smoke test — feed OCaml source to ocaml-syntax-shims preprocessor
set -euo pipefail

BIN="${1:?usage: $0 <path-to-ocaml-syntax-shims>}"
TEST_SRC="$(dirname "$0")/test_input.ml"

cat "$TEST_SRC" | "$BIN"
