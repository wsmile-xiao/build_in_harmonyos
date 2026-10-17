#!/bin/sh
# test_package/test.sh — consumer smoke test for integrit 4.1
#
# Verifies the INSTALLED binary (from this package, via conanrun PATH):
#   1. version fingerprint reported by the binary itself
#   2. help/usage entry point
#   3. first update (exit 0, known db produced)
#   4. unchanged check (exit 0)
#   5. modified-file check (exit 1 = INTEGRIT_EXIT_CHANGES)
#   6. report line acknowledgement ("changed: ")
#   7. missing-config failure (exit 2 = INTEGRIT_EXIT_FAILURE)
#
# Assertion 7 deliberately uses a *missing config file* to exercise exit code 2:
# it does not depend on filesystem permission bits, so it stays meaningful on
# HMDFS where `chmod 000` is rewritten to `rw-rw----` (see notes.md #31).
#
# POSIX sh only (no bash, no GNU-only extensions; /bin/sh is toybox on OHOS).
set -u

fail=0
assert_eq() { # desc expected actual
    if [ "$2" = "$3" ]; then
        echo "[ok]   $1 (rc=$3)"
    else
        echo "[FAIL] $1 (expected rc=$2, got rc=$3)"
        fail=1
    fi
}
assert_has() { # desc needle haystack
    case "$3" in
        *"$2"*) echo "[ok]   $1" ;;
        *)      echo "[FAIL] $1 — pattern [$2] not found in: $3"; fail=1 ;;
    esac
}
assert_file() { # desc path
    if [ -f "$2" ] && [ -s "$2" ]; then
        echo "[ok]   $1 ($2)"
    else
        echo "[FAIL] $1 — missing or empty: $2"
        fail=1
    fi
}

# ── 1. version fingerprint ──────────────────────────────────────────────
ver=$(integrit -V 2>&1)
assert_has "version fingerprint from installed binary" "integrit version 4.1" "$ver"

# ── 2. help entry point ─────────────────────────────────────────────────
help=$(integrit -h 2>&1); help_rc=$?
assert_eq "help exit status" 0 "$help_rc"
assert_has "usage names the -C conffile option" "-C" "$help"

# ── build a small file tree (self-contained; no root/net/TTY) ───────────
root=./tp_tree
rm -rf "$root"
mkdir -p "$root/data/one" "$root/data/two" || exit 1
echo "alpha content" > "$root/data/one/a"
echo "beta content"  > "$root/data/two/b"

# The databases live inside `root`, so without exclusions integrit would see
# its own just-written db as an unknown file and never report "no changes"
# (upstream `test/make-config -i` adds exactly these exclusions for the same
# reason; upstream assertion #24 only passes after it runs with -i).
cat > "$root/tp.conf" <<EOF
root = $root
known = $root/known.cdb
current = $root/curr.cdb
! $root/known.cdb
! $root/curr.cdb
EOF

# ── 3. first update: exit 0 and a non-empty known db is produced ────────
integrit -C "$root/tp.conf" -u >/dev/null 2>&1; upd_rc=$?
assert_eq "first update exit status (no change yet)" 0 "$upd_rc"
assert_file "current-state database created" "$root/curr.cdb"
mv "$root/curr.cdb" "$root/known.cdb"

# ── 4. unchanged check: exit 0 ──────────────────────────────────────────
integrit -C "$root/tp.conf" -c >/dev/null 2>&1; same_rc=$?
assert_eq "check with no changes" 0 "$same_rc"

# ── 5+6. modified file: exit 1 and report acknowledges it ───────────────
echo "modified by consumer test" > "$root/data/one/a"
out=$(integrit -C "$root/tp.conf" -c 2>&1); chg_rc=$?
assert_eq "check after modification reports changes" 1 "$chg_rc"
assert_has "report acknowledges the changed file" "changed:" "$out"

# ── 7. missing config: exit 2 (INTEGRIT_EXIT_FAILURE) ───────────────────
integrit -C "$root/does-not-exist.conf" -c >/dev/null 2>&1; err_rc=$?
assert_eq "missing config reports failure" 2 "$err_rc"

# ── summary ─────────────────────────────────────────────────────────────
rm -rf "$root"
if [ "$fail" -eq 0 ]; then
    echo "test_package: ALL 9 CONSUMER ASSERTIONS PASSED"
    exit 0
fi
echo "test_package: CONSUMER ASSERTIONS FAILED"
exit 1
