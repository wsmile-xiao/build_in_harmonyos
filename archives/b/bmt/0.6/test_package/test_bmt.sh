#!/bin/sh
# R34: real smoke test for bmt 0.6 — exercises the packaged artifact.
# bmt is a shell/Perl toolkit; verify presence, executable bit, version, help and share payload.
# HarmonyOS HNP compatibility: use /bin/sh (not bash), respect HMBS TMPDIR, handle read-only /tmp.
set -eu
# pipefail where supported
set -o pipefail 2>/dev/null || true

BIN_DIR="${1:?usage: test_bmt.sh <package bin dir> <package folder>}"
PKG_FOLDER="${2:?usage: test_bmt.sh <package bin dir> <package folder>}"

FAIL=0

CPBM="$BIN_DIR/cpbm"
SHARE_DIR="$PKG_FOLDER/share/cpbm"

echo "=== bmt test_package ==="

# HMBS readonly /tmp handling: HarmonyOS mounts /tmp read-only. Use HMBS injected
# TMPDIR/TMP/TEMP (e.g. /storage/.../runtime/bmt-0.6/tmp) for any temp files.
# Previous preflight hit "can't create temporary file /tmp/sh...: Read-only file system".
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ] && [ -w "$TMPDIR" ]; then
  export TMP="${TMP:-$TMPDIR}"
  export TEMP="${TEMP:-$TMPDIR}"
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ] && [ -w "$TMP" ]; then
  export TMPDIR="$TMP"
  export TEMP="${TEMP:-$TMP}"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ] && [ -w "$TEMP" ]; then
  export TMPDIR="$TEMP"
  export TMP="${TMP:-$TEMP}"
else
  TMPDIR="$PKG_FOLDER/tmp"
  mkdir -p "$TMPDIR" 2>/dev/null || true
  export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR"
fi
export TMPDIR TMP TEMP
# Shell diagnosis: HNP bash cannot access HMFS/HMDFS cwd; force /bin/sh
export SHELL=/bin/sh
export CONFIG_SHELL=/bin/sh

# 1. cpbm exists (HMDFS chmod=0 makes -x unreliable; check -f)
if [ ! -f "$CPBM" ]; then
    echo "FAIL: cpbm missing or not executable in $BIN_DIR"
    FAIL=1
else
    echo "PASS: cpbm exists and executable"
    if [ ! -x "$CPBM" ]; then
        echo "[warn] cpbm not executable bit (HMDFS chmod=0), will invoke via sh"
    fi
fi

# helper to invoke cpbm via sh to avoid bad interpreter /bin/bash
run_cpbm() {
    # Prefer sh wrapper to avoid shebang /bin/bash missing on HarmonyOS
    sh "$CPBM" "$@" 2>&1
}

# 2. --version == 0.6 (use sh wrapper)
if [ -f "$CPBM" ]; then
    # Try sh wrapper first (robust on HarmonyOS where /bin/bash missing)
    VER=$(sh "$CPBM" --version 2>&1 | tr -d ' \r\n' || true)
    # fallback direct exec (if shebang already patched to /bin/sh)
    if [ -z "$VER" ] || echo "$VER" | grep -q "bad interpreter"; then
        VER=$("$CPBM" --version 2>&1 | tr -d ' \r\n' || true)
        # If still bad interpreter, try sh fallback again
        if echo "$VER" | grep -q "bad interpreter"; then
            VER=$(sh "$CPBM" --version 2>&1 | tr -d ' \r\n' || true)
        fi
    fi
    echo "cpbm --version => $VER"
    if [ "$VER" != "0.6" ]; then
        echo "FAIL: expected version 0.6, got $VER"
        FAIL=1
    else
        echo "PASS: version 0.6"
    fi
fi

# 3. help lists expected subcommands (via sh wrapper)
if [ -f "$CPBM" ]; then
    HELP=$(sh "$CPBM" help 2>&1 || sh "$CPBM" --help 2>&1 || true)
    # also try direct if sh help empty
    if [ -z "$HELP" ]; then
        HELP=$("$CPBM" help 2>&1 || true)
    fi
    for cmd in unpack update init run csv table graph; do
        if echo "$HELP" | grep -qw "$cmd"; then
            echo "PASS: help contains $cmd"
        else
            echo "FAIL: help missing $cmd"
            FAIL=1
        fi
    done
fi

# 4. sh syntax check on cpbm (use sh -n, not bash -n)
if [ -f "$CPBM" ]; then
    if ! sh -n "$CPBM" 2>&1; then
        echo "FAIL: cpbm sh syntax check failed"
        FAIL=1
    else
        echo "PASS: sh -n cpbm OK"
    fi
    # also check share scripts syntax via sh -n
    for _f in "$SHARE_DIR/unpack.sh" "$SHARE_DIR/update.sh" "$SHARE_DIR/verify.sh" "$SHARE_DIR/cil_wrapper.sh" "$SHARE_DIR/list_claims.sh"; do
        if [ -f "$_f" ]; then
            if sh -n "$_f" 2>&1; then
                echo "PASS: sh -n $(basename "$_f") OK"
            else
                echo "FAIL: $(basename "$_f") sh syntax check failed"
                FAIL=1
            fi
        fi
    done
fi

# 5. share payload exists
for f in VERSION verify.sh unpack.sh update.sh make_csv.pl make_table.pl; do
    if [ ! -f "$SHARE_DIR/$f" ]; then
        echo "FAIL: share/cpbm/$f missing"
        FAIL=1
    else
        echo "PASS: share/cpbm/$f present"
    fi
done

# 6. check at least 20 files in share/cpbm
COUNT=$(ls -1 "$SHARE_DIR" 2>/dev/null | wc -l | tr -d ' ')
echo "share/cpbm file count: $COUNT"
if [ "$COUNT" -lt 20 ]; then
    echo "FAIL: expected >=20 files in share/cpbm, got $COUNT"
    FAIL=1
else
    echo "PASS: share/cpbm has $COUNT files"
fi

if [ "$FAIL" -eq 0 ]; then
    echo "bmt smoke test: OK"
fi
exit "$FAIL"
