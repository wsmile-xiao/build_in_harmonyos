#!/bin/sh
# test_package/test_lutefisk.sh �?functional test for the packaged lutefisk CLI.
#
# Runs the packaged aarch64-linux-ohos executable (binfmt/qemu on the CI worker)
# and asserts observable behaviour, not internal state:
#   * the usage text lists every documented option;
#   * a full de novo sequencing run over the upstream sample spectrum produces
#     the published reference peptide ranking (Qtof_ELVISLIVESK.dta);
#   * the run-time data files that the program reads are really installed and
#     really consumed (the -s database is reported as loaded);
#   * a missing input file makes the program fail (proves the positive path is
#     not a no-op);
#   * HarmonyOS ELF properties (aarch64 / PIE / NX / RELRO / system libs only).
#
# POSIX sh only (no bashisms) so it behaves the same under dash.
set -u

EXE=${1:?usage: test_lutefisk.sh <exe> <share-dir> <elf_check.py>}
SHARE=${2:?}
ELFCHECK=${3:?}

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
}

expect_grep() {
    # expect_grep <label> <pattern> <file>
    if grep -q -- "$2" "$3"; then
        ok "$1"
    else
        bad "$1 (pattern not found: $2)"
    fi
}

EXAMPLES="$SHARE/examples"
DTA="$EXAMPLES/Qtof_ELVISLIVESK.dta"
REF="$EXAMPLES/Qtof_ELVISLIVESK.lut"
DETAILS="$SHARE/Lutefisk.details"
RESIDUES="$SHARE/Lutefisk.residues"
PARAMS="$SHARE/Lutefisk.qtof_params"
DB="$SHARE/database.sequence"
OUT="$WORK/result.lut"
STDOUT="$WORK/stdout.txt"

# ---------------------------------------------------------------- T1..T3 ----
echo "--- usage / help ---"
"$EXE" -h > "$WORK/help.txt" 2>&1
rc=$?
# Upstream's case 'h' prints the usage and then calls exit(1)
# (LutefiskMain.c:663-677), so rc=1 is the correct expectation here.
if [ "$rc" -eq 1 ]; then
    ok "T1: lutefisk -h prints usage and exits 1 (upstream behaviour, rc=$rc)"
else
    bad "T1: lutefisk -h exited $rc, expected 1"
fi
expect_grep "T2: usage banner printed" "USAGE:  lutefisk" "$WORK/help.txt"

missing=""
for opt in o q m d p r s v h; do
    if ! grep -q -- "-$opt = " "$WORK/help.txt"; then
        missing="$missing -$opt"
    fi
done
if [ -z "$missing" ]; then
    ok "T3: all 9 documented options listed in usage"
else
    bad "T3: options missing from usage:$missing"
fi

# ------------------------------------------------------------- T4..T11 ----
echo "--- full de novo sequencing run on the upstream sample spectrum ---"
if [ ! -f "$DTA" ]; then
    bad "T4: sample spectrum not installed at $DTA"
