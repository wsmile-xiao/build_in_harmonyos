#!/usr/bin/zsh
# test_package/src/test_cosign.sh
#
# L1/L2 smoke test for the cosign application package (shell wrapper).
#
# The test invokes the actual installed cosign binary via `cosign version`.
# This shell wrapper performs the same invocation so the CI L0c gate (which
# scans .c/.cpp/.cc/.cxx/.sh/.py) detects a test source file, and so a
# non-Go CI runner can still run the smoke test.
#
# Usage:
#   COSIGN_BIN=/path/to/cosign zsh test_cosign.sh
#   zsh test_cosign.sh          # looks up cosign on PATH
#
# Exit codes:
#   0 — cosign version printed a string containing the expected version
#   1 — cosign not found, version mismatch, or placeholder binary detected
#   2 — cosign version exited non-zero
set -euo pipefail

COSIGN_BIN="${COSIGN_BIN:-}"
if [ -z "$COSIGN_BIN" ]; then
    if command -v cosign >/dev/null 2>&1; then
        COSIGN_BIN="$(command -v cosign)"
    else
        echo "        [fail] cosign binary not found (set COSIGN_BIN or add cosign to PATH)" >&2
        exit 1
    fi
fi

EXPECTED_VERSION="3.1.1"
rc=0
out="$("$COSIGN_BIN" version 2>&1)" || rc=$?

if [ "$rc" -ne 0 ]; then
    echo "        [fail] cosign version exited with $rc" >&2
    echo "        [fail] output: $out" >&2
    exit 2
fi

case "$out" in
    *"[PLACEHOLDER]"*)
        # R9: conanfile.py builds a C placeholder when the Go toolchain is
        # unavailable; a placeholder must never pass as a genuine build.
        echo "        [fail] cosign version output contains placeholder marker (R9: 禁止伪造通过)" >&2
        echo "        [fail] output: $out" >&2
        exit 1
        ;;
esac

case "$out" in
    *"$EXPECTED_VERSION"*)
        echo "        [ok] cosign version output contains $EXPECTED_VERSION"
        exit 0
        ;;
    *)
        echo "        [fail] cosign version output does not contain $EXPECTED_VERSION" >&2
        echo "        [fail] output: $out" >&2
        exit 1
        ;;
esac
