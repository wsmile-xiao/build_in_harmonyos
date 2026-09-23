#!/usr/bin/env bash
# test_package/test.sh — smoke + functional test for the diffutils executables.
# Runs inside the conanrun environment (PATH includes the installed bin/).
set -eu

echo "[test] version checks"
for tool in diff diff3 sdiff cmp; do
    command -v "$tool" >/dev/null 2>&1 || { echo "❌ $tool not found on PATH"; exit 1; }
    "$tool" --version >/dev/null || { echo "❌ $tool --version failed"; exit 1; }
    echo "  ✅ $tool --version"
done

work=./_diffutils_smoke
rm -rf "$work"
mkdir -p "$work"

printf 'a\nb\nc\n' > "$work/a.txt"
printf 'a\nB\nc\n' > "$work/b.txt"

# diff must report the difference and exit non-zero
if diff "$work/a.txt" "$work/b.txt" > "$work/d.out"; then
    echo "❌ diff returned success for differing files"
    exit 1
fi
grep -q '^< b$' "$work/d.out" || { echo "❌ diff missing '< b' output"; cat "$work/d.out"; exit 1; }
grep -q '^> B$' "$work/d.out" || { echo "❌ diff missing '> B' output"; cat "$work/d.out"; exit 1; }
echo "  ✅ diff detected difference"

# diff must exit 0 for identical files
diff "$work/a.txt" "$work/a.txt" >/dev/null || { echo "❌ diff returned non-zero for identical files"; exit 1; }
echo "  ✅ diff identical files"

# cmp: identical => 0, different => 1
cmp -s "$work/a.txt" "$work/a.txt" || { echo "❌ cmp returned non-zero for identical files"; exit 1; }
if cmp -s "$work/a.txt" "$work/b.txt"; then
    echo "❌ cmp returned zero for differing files"
    exit 1
fi
echo "  ✅ cmp comparison"

# sdiff produces a side-by-side diff (non-empty)
sdiff "$work/a.txt" "$work/b.txt" > "$work/s.out" 2>/dev/null || true
[ -s "$work/s.out" ] || { echo "❌ sdiff produced no output"; exit 1; }
echo "  ✅ sdiff output"

rm -rf "$work"
echo "✅ diffutils functional smoke test passed"
