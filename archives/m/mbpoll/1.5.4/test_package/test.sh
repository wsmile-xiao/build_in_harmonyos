#!/data/service/hnp/bin/bash
# test_package/test.sh - smoke test for the mbpoll executable.
# Usage: test.sh <path-to-mbpoll-binary>
# Invoked by conanfile.py with the packaged binary's full path.
set -eo pipefail

MBPOLL="${1:?usage: test.sh <mbpoll binary>}"

echo "[test] $MBPOLL -V"
"$MBPOLL" -V 2>&1 | head -3
# mbpoll -V prints the bare version string (e.g. "1.5.4"); verify it ran and
# produced a version-like token.
"$MBPOLL" -V 2>&1 | grep -qE "[0-9]+\.[0-9]+"
echo "[ok] mbpoll executable runs and reports its version"
