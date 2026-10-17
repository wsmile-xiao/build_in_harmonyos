#!/bin/bash
# test_mstpd.sh — mstpd 0.2.0 consumer test (HarmonyOS PC)
#
# Runs inside the conanrun environment.  Every artifact is written to the
# absolute directory given by MSTPD_TEST_OUT; nothing is written relative to
# the current working directory, because the framework executes a second
# (negative) conan test pass over the same test_package folder and would
# otherwise clobber this evidence.
#
# Structure:
#   ASSERT   real executed assertions, counted in PASS/FAIL below
#   CAPTURE  capability-surface recordings (daemon run, client run, syscall
#            probe) whose values are quoted verbatim in notes.md / reports
set -u

OUT="${MSTPD_TEST_OUT:?MSTPD_TEST_OUT must be an absolute directory}"
BIN="${MSTPD_BINDIR:?MSTPD_BINDIR must point at the package bin directory}"
PROBE="${MSTPD_PROBE:-}"

mkdir -p "$OUT"
PASS=0
FAIL=0

ck() { # ck <name> <condition-result> <detail>
    local name="$1" ok="$2" detail="${3:-}"
    if [ "$ok" = "0" ]; then
        PASS=$((PASS + 1))
        printf 'ASSERT pass  %s %s\n' "$name" "$detail"
    else
        FAIL=$((FAIL + 1))
        printf 'ASSERT FAIL  %s %s\n' "$name" "$detail"
    fi
}

printf '== consumer test: mstpd 0.2.0 ==\n'
printf 'bindir=%s\n' "$BIN"
ls -l "$BIN" > "$OUT/package-bin-ls.txt" 2>&1

# ---------------------------------------------------------------- A1: mstpd -V
"$BIN/mstpd" -V > "$OUT/mstpd-V.out" 2> "$OUT/mstpd-V.err"
rc=$?
ck "mstpd -V exit code" "$([ $rc -eq 0 ] && echo 0 || echo 1)" "rc=$rc"
if grep -Eq '^0\.2\.0' "$OUT/mstpd-V.out"; then
    ck "mstpd -V reports 0.2.0" 0 "output=$(tr -d '\n' < "$OUT/mstpd-V.out")"
else
    ck "mstpd -V reports 0.2.0" 1 "see $OUT/mstpd-V.out"
fi

# ------------------------------------------------------------- A2: mstpctl -h
"$BIN/mstpctl" -h > "$OUT/mstpctl-h.out" 2> "$OUT/mstpctl-h.err"
rc=$?
printf 'mstpctl -h rc=%d\n' "$rc" > "$OUT/mstpctl-h-rc.txt"
if grep -qF 'Usage: mstpctl' "$OUT/mstpctl-h.out"; then
    ck "mstpctl -h prints usage" 0 "rc=$rc"
else
    ck "mstpctl -h prints usage" 1 "rc=$rc, see $OUT/mstpctl-h.out"
fi

# ---------------------------------------------------------------- A3: mstpctl -V
"$BIN/mstpctl" -V > "$OUT/mstpctl-V.out" 2> "$OUT/mstpctl-V.err"
rc=$?
if [ $rc -eq 0 ] && [ -s "$OUT/mstpctl-V.out" ]; then
    ck "mstpctl -V prints a version" 0 "rc=$rc output=$(tr -d '\n' < "$OUT/mstpctl-V.out")"
else
    ck "mstpctl -V prints a version" 1 "rc=$rc"
fi

# ------------------------------------------- A4: generated scripts are complete
# bridge-stp is produced from bridge-stp.in by the Makefile sed template pass;
# an unsubstituted @token@ would mean the install produced a broken script.
if [ -f "$BIN/bridge-stp" ]; then
    sh -n "$BIN/bridge-stp"; rc=$?
    ck "bridge-stp passes sh -n" "$([ $rc -eq 0 ] && echo 0 || echo 1)" "rc=$rc"
    if grep -q '@[a-z]*@' "$BIN/bridge-stp"; then
        ck "bridge-stp has no unsubstituted template tokens" 1 ""
    else
        ck "bridge-stp has no unsubstituted template tokens" 0 ""
    fi
