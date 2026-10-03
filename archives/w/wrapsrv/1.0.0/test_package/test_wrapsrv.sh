#!/bin/bash
# test_wrapsrv.sh -- functional test for the wrapsrv 1.0.0 CLI.
#
# Invoked by test_package/conanfile.py with WRAPSRV_RES_STUB pointing at the
# LD_PRELOAD object compiled from res_stub.c.  Every assertion below runs the
# *delivered* wrapsrv binary (conan's run_environment puts the package's bin/
# on PATH) and compares exact bytes / exit codes -- no "did not crash" checks.
#
# Covered:
#   1. CLI contract: no args / one arg / --help all fail with the upstream
#      usage text on stderr and exit status 1.
#   2. Full SRV pipeline against a byte-accurate canned DNS answer:
#      answer parsing, %h / %p substitution (standalone and inline), execution
#      of the substituted command line and propagation of its exit status.
#   3. RFC 2782 selection order: lowest priority first, and fallback to the
#      next priority when the command fails.
#   4. Negative DNS paths: NXDOMAIN rcode and empty answer section.
#   5. A live lookup through the platform resolver (no stub) must fail for a
#      name that cannot exist.
set -u
export LC_ALL=C

PASS=0
FAIL=0
TOTAL=0
FAILURES=()

t() { # t <name> <expected_exit> <actual_exit>
    TOTAL=$((TOTAL + 1))
    if [ "$3" = "$2" ]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAILURES+=("  $1: exit $3 != $2")
    fi
}

check() { # check <name> <condition_rc> <detail-on-fail>
    TOTAL=$((TOTAL + 1))
    if [ "$2" = "0" ]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAILURES+=("  $1: $3")
    fi
}

RES_STUB="${WRAPSRV_RES_STUB:-}"
[ -n "$RES_STUB" ] || { echo "ERROR: WRAPSRV_RES_STUB not set" >&2; exit 2; }
[ -f "$RES_STUB" ] || { echo "ERROR: stub $RES_STUB missing" >&2; exit 2; }

TMPD=$(mktemp -d) || exit 2
trap 'rm -rf "$TMPD"' EXIT

SRVNAME="_stub._tcp.wrapsrv.test"

# Command line driven through wrapsrv's system() call.
cat > "$TMPD/show.sh" <<'SHEOF'
#!/bin/sh
echo "HOST=$1 PORT=$2"
SHEOF

# Always-failing command line: records every attempt so the RFC 2782 fallback
# order becomes observable.
cat > "$TMPD/failer.sh" <<'SHEOF'
#!/bin/sh
echo "try $1 $2" >> "$WRAPSRV_TRIES"
exit 1
SHEOF

# Command line echoing its single argument verbatim, so that in-line
# substitution can be observed without a second placeholder being consumed.
cat > "$TMPD/echo1.sh" <<'SHEOF'
#!/bin/sh
echo "$1"
SHEOF

chmod +x "$TMPD/show.sh" "$TMPD/echo1.sh" "$TMPD/failer.sh"

# stub <mode> <wrapsrv-args...> -- run the real binary with the DNS transport
# stubbed; LD_PRELOAD is scoped to this one invocation only.
stub() {
    mode=$1
    shift
    LD_PRELOAD="$RES_STUB" WRAPSRV_STUB_MODE="$mode" \
        WRAPSRV_TRIES="$TMPD/tries.log" wrapsrv "$@"
}

echo "=== wrapsrv functional test ==="

# ── 0. the packaged binary is present and runnable ────────────────────────
command -v wrapsrv >/dev/null 2>&1
t "wrapsrv-on-PATH" 0 $?
WRAPSRV_BIN=$(command -v wrapsrv 2>/dev/null)
[ -n "$WRAPSRV_BIN" ] && [ -x "$WRAPSRV_BIN" ]
check "wrapsrv-executable" $? "wrapsrv not found or not executable on PATH"

# ── 1. CLI contract: too few arguments is a usage error ───────────────────
wrapsrv >"$TMPD/u0.out" 2>"$TMPD/u0.err"; ec=$?
t "usage-noargs-exit" 1 $ec
grep -q 'Usage: wrapsrv <SRVNAME> <COMMAND> \[OPTION\]\.\.\.' "$TMPD/u0.err"
check "usage-noargs-text" $? "stderr: $(cat "$TMPD/u0.err")"
grep -q '%h and %p sequences will be converted to hostname and port\.' "$TMPD/u0.err"
check "usage-noargs-placeholder-doc" $? "stderr: $(cat "$TMPD/u0.err")"

wrapsrv _only_one_arg >"$TMPD/u1.out" 2>"$TMPD/u1.err"; ec=$?
t "usage-onearg-exit" 1 $ec
grep -q 'Usage: wrapsrv <SRVNAME> <COMMAND> \[OPTION\]\.\.\.' "$TMPD/u1.err"
check "usage-onearg-text" $? "stderr: $(cat "$TMPD/u1.err")"

wrapsrv --help >"$TMPD/u2.out" 2>"$TMPD/u2.err"; ec=$?
t "usage-help-flag-exit" 1 $ec
grep -q '%h and %p sequences will be converted to hostname and port\.' "$TMPD/u2.err"
check "usage-help-flag-text" $? "stderr: $(cat "$TMPD/u2.err")"

