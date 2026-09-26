#!/bin/bash
# test_package/test.sh — consumer behaviour contract for the zpaq 7.15 package.
#
# R34: this script really executes the binary that the package installs and
# asserts its real behaviour (archive creation, journaling, revision rollback,
# deduplication accounting, error diagnostics) — it is not a print-only or
# pass-only stub.  It is the "installed package" counterpart of upstream's own
# `make check` target (Makefile:32-36 = add -> extract -to -> cmp).
#
# Usage: bash test.sh <path-to-installed-zpaq>
#   exit 0 = all checks passed, non-zero = at least one check failed.
#
# Requires bash: the safe-mode header below uses `pipefail`, and this platform's
# /system/bin/sh (mksh) cannot reliably spawn ELF binaries.  The interpreter is
# chosen by the caller (test_package/conanfile.py): $CONFIG_SHELL when it points
# at an existing file, otherwise the first of the known OHOS bash locations
# (/data/service/hnp/bin/bash, /bin/bash, /usr/bin/bash) that exists; if none is
# available the test fails with an explicit ConanException.  There is no PATH
# lookup.  The shebang above is therefore only for local debugging — the script
# is always invoked as `<resolved bash> test.sh <binary>`.
#
# Exit statuses of zpaq 7.15, measured on the packaged aarch64 binary:
#   usage / unknown option        -> 1
#   missing archive file          -> 2  (with "…: No such file or directory")
#   `add` with a missing input    -> 0  (diagnostic only, no non-zero status!)
#   successful add / extract / l  -> 0
# Because some error paths still return 0, the positive checks assert on the
# produced archive bytes rather than on $?, and every zpaq invocation below
# captures its status explicitly so that a failure is reported as a failed
# check instead of aborting the script mid-report.

set -euo pipefail

ZPAQ="${1:?usage: test.sh <path-to-zpaq>}"
# Existence only: on the OHOS/HMDFS storage of this project the executable bit
# is not reliable (access(X_OK) can report false for a runnable file), see
# R49.  Whether the binary really runs is asserted by T1 itself.
if [ ! -f "$ZPAQ" ]; then
    echo "[FAIL] packaged binary not found: $ZPAQ"
    exit 1
fi

WORK="${TMPDIR:-/tmp}/zpaq-7.15-test-$$"
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$WORK/src" || exit 1
cd "$WORK" || exit 1
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT HUP INT TERM

CHECKS=0
PASSED=0

ok() {
    CHECKS=$((CHECKS + 1))
    PASSED=$((PASSED + 1))
    echo "[PASS] $1"
}

no() {
    CHECKS=$((CHECKS + 1))
    echo "[FAIL] $1"
    shift
    for line in "$@"; do
        echo "  | $line"
    done
}

# ── payload ────────────────────────────────────────────────────────────────
# One binary member (the zpaq executable itself, ~2.2 MB — the same trick
# upstream's `make check` uses) plus one small text member that we revise to
# exercise the journal.
cp "$ZPAQ" src/zpaq.bin || exit 1
i=0
while [ "$i" -lt 10 ]; do
    printf 'zpaq 7.15 consumer test line %s\n' "$i"
    i=$((i + 1))
done > src/text.txt
cp src/text.txt text-v1.txt

# ── T1: the binary runs and reports the expected upstream version ──────────
OUT=$("$ZPAQ" 2>&1) || true
case "$OUT" in
    *"zpaq v7.15 journaling archiver"*)
        ok "T1 no-arg invocation prints the zpaq v7.15 banner and usage" ;;
    *)
        no "T1 banner missing from no-arg invocation" "$OUT" ;;
esac

# ── T2: upstream round trip (add -> extract -> byte compare) ───────────────
# `-to out1` is not pre-created on purpose: zpaq creates a missing output
# directory itself (measured), which is the behaviour upstream's own `make
# check` relies on.
add1_rc=0
"$ZPAQ" add a1.zpaq src >add1.log 2>&1 || add1_rc=$?
ext1_rc=0
"$ZPAQ" extract a1.zpaq -to out1 >ext1.log 2>&1 || ext1_rc=$?
if [ "$add1_rc" -eq 0 ] && [ "$ext1_rc" -eq 0 ] \
   && cmp -s src/zpaq.bin out1/src/zpaq.bin \
   && cmp -s src/text.txt out1/src/text.txt; then
    ok "T2 add+extract round trip is byte-identical for both payload members"
else
    no "T2 round trip mismatch (add rc=$add1_rc, extract rc=$ext1_rc)" \
       "$(cat add1.log ext1.log 2>/dev/null || true)" \
       "$(ls -l out1/src 2>&1 || true)"
fi

# ── T3: journaling — a second add() stores a new version of the changed
#        member only (the unchanged 2.2 MB member is not re-added) ─────────
printf 'CHANGED CONTENT FOR VERSION 2\n' >> src/text.txt
cp src/text.txt text-v2.txt
add2_rc=0
"$ZPAQ" add a1.zpaq src >add2.log 2>&1 || add2_rc=$?
OUT=$("$ZPAQ" l a1.zpaq 2>&1) || true
case "$OUT" in
    *"2 versions"*)
        ok "T3 second add() created a second journal version (2 versions)" ;;
    *)
        no "T3 journal version count wrong (add rc=$add2_rc)" "$OUT" ;;
esac

# ── T4: rollback — -until 1 restores the previous revision byte-exactly ────
roll_rc=0
"$ZPAQ" x a1.zpaq src/text.txt -until 1 -to v1copy.txt >roll.log 2>&1 || roll_rc=$?
if [ "$roll_rc" -eq 0 ] && cmp -s text-v1.txt v1copy.txt; then
    ok "T4 -until 1 restores the v1 revision byte-exactly"
else
    no "T4 rollback mismatch (rc=$roll_rc)" \
       "$(cat roll.log 2>&1 || true)" \
       "$(cmp text-v1.txt v1copy.txt 2>&1 || true)"
fi

# ── T5: deduplication accounting is present in the listing, and the second
#        add() really added only the one changed member ────────────────────
OUT=$("$ZPAQ" l a1.zpaq 2>&1) || true
case "$OUT" in
    *"after dedupe"*)
        ok "T5 listing accounts for cross-version fragment dedup" ;;
    *)
        no "T5 no dedup accounting in listing" "$OUT" ;;
esac
case "$(cat add2.log 2>/dev/null || true)" in
    *"1 +added, 0 -removed."*)
        ok "T5b second add() re-added only the changed member" ;;
    *)
        no "T5b incremental add count wrong" "$(cat add2.log 2>/dev/null || true)" ;;
esac

# ── T6: diagnostics — a missing archive is reported, not silently accepted ─
# The output directory is pre-created so that the archive path is the only
# possible source of ENOENT, and the assertion pins both the offending file
# name and the reason plus the (measured) non-zero status, so the check cannot
# pass for an unrelated missing path.
mkdir -p out6
t6_rc=0
OUT=$("$ZPAQ" x no-such-archive.zpaq -to out6 2>&1) || t6_rc=$?
case "$OUT" in
    *"no-such-archive.zpaq: No such file or directory"*)
        if [ "$t6_rc" -ne 0 ]; then
            ok "T6 missing archive is diagnosed and reported as rc=$t6_rc"
        else
            no "T6 missing archive diagnosed but exit status was 0" "$OUT"
        fi ;;
    *)
        no "T6 missing archive not diagnosed (rc=$t6_rc)" "$OUT" ;;
esac

echo "RESULT: ${PASSED}/${CHECKS} checks passed"
[ "$PASSED" -eq "$CHECKS" ] || exit 1
exit 0