else
    ck "bridge-stp installed" 1 "missing $BIN/bridge-stp"
fi

# ------------------------------------------- A5: helper scripts landed on disk
# Upstream's own location: Makefile.am:44 utilsexecdir=$(libexecdir)/mstpctl-utils,
# and configure.ac:34 pins libexecdir=/lib whenever exec_prefix is empty
# (configure.ac:11 empties it unconditionally) -- so it is lib/, not libexec/.
UTIL="$(dirname "$BIN")/lib/mstpctl-utils"
missing=""
for f in "$BIN/bridge-stp" "$UTIL/mstp_config_bridge" "$UTIL/ifquery" \
         "$UTIL/ifupdown.sh" "$UTIL/mstpctl-utils-functions.sh"; do
    [ -e "$f" ] || missing="$missing $f"
done
ck "helper scripts installed under lib/mstpctl-utils" "$([ -z "$missing" ] && echo 0 || echo 1)" "missing:${missing:- none}"

# ------------------------------------------------ A6: ELF is loadable on device
"$BIN/mstpctl" --version > "$OUT/mstpctl-longversion.out" 2>&1
rc=$?
ck "mstpctl --version (long option) execs" "$([ $rc -eq 0 ] && echo 0 || echo 1)" "rc=$rc"

# ==========================================================================
# CAPTURE — runtime capability surface.  Recorded verbatim, interpreted in
# notes.md; these lines are not counted as assertions.
# ==========================================================================
echo
echo '== CAPTURE: syscall capability probe =='
if [ -n "$PROBE" ] && [ -x "$PROBE" ]; then
    "$PROBE" > "$OUT/capability-probes.txt" 2>&1
    printf 'probe rc=%d -> %s\n' "$?" "$OUT/capability-probes.txt"
    sed -n '1,200p' "$OUT/capability-probes.txt"
else
    echo 'probe binary not available'
fi

echo
echo '== CAPTURE: mstpd foreground run (upstream sanity_check + event loop) =='
"$BIN/mstpd" -d -v 7 > "$OUT/mstpd-foreground.log" 2>&1 &
child=$!
sleep 3
if kill -0 "$child" 2>/dev/null; then
    printf 'mstpd -d stayed alive for 3s, terminating it\n'
    kill "$child" 2>/dev/null
    wait "$child" 2>/dev/null
    printf 'mstpd -d observation=alive-after-3s\n' > "$OUT/mstpd-daemon-rc.txt"
else
    wait "$child" 2>/dev/null
    drc=$?
    printf 'mstpd -d exited early, rc=%d\n' "$drc"
    printf 'mstpd -d observation=exited-early rc=%d\n' "$drc" > "$OUT/mstpd-daemon-rc.txt"
fi
sed -n '1,60p' "$OUT/mstpd-foreground.log"

echo
echo '== CAPTURE: staged-install absolute paths (deployment model, not a gate) =='
{
    for l in "$BIN/mstp_restart" "$UTIL/mstpctl_restart_config"; do
        printf 'entry=%s target=%s resolves_inside_package=%s\n' \
            "$l" "$(readlink "$l")" "$([ -e "$l" ] && echo yes || echo no)"
    done
    grep -n '^config_cmd=' "$BIN/bridge-stp"
} > "$OUT/staged-absolute-paths.txt" 2>&1
sed -n '1,20p' "$OUT/staged-absolute-paths.txt"

echo
echo '== CAPTURE: mstpctl client against an unconfigured bridge =='
"$BIN/mstpctl" showtree br0 > "$OUT/mstpctl-showtree-br0.log" 2>&1
printf 'mstpctl showtree br0 rc=%d\n' "$?"
sed -n '1,20p' "$OUT/mstpctl-showtree-br0.log"
"$BIN/mstpctl" -b br0 showtree > "$OUT/mstpctl-b-showtree.log" 2>&1
printf 'mstpctl -b br0 showtree rc=%d\n' "$?"
sed -n '1,20p' "$OUT/mstpctl-b-showtree.log"

echo
echo "MSTPD_TEST_SUMMARY executed=$((PASS + FAIL)) passed=$PASS failed=$FAIL"
[ $FAIL -eq 0 ]
