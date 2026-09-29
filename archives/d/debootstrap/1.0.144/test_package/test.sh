#!/bin/sh
# debootstrap consumer test — asserts on the REAL packaged artifacts.
#
# R34/PF3: every assertion below reads the installed package, not a fixture.
# Notably the packaged main script is executed *directly* (relying on its own
# shebang) rather than via `sh <script>`: invoking it through `sh` hides a
# CRLF shebang, which is exactly the defect that shipped before. On Linux a
# CRLF build dies with "/bin/sh^M: bad interpreter" (rc=126).
set -eu

BIN_DIR="$1"
SHARE_DIR="$2"

# Normalize Windows-style "C:\..." paths to POSIX when running under
# git-bash (local Windows verification). No-op on Linux CI workers.
case "$BIN_DIR" in
  [A-Za-z]:*)
    if command -v cygpath >/dev/null 2>&1; then
      BIN_DIR=$(cygpath -u "$BIN_DIR")
      SHARE_DIR=$(cygpath -u "$SHARE_DIR")
    fi
    ;;
esac

MAIN="$BIN_DIR/debootstrap"

# The main script sources "$DEBOOTSTRAP_DIR/functions" at line 21, before it
# parses any argument, so the data dir must be exported before *any* invocation.
export DEBOOTSTRAP_DIR="$SHARE_DIR"

# ---- assertion 1: the packaged main script exists -------------------------
if [ ! -f "$MAIN" ]; then
    echo "[debootstrap test] FAIL: missing $MAIN"
    exit 1
fi

# ---- assertion 2: no CR anywhere in the packaged script -------------------
# A CR makes the shebang "/bin/sh\r" and the script unexecutable.
if LC_ALL=C grep -q "$(printf '\r')" "$MAIN"; then
    echo "[debootstrap test] FAIL: $MAIN contains CR (CRLF) -- shebang would be /bin/sh^M"
    exit 1
fi

# ---- assertion 3: shebang is intact and directly executable ----------------
if [ "$(head -n 1 "$MAIN")" != "#!/bin/sh" ]; then
    echo "[debootstrap test] FAIL: unexpected shebang: $(head -n 1 "$MAIN")"
    exit 1
fi
chmod +x "$MAIN" 2>/dev/null || true
echo "[debootstrap test] direct exec (uses packaged shebang, not 'sh <script>')"
out="$("$MAIN" --version 2>&1)" || {
    echo "[debootstrap test] FAIL: direct exec of $MAIN failed: $out"
    exit 1
}
echo "$out"
echo "$out" | grep -q "debootstrap 1.0.144"

# ---- assertion 4/5: data file layout (functions + non-empty scripts/) -----
if [ ! -f "$SHARE_DIR/functions" ]; then
    echo "[debootstrap test] FAIL: missing $SHARE_DIR/functions"
    exit 1
fi
if [ ! -d "$SHARE_DIR/scripts" ]; then
    echo "[debootstrap test] FAIL: missing $SHARE_DIR/scripts/"
    exit 1
fi
if [ -z "$(ls -A "$SHARE_DIR/scripts" 2>/dev/null || true)" ]; then
    echo "[debootstrap test] FAIL: $SHARE_DIR/scripts/ is empty"
    exit 1
fi

# ---- assertion 6: --help resolves the suite scripts via DEBOOTSTRAP_DIR ---
# Proves the data dir is really wired, not just present on disk: pointing
# DEBOOTSTRAP_DIR at a directory without functions/ must make it fail (rc=2).
if ! "$MAIN" --help >/dev/null 2>&1; then
    echo "[debootstrap test] FAIL: $MAIN --help failed with DEBOOTSTRAP_DIR=$SHARE_DIR"
    exit 1
fi

EMPTY_DIR="$(mktemp -d)"
trap 'rm -rf "$EMPTY_DIR"' EXIT
if (DEBOOTSTRAP_DIR="$EMPTY_DIR" "$MAIN" --help) >/dev/null 2>&1; then
    echo "[debootstrap test] FAIL: --help succeeded with an empty DEBOOTSTRAP_DIR"
    echo "[debootstrap test]        (data dir is not actually being used)"
    exit 1
fi

echo "[debootstrap test] PASS"
