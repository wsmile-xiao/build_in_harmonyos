#!/usr/bin/env bash
# Functional smoke test for the packaged bookloupe binary.
# Feeds a tiny e-text containing a known punctuation problem and asserts that
# bookloupe reports the expected diagnostic ("Missing space?") and exits 0.
# The runtime data file bookloupe.typ is installed next to the binary, so the
# tool runs with its full typography/user-typo configuration.
set -eu

BOOKLOUPE_BIN="${BOOKLOUPE_BIN:-bookloupe}"

sample="bookloupe-sample-$$.txt"
cleanup() { rm -f "$sample"; }
trap cleanup EXIT

cat > "$sample" <<'EOF'
"Look!John, over there!"
EOF

set +e
out="$("$BOOKLOUPE_BIN" "$sample" 2>&1)"
rc=$?
set -e

if [ "$rc" -ne 0 ]; then
    echo "bookloupe exited with $rc on the sample file:"
    echo "$out"
    exit 1
fi

case "$out" in
  *"Missing space?"*)
    echo "bookloupe smoke test passed (Missing space? detected)"
    ;;
  *)
    echo "Unexpected bookloupe output (expected 'Missing space?' diagnostic):"
    echo "$out"
    exit 1
    ;;
esac
