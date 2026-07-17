#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the showkey binary.
#
# showkey is an interactive TTY tool with no --version/--help flags and no
# library API. With no tty on stdin it deterministically prints
# "stdin is not a tty" and exits 1. Asserting that behavior proves the
# installed binary is the genuine showkey and actually runs.
set -euo pipefail

bin="${1:-showkey}"

# Run with /dev/null as stdin (not a tty); capture combined output and exit code.
out=$("$bin" </dev/null 2>&1) && rc=0 || rc=$?
echo "[test] showkey ran, exit code with non-tty stdin: $rc"
echo "[test] output: $out"

# The deterministic non-tty diagnostic must be present.
echo "$out" | grep -q "stdin is not a tty" || {
    echo "[fail] expected 'stdin is not a tty' diagnostic, got: $out" >&2
    exit 1
}

echo "[ok] showkey binary verified"
