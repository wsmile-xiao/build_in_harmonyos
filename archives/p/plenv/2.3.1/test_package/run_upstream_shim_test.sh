#!/usr/bin/env bash
# test_package/run_upstream_shim_test.sh — offline mirror of upstream test/shim.t.
# Usage: bash run_upstream_shim_test.sh <plenv-bin> <work-dir>
# (<work-dir>-only single-arg form kept as fallback for manual runs.)
# Takes the packaged `plenv` binary explicitly (conanrun PATH alone proved
# unreliable on the true machine: `plenv: inaccessible or not found`) with an
# isolated PLENV_ROOT. A stub perl that prints the live $PLENV_DIR stands in for a
# real perl, and PLENV_VERSION=dummy selects it, so no network / prove /
# real perl is needed. Fails non-zero on any mismatch.
set -eu
set -o pipefail 2>/dev/null || true
# HMBS true-machine compat: start from a getcwd-safe cwd (HNP bash fails on
# HMFS/HMDFS) and prefer injected SHELL, falling back to PATH bash only when
# SHELL cannot run bashisms (shims REQUIRE bash: [[ =~ ]]). Assertions unchanged.
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

if [ $# -ge 2 ]; then
  PLENV_BIN="$1"
  WORK="$2"
else
  WORK="$1"
  PLENV_BIN="${PLENV_BIN:-plenv}"
fi
ROOT="$WORK/plenv-root-upstream"

rm -rf "$ROOT"
mkdir -p "$ROOT/versions/dummy/bin"

# Stub perl: prints the LIVE $PLENV_DIR (no baked-in value, so a broken
# shim that drops the environment is caught instead of silently passing).
cat > "$ROOT/versions/dummy/bin/perl" <<'EOF'
#!/usr/bin/env bash
printf "%s\n" "$PLENV_DIR"
EOF
chmod +x "$ROOT/versions/dummy/bin/perl"

export PLENV_ROOT="$ROOT"
# Packaged plenv must be on PATH: generated shims re-exec via
# `command -v plenv` at runtime, so prepend the binary's dir when known.
case "$PLENV_BIN" in
  */*) PATH="$(dirname "$PLENV_BIN"):$PATH"; export PATH ;;
esac
case "$PLENV_BIN" in
  */*) "$BASHRUN" "$PLENV_BIN" rehash ;;
  *) plenv rehash ;;
esac
test -s "$ROOT/shims/perl" || { echo "shim missing or empty" >&2; exit 1; }

OUT="$(PLENV_ROOT="$ROOT" PLENV_VERSION="dummy" PLENV_DIR="$ROOT" "$BASHRUN" "$ROOT/shims/perl" -E 1)"
test "$OUT" = "$ROOT" || { echo "shim env mismatch: [$OUT] != [$ROOT]" >&2; exit 1; }
test -n "$OUT" || { echo "shim output unexpectedly empty" >&2; exit 1; }

echo "upstream shim mirror: 1/1 passed"
