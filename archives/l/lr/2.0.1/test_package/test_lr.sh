#!/bin/sh
# test_package/test_lr.sh — functional + OHOS-specific tests for the lr executable.
# Runs in the conanrun env (PATH includes the packaged bin/).
#
# Upstream lr 2.0.1 ships NO test suite: the Makefile has only
# all/clean/install targets, and the tarball contains no test files.
# These binary-level assertions supplement that gap.  Every expectation
# below was captured from real lr 2.0.1 behavior on this OHOS host
# before being written in (no guessed values).
#
# The OHOS-specific block at the end verifies the packaged ELF itself:
# ELF64/LSB/AArch64 ABI, PIE, musl interpreter, libc.so-only dependency
# and absence of RPATH/RUNPATH.
set -u

TMPD="$(pwd)"   # test build dir is writable; /tmp is read-only on OHOS
PASS=0
FAIL=0

ok()   { echo "ok - $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL - $1"; FAIL=$((FAIL+1)); }

check_eq() {   # name expected actual
    if [ "$3" = "$2" ]; then
        ok "$1"
    else
        fail "$1 (expected: [$2], got: [$3])"
    fi
}

echo "--- lr 2.0.1 test suite (upstream tests: 0, all assertions adapted) ---"

LR_BIN=$(command -v lr 2>/dev/null || true)
if [ -z "$LR_BIN" ]; then
    echo "FAIL - lr not found on PATH (conanrun env)"
    exit 1
fi
ok "lr binary found on PATH: $LR_BIN"

# --- fixture tree -------------------------------------------------------
FX="$TMPD/lr-fx"
rm -rf "$FX"
mkdir -p "$FX/a" "$FX/b/c"
printf 'hello\n' > "$FX/a/x.txt"     # 6 bytes
ln -s a/x.txt "$FX/y.link"

# --- test 1: -1 depth limit ----------------------------------------------
echo "[test] lr -1 (depth-1 only)"
check_eq "lr -1 lists exactly 4 entries" "4" "$(lr -1 "$FX" | wc -l | tr -d ' ')"
if lr -1 "$FX" | grep -qx "$FX"; then
    ok "lr -1 includes the root argument"
else
    fail "lr -1 should include the root argument"
fi
if lr -1 "$FX" | grep -qx "$FX/b/c"; then
    fail "lr -1 should not descend below one level"
else
    ok "lr -1 does not descend below one level"
fi

# --- test 2: -0 NUL-separated output --------------------------------------
echo "[test] lr -0 (NUL-separated output)"
check_eq "lr -0 lists 6 entries" "6" "$(lr -0 "$FX" | tr '\0' '\n' | wc -l | tr -d ' ')"
total=$(lr -0 "$FX" | wc -c | tr -d ' ')
nonnul=$(lr -0 "$FX" | tr -d '\0' | wc -c | tr -d ' ')
check_eq "lr -0 emits exactly 6 NUL bytes" "6" "$((total - nonnul))"

# --- test 3: -F type indicators -------------------------------------------
echo "[test] lr -F (file type indicators)"
if lr -F "$FX" | grep -qx "$FX/"; then
    ok "lr -F marks directories with /"
else
    fail "lr -F should mark directories with /"
fi
if lr -F "$FX" | grep -qx "$FX/b/c/"; then
    ok "lr -F marks nested directories with /"
else
    fail "lr -F should mark nested directories with /"
fi
if lr -F "$FX" | grep -qx "$FX/a/x.txt"; then
    ok "lr -F leaves regular files unadorned"
else
    fail "lr -F should not adorn regular files"
fi
if lr -F "$FX" | grep -qx "$FX/y.link@"; then
    ok "lr -F marks symlinks with @"
else
    fail "lr -F should mark symlinks with @"
fi

# --- test 4: -t 'type == d' filter ----------------------------------------
echo "[test] lr -t 'type == d' (directory filter)"
check_eq "type == d yields 4 directories" "4" "$(lr -t 'type == d' "$FX" | wc -l | tr -d ' ')"
if lr -t 'type == d' "$FX" | grep -qx "$FX/b/c"; then
    ok "type == d includes nested directory"
else
    fail "type == d should include nested directory"
fi
if lr -t 'type == d' "$FX" | grep -q 'x\.txt'; then
    fail "type == d must not match regular files"
else
    ok "type == d excludes regular files"
fi

# --- test 5: -t 'name ==' exact filter ------------------------------------
echo "[test] lr -t 'name == \"x.txt\"' (exact name filter)"
check_eq "name == x.txt finds the file" "$FX/a/x.txt" \
    "$(lr -t 'name == "x.txt"' "$FX")"

# --- test 6: -t 'name ~~' glob filter -------------------------------------
echo "[test] lr -t 'name ~~ \"*.txt\"' (glob name filter)"
check_eq "name ~~ *.txt finds the file" "$FX/a/x.txt" \
    "$(lr -t 'name ~~ "*.txt"' "$FX")"

