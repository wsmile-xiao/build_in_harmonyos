#!/bin/sh
# quicktype 26.0.0 consumer tests.
#   $1 = packaged quicktype launcher
#   $2 = writable work directory
set -eu

qt=$1
workdir=$2

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

mkdir -p "$workdir"

# 1. The packaged launcher must carry the executable bit.
[ -x "$qt" ] || fail "launcher is not executable"
pass "launcher is executable"

# The launcher is a /bin/sh script; the Conan test context on OHOS refuses to
# exec script files directly, so fall back to `sh <launcher>` when needed.
if "$qt" --version >/dev/null 2>&1; then
    qt_run() { "$qt" "$@"; }
else
    qt_run() { sh "$qt" "$@"; }
fi

# 2. The CLI runs and reports the packaged version.
version=$(qt_run --version)
echo "$version"
echo "$version" | grep -q "26.0.0" || fail "version reports 26.0.0"
pass "version == 26.0.0"

# 3. --help enumerates the code-generation options.
help=$(qt_run --help 2>&1 || true)
echo "$help" | grep -q -- "--lang" || fail "--help lists --lang"
pass "--help lists --lang"

# 4. Real generation: JSON sample -> TypeScript model (exercises quicktype-core).
cat > "$workdir/sample.json" <<'JSON'
{"name":"Ada","age":37,"roles":["admin","dev"]}
JSON
qt_run --src-lang json --lang typescript --out "$workdir/TopLevel.ts" "$workdir/sample.json"
test -s "$workdir/TopLevel.ts" || fail "typescript output is empty"
grep -q "export interface" "$workdir/TopLevel.ts" || fail "typescript output has interface"
pass "generates TypeScript from JSON"

# 5. Real generation in a second target language (multi-language pipeline).
qt_run --src-lang json --lang go --out "$workdir/quicktype.go" "$workdir/sample.json"
test -s "$workdir/quicktype.go" || fail "go output is empty"
grep -q "package main" "$workdir/quicktype.go" || fail "go output has package main"
pass "generates Go from JSON"

# 6. OHOS-specific: the launcher must drive the OpenHarmony Node runtime in
#    JIT-less mode (native JIT cannot map executable memory on OHOS PC).
grep -q -- "--jitless" "$qt" || fail "OHOS launcher must invoke node --jitless"
pass "OHOS: launcher runs through node --jitless"

echo "quicktype consumer tests passed"