else
    ok "T4: sample spectrum Qtof_ELVISLIVESK.dta installed"

    "$EXE" -q -m 1229.74 -d "$DETAILS" -p "$PARAMS" -r "$RESIDUES" \
        -s "$DB" -o "$OUT" "$DTA" > "$STDOUT" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ]; then
        ok "T5: analysis run exits 0 (rc=$rc)"
    else
        bad "T5: analysis run exited $rc"
    fi

    if [ -s "$OUT" ]; then
        ok "T6: output file written and non-empty"
    else
        bad "T6: output file missing or empty"
        echo "--- program stdout ---"
        cat "$STDOUT"
    fi

    expect_grep "T7: version banner in result" "LutefiskXP v1.0.7" "$OUT"
    expect_grep "T8: molecular weight from the spectrum" \
        "Molecular Weight: 1228.73" "$OUT"
    expect_grep "T9: charge state from the spectrum" "Charge State:  2" "$OUT"
    expect_grep "T10: ranked-candidate table header" \
        "Rank  Pr(c)   PevzScr  Quality IntScr X-corr" "$OUT"
    expect_grep "T11: search completed" "Search time:" "$OUT"

    # The X-corr column is recomputed by the local libm, so it is excluded from
    # every comparison; the sequence column and the four score columns that come
    # straight out of the search are compared against the reference the
    # upstream author published for this very spectrum in 2005.
    if [ -f "$REF" ]; then
        ranked() {
            # $1 = .lut file -> "<seq> <Pr(c)> <PevzScr> <Quality> <IntScr>" per row
            awk '/^ *Sequence/ {seen = 1; next}
                 seen && NF >= 7 {print $1, $3, $4, $5, $6}' "$1"
        }
        ranked "$OUT" > "$WORK/got.txt"
        ranked "$REF" > "$WORK/ref.txt"

        got=$(wc -l < "$WORK/got.txt")
        if [ "$got" -ge 10 ]; then
            ok "T12: at least 10 ranked candidates produced ($got)"
        else
            bad "T12: only $got ranked candidates"
        fi

        cut -d' ' -f1 "$WORK/got.txt" | sort > "$WORK/got.seq"
        cut -d' ' -f1 "$WORK/ref.txt" | sort > "$WORK/ref.seq"
        if [ "$got" -ge 10 ] && diff -q "$WORK/got.seq" "$WORK/ref.seq" > /dev/null 2>&1; then
            ok "T13: de novo peptide set matches the upstream reference output"
        else
            bad "T13: peptide set differs from the upstream reference"
            diff "$WORK/ref.seq" "$WORK/got.seq" | head -10
        fi

        head -10 "$WORK/got.txt" | cut -d' ' -f1 > "$WORK/got.order"
        head -10 "$WORK/ref.txt" | cut -d' ' -f1 > "$WORK/ref.order"
        if diff -q "$WORK/got.order" "$WORK/ref.order" > /dev/null 2>&1; then
            ok "T13b: ranking ORDER of the top 10 matches the reference (not just the set)"
        else
            bad "T13b: top-10 ranking order differs from the reference"
            diff "$WORK/ref.order" "$WORK/got.order" | head -10
        fi

        # Score columns: numeric compare with a 0.005 tolerance, because the
        # 2005 reference was produced with a different libm (Pr(c) at rank 9
        # reads 0.932 here vs 0.933 there; X-corr differs in the 3rd decimal).
        if head -10 "$WORK/got.txt" > "$WORK/g10" && head -10 "$WORK/ref.txt" > "$WORK/r10" \
           && awk '
               FNR == NR { for (i = 1; i <= NF; i++) r[FNR, i] = $i; nr = FNR; next }
               { ok = 1
                 if ($1 != r[FNR, 1]) { print "seq mismatch line " FNR ": " $1 " vs " r[FNR, 1] > "/dev/stderr"; ok = 0 }
                 for (i = 2; i <= 5; i++) {
                     d = $i - r[FNR, i]
                     if (d < 0) d = -d
                     if (d > 0.005) { print "col " i " line " FNR ": " $i " vs " r[FNR, i] > "/dev/stderr"; ok = 0 }
                 }
                 if (!ok) bad++ }
               END { if (bad > 0) { print "mismatching rows: " bad > "/dev/stderr"; exit 1 } }
           ' "$WORK/r10" "$WORK/g10"; then
            ok "T13c: Pr(c)/PevzScr/Quality/IntScr of the top 10 match the reference (tol 0.005)"
        else
            bad "T13c: score columns of the top 10 differ from the reference"
        fi

        top=$(head -1 "$WORK/got.txt")
        case "$top" in
        NQVLSLLVESK\ *)
            ok "T14: top-ranked peptide is NQVLSLLVESK with Pr(c)=$(echo "$top" | cut -d' ' -f2)"
            ;;
        *)
            bad "T14: unexpected top-ranked peptide line: $top"
            ;;
        esac
    else
        bad "T12: upstream reference output not installed at $REF"
    fi

    expect_grep "T15: spectrum was read (data point count)" \
        "Data points = 1622" "$STDOUT"
    expect_grep "T16: searchable sequence database was loaded" \
        "database sequences added." "$STDOUT"
fi

# --------------------------------------------------------------- T17..T18 ----
echo "--- negative path (must fail) ---"
"$EXE" -q -o "$WORK/never.lut" "$WORK/does-not-exist.dta" > "$WORK/neg.txt" 2>&1
rc=$?
if [ "$rc" -eq 127 ]; then
    bad "T17: lutefisk is not executable at $EXE (rc=127)"
elif [ "$rc" -ne 0 ]; then
    ok "T17: missing input spectrum makes lutefisk fail (rc=$rc)"
else
    bad "T17: missing input spectrum still exited 0"
fi

# ------------------------------------------------------- T18 (OHOS) ----
echo "--- HarmonyOS ELF properties ---"
if python3 "$ELFCHECK" "$EXE"; then
    ok "T18: HarmonyOS ELF properties (8 sub-assertions above)"
else
    bad "T18: HarmonyOS ELF properties (see sub-assertions above)"
fi

echo
echo "assertions: $((PASS + FAIL)), passed: $PASS, failed: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