# --- test 7: -e ERE filter -------------------------------------------------
echo "[test] lr -e 'x\\.txt' (POSIX ERE filter)"
check_eq "-e ERE matches basename" "$FX/a/x.txt" "$(lr -e 'x\.txt' "$FX")"

# --- test 8: -f custom format ----------------------------------------------
echo "[test] lr -f '%f %s\\n' (custom format: basename + size)"
check_eq "-f prints 'x.txt 6'" "x.txt 6" "$(lr -f '%f %s\n' "$FX/a/x.txt")"

# --- test 9: stdin mode (path argument '-') --------------------------------
echo "[test] lr - (read paths from stdin)"
check_eq "stdin mode echoes the path" "$FX/a/x.txt" \
    "$(printf '%s\n' "$FX/a/x.txt" | lr -)"

# --- test 10: -d don't enter directories -----------------------------------
echo "[test] lr -d (do not enter directories)"
check_eq "-d lists only the root itself" "$FX" "$(lr -d "$FX")"

# --- test 11: -l long format ------------------------------------------------
echo "[test] lr -l (ls -l style long output)"
out=$(lr -l "$FX/a/x.txt")
case "$out" in
    -*) ok "lr -l line starts with file type indicator" ;;
    *)  fail "lr -l line should start with '-'" ;;
esac
case "$out" in
    *x.txt*) ok "lr -l line shows the file name" ;;
    *)      fail "lr -l line should show the file name" ;;
esac

# --- test 12: invalid option -Z ---------------------------------------------
echo "[test] lr -Z (invalid option)"
lr -Z "$FX" >"$TMPD/z.out" 2>"$TMPD/z.err"
check_eq "invalid option exits 2" "2" "$?"
if grep -q 'unrecognized option' "$TMPD/z.err"; then
    ok "invalid option reports error on stderr"
else
    fail "invalid option should report error on stderr"
fi
if [ -s "$TMPD/z.out" ]; then
    fail "invalid option should print nothing to stdout"
else
    ok "invalid option prints nothing to stdout"
fi

# --- test 13: nonexistent path ----------------------------------------------
echo "[test] lr on nonexistent path"
lr "$FX/nope" >"$TMPD/n.out" 2>"$TMPD/n.err"
check_eq "nonexistent path exits 1" "1" "$?"
if grep -q 'cannot lstat' "$TMPD/n.err"; then
    ok "nonexistent path reports lstat error on stderr"
else
    fail "nonexistent path should report lstat error on stderr"
fi
if [ -s "$TMPD/n.out" ]; then
    fail "nonexistent path should print nothing to stdout"
else
    ok "nonexistent path prints nothing to stdout"
fi

# --- test 14: OHOS-specific ELF / ABI / dependency checks --------------------
echo "[test] OHOS-specific: AArch64 ELF/ABI/dependency checks on packaged binary"
set -- $(od -An -tx1 -N20 "$LR_BIN")
if [ "$1$2$3$4" = "7f454c46" ]; then
    ok "ELF magic (7f 45 4c 46)"
else
    fail "ELF magic mismatch: $1$2$3$4"
fi
check_eq "EI_CLASS = ELFCLASS64" "02" "$5"
check_eq "EI_DATA = little-endian" "01" "$6"
# NB: multi-digit positional params MUST be braced: mksh parses $17 as ${1}7.
check_eq "e_type = ET_DYN (PIE)" "0300" "${17}${18}"
check_eq "e_machine = EM_AARCH64 (183)" "b700" "${19}${20}"

n_needed=$(readelf -d "$LR_BIN" 2>/dev/null | grep -c "(NEEDED)" || true)
check_eq "exactly one NEEDED entry" "1" "$n_needed"
if readelf -d "$LR_BIN" 2>/dev/null | grep "(NEEDED)" | grep -q "\[libc\.so\]"; then
    ok "sole dependency is libc.so (musl libc)"
else
    fail "expected sole dependency [libc.so]"
fi

if readelf -p .interp "$LR_BIN" 2>/dev/null | grep -q "ld-musl-aarch64"; then
    ok "interpreter is OHOS musl aarch64 dynamic linker"
else
    fail "expected /lib/ld-musl-aarch64.so.1 interpreter"
fi

n_rpath=$(readelf -d "$LR_BIN" 2>/dev/null | grep -ciE "(RPATH|RUNPATH)" || true)
check_eq "no RPATH/RUNPATH entries" "0" "$n_rpath"

rm -rf "$FX" "$TMPD/z.out" "$TMPD/z.err" "$TMPD/n.out" "$TMPD/n.err"

echo "--- results: $PASS passed, $FAIL failed ---"
if [ "$FAIL" -ne 0 ]; then
    echo "LR_CLI_CHECKS_FAILED"
    exit 1
fi
echo "LR_OK: all $PASS checks passed"