# ── 2. one SRV answer: substitution + real command execution ──────────────
# Answer: _stub._tcp.wrapsrv.test SRV 10 100 8080 primary.example.com
stub single "$SRVNAME" "$TMPD/show.sh" %h %p >"$TMPD/s1.out" 2>"$TMPD/s1.err"; ec=$?
t "single-srv-exit" 0 $ec
printf 'HOST=primary.example.com PORT=8080\n' >"$TMPD/s1.want"
cmp -s "$TMPD/s1.out" "$TMPD/s1.want"
check "single-srv-stdout" $? "got: $(cat "$TMPD/s1.out")"
! grep -q '%h\|%p' "$TMPD/s1.out"
check "single-srv-no-placeholder-leftover" $? "stdout still holds a placeholder: $(cat "$TMPD/s1.out")"

# ── 3. substitution is in-line, not only for standalone tokens ────────────
stub single "$SRVNAME" "$TMPD/echo1.sh" 'x%hy%pz' >"$TMPD/s2.out" 2>"$TMPD/s2.err"; ec=$?
t "inline-substitution-exit" 0 $ec
printf 'xprimary.example.comy8080z\n' >"$TMPD/s2.want"
cmp -s "$TMPD/s2.out" "$TMPD/s2.want"
check "inline-substitution-stdout" $? "got: $(cat "$TMPD/s2.out")"

# ── 4. RFC 2782: the lowest priority wins ─────────────────────────────────
# Answer lists the priority-20 record FIRST, so picking the answer order would
# hand over backup.example.com; RFC 2782 requires primary (priority 10).
stub pair "$SRVNAME" "$TMPD/show.sh" %h %p >"$TMPD/s3.out" 2>"$TMPD/s3.err"; ec=$?
t "priority-order-exit" 0 $ec
printf 'HOST=primary.example.com PORT=8080\n' >"$TMPD/s3.want"
cmp -s "$TMPD/s3.out" "$TMPD/s3.want"
check "priority-order-lowest-prio-first" $? "got: $(cat "$TMPD/s3.out")"

# ── 5. RFC 2782: a failing command falls back to the next priority ────────
rm -f "$TMPD/tries.log"
stub pair "$SRVNAME" "$TMPD/failer.sh" %h %p >"$TMPD/s4.out" 2>"$TMPD/s4.err"; ec=$?
t "fallback-exit-propagated" 1 $ec
[ "$(wc -l < "$TMPD/tries.log" 2>/dev/null || echo 0)" = "2" ]
check "fallback-two-attempts" $? "tries.log: $(cat "$TMPD/tries.log" 2>/dev/null)"
[ "$(sed -n 1p "$TMPD/tries.log" 2>/dev/null)" = "try primary.example.com 8080" ]
check "fallback-first-attempt-prio10" $? "tries.log line 1: $(sed -n 1p "$TMPD/tries.log" 2>/dev/null)"
[ "$(sed -n 2p "$TMPD/tries.log" 2>/dev/null)" = "try backup.example.com 9090" ]
check "fallback-second-attempt-prio20" $? "tries.log line 2: $(sed -n 2p "$TMPD/tries.log" 2>/dev/null)"

# ── 6. negative DNS answers ───────────────────────────────────────────────
stub nxdomain "$SRVNAME" "$TMPD/show.sh" %h %p >"$TMPD/s5.out" 2>"$TMPD/s5.err"; ec=$?
t "nxdomain-exit" 1 $ec
grep -q "returned rcode 3" "$TMPD/s5.err"
check "nxdomain-rcode-reported" $? "stderr: $(cat "$TMPD/s5.err")"
[ ! -s "$TMPD/s5.out" ]
check "nxdomain-command-not-run" $? "command ran despite NXDOMAIN: $(cat "$TMPD/s5.out")"

stub noanswer "$SRVNAME" "$TMPD/show.sh" %h %p >"$TMPD/s6.out" 2>"$TMPD/s6.err"; ec=$?
t "noanswer-exit" 1 $ec
grep -q 'returned no answers' "$TMPD/s6.err"
check "noanswer-diagnosed" $? "stderr: $(cat "$TMPD/s6.err")"

# ── 7. live lookup through the platform resolver (no stub) ─────────────────
# .invalid is reserved by RFC 2606 and can never resolve, so this exercises the
# real res_init()/res_query() of the OHOS libc and must not report success.
wrapsrv _no_such_service._tcp.wrapsrv.invalid "$TMPD/show.sh" %h %p \
    >"$TMPD/s7.out" 2>"$TMPD/s7.err"; ec=$?
[ "$ec" != "0" ]
check "live-resolver-fails" $? "wrapsrv exited 0 for an unresolvable name"
[ -s "$TMPD/s7.err" ]
check "live-resolver-diagnoses" $? "no diagnostic on stderr for an unresolvable name"

echo "TOTAL=$TOTAL PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    printf '%s\n' "${FAILURES[@]}" >&2
    exit 1
fi
echo "=== All tests passed ==="
exit 0
