#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ciwiki executable (didiwiki/3.0.5)
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# ciwiki normally keeps per-user state under $HOME/.ciwiki once it starts
# serving; use a throwaway HOME so the smoke test never touches real data.
SMOKE_HOME="$(mktemp -d "${TMPDIR:-${HOME}}/ciwiki-smoke.XXXXXX")"
trap 'rm -rf "$SMOKE_HOME"' EXIT
export HOME="$SMOKE_HOME"

echo "[test] ciwiki -v"
out="$(ciwiki -v)"
echo "$out"
echo "$out" | grep -q "CiWiki - version 3.0.5" && echo "✅ version OK" || {
    echo "❌ ciwiki -v output mismatch: $out"
    exit 1
}

echo "All tests passed!"
