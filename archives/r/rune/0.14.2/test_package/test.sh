#!/usr/bin/env zsh
# test_package/test.sh — 验证 Rune CLI 的参数解析、语法检查与脚本执行。
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-rune>" >&2
    exit 2
fi

rune_bin="$1"
tmpdir="$(mktemp -d 2>/dev/null || printf '%s/rune-test-%s' "${TMPDIR:?}" "$$")"
trap 'rm -rf "$tmpdir"' EXIT
mkdir -p "$tmpdir"

version_output="$("$rune_bin" --version 2>&1)"
printf '%s\n' "$version_output" | grep -F "The Rune Language Interpreter" >/dev/null

help_output="$("$rune_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Usage:" >/dev/null

cat > "$tmpdir/smoke.rn" <<'RUNE'
pub fn main() {
    let values = [1, 2, 3];
    values.iter().sum::<i64>()
}
RUNE
"$rune_bin" check "$tmpdir/smoke.rn" >/dev/null
"$rune_bin" run "$tmpdir/smoke.rn" >/dev/null

cat > "$tmpdir/invalid.rn" <<'RUNE'
pub fn main( {
RUNE
if "$rune_bin" check "$tmpdir/invalid.rn" >/dev/null 2>&1; then
    echo "invalid Rune source was unexpectedly accepted" >&2
    exit 1
fi

printf '        [ok] Rune version, help, syntax check, and script execution tests passed.\n'
