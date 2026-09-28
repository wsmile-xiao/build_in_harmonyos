#!/usr/bin/env bash
set -euo pipefail

bindir=${1:?expected Conan package bin directory}
tmpdir=$(mktemp -d "${TMPDIR:-.}/yodl-harmony-test.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

# This test is deliberately tied to the target platform. A passing result
# proves that the package was exercised on HarmonyOS PC, not just cross-built.
uname -a | grep -qi 'HarmonyOS'
[ "$(uname -m)" = "aarch64" ]

version_status=0
"$bindir/yodl" --version > "$tmpdir/version.txt" 2>&1 || version_status=$?
if [ "$version_status" -ne 0 ] && [ "$version_status" -ne 1 ]; then
    cat "$tmpdir/version.txt" >&2
    echo "unexpected yodl --version exit status: $version_status" >&2
    exit "$version_status"
fi
grep -F '4.05.01' "$tmpdir/version.txt"

cat > "$tmpdir/smoke.yo" <<'EOF'
HarmonyOS Yodl conversion smoke test.
EOF
"$bindir/yodl2txt" --output="$tmpdir/smoke.txt" "$tmpdir/smoke.yo"
grep -F 'HarmonyOS Yodl conversion smoke test.' "$tmpdir/smoke.txt"

cat > "$tmpdir/verbatim.txt" <<'EOF'
Yodl verbatim conversion smoke test.
EOF
"$bindir/yodlverbinsert" -a "$tmpdir/verbatim.txt" > "$tmpdir/verbatim.yo"
grep -F 'Yodl verbatim conversion smoke test.' "$tmpdir/verbatim.yo"

if "$bindir/yodl2txt" --output="$tmpdir/missing.txt" \
        "$tmpdir/does-not-exist.yo"; then
    echo "conversion unexpectedly accepted a missing input" >&2
    exit 1
fi

echo "PASS: HarmonyOS/aarch64 runtime, Yodl and verbatim conversion, and error handling"
