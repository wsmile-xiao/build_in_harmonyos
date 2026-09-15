#!/usr/bin/env bash
# test_package/test.sh — consumer smoke test for the packaged plenv binary.
# Usage: bash test.sh <plenv-bin> <expected-root>
# Runs 6 checks against an isolated PLENV_ROOT; nothing is written to $HOME.
set -eu
set -o pipefail 2>/dev/null || true
# HMBS true-machine compat: HNP bash cannot getcwd on HMFS/HMDFS dirs, which
# breaks plenv (shebang env bash) and its `cd "$OLDPWD"` roundtrips. Probe a
# getcwd-safe startup dir (/tmp first, TMPDIR last); all writes stay on the
# isolated root. The 6 consumer assertions below are unchanged.
SH="${CONFIG_SHELL:-${SHELL:-/bin/sh}}"
if "$SH" -c 'shopt -s nullglob' 2>/dev/null; then BASHRUN="$SH"; else BASHRUN="bash"; fi
STARTDIR=""
for d in "/tmp" "/" "${HOME:-}" "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}"; do
  if [ -n "$d" ] && [ -d "$d" ] && cd "$d" 2>/dev/null; then
    err=$("$BASHRUN" -c 'pwd' 2>&1 || true)
    case "$err" in *shell-init*|*cannot*access*parent*) continue;; *) STARTDIR="$d"; break;; esac
  fi
done
if [ -n "$STARTDIR" ]; then cd "$STARTDIR" 2>/dev/null || true; else cd /tmp 2>/dev/null || true; fi

PLENV_BIN="$1"
EXPECTED_ROOT="$2"

export PLENV_ROOT="$EXPECTED_ROOT"
export PATH="$(dirname "$PLENV_BIN"):$PATH"
rm -rf "$EXPECTED_ROOT"
mkdir -p "$EXPECTED_ROOT"

# 1. --version reports 2.3.1 (and is non-empty)
version_output="$("$PLENV_BIN" --version)"
test -n "$version_output"
case "$version_output" in
  *"2.3.1"*) ;;
  *) echo "unexpected version output: $version_output" >&2; exit 1 ;;
esac
echo "PASS 1/6: --version reports 2.3.1"

# 2. root returns the isolated root
root_output="$("$PLENV_BIN" root)"
test "$root_output" = "$EXPECTED_ROOT"
echo "PASS 2/6: root returns isolated PLENV_ROOT"

# 3. commands lists the core subcommands (and is non-empty)
commands_output="$("$PLENV_BIN" commands)"
test -n "$commands_output"
echo "$commands_output" | grep -E '(^|[[:space:]])versions($|[[:space:]])' >/dev/null
echo "$commands_output" | grep -E '(^|[[:space:]])rehash($|[[:space:]])' >/dev/null
echo "$commands_output" | grep -E '(^|[[:space:]])global($|[[:space:]])' >/dev/null
echo "$commands_output" | grep -E '(^|[[:space:]])local($|[[:space:]])' >/dev/null
echo "PASS 3/6: commands lists versions/rehash/global/local"

# 4. init emits shell integration code mentioning shims
init_output="$("$PLENV_BIN" init -)"
test -n "$init_output"
echo "$init_output" | grep -F "shims" >/dev/null
echo "PASS 4/6: init emits shims integration code"

# 5. rehash succeeds and prepares the shims directory
"$PLENV_BIN" rehash
test -d "$EXPECTED_ROOT/shims"
echo "PASS 5/6: rehash prepares shims directory"

# 6. global/local roundtrip writes and reads back under the isolated root
"$PLENV_BIN" global system
test -f "$EXPECTED_ROOT/version"
test "$(cat "$EXPECTED_ROOT/version")" = "system"
version_line="$("$PLENV_BIN" version)"
case "$version_line" in
  *"system"*) ;;
  *) echo "unexpected version line: $version_line" >&2; exit 1 ;;
esac
echo "PASS 6/6: global system roundtrip under isolated root"

echo "consumer test: 6/6 passed"
