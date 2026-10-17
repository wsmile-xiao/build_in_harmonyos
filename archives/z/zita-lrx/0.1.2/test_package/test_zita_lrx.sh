#!/bin/sh
# zita-lrx 0.1.2 packaged-tool smoke test.
#
# zita-lrx is a JACK real-time crossover filter client: it needs a running
# JACK server and audio hardware, which the OHOS build host does not have.
# The pass conditions are layered, and each layer is actually executed and
# reported with a machine-readable verdict line:
#
#   LOADER/PARSER layer:
#     load-banner        `zita-lrx -h` prints the "zita-lrx-0.1.2" banner and
#                        takes the upstream exit(1) path (help() exits 1).
#     load-noargs        `zita-lrx` with no argument falls through to the same
#                        banner, exit 1.
#     load-missing-conf  a nonexistent config file makes Lrxconf::load fail
#                        and main() report "Can't load configuration", exit 1.
#     All three prove the loader accepted the binary and the shared-library
#     closure resolved (a loader rejection shows up as exit 127 instead).
#
#   CAPABILITY layer:
#     process-valid-conf a *valid* config file is parsed to completion (full
#                        Lrxconf grammar: /zita-lrx, /xover/freq, /xover/shape)
#                        and main() reaches the Jclient construction, which
#                        fails with "Can't connect to JACK" because the host
#                        runs no JACK server. The clthreads A_thread base and
#                        the config parser are exercised for real; only the
#                        audio service boundary is unreachable, and that is
#                        asserted by its observed signature.
#     realtime-dsp       declared SKIP with reason: the real-time crossover
#                        processing needs a live JACK audio graph, which no
#                        build host provides. Never recorded as a pass.
#
# NOTE: OHOS /system/bin/sh (toybox) lacks command substitution `$(...)`,
# so checks are done through pipelines and rc captures instead.
#
# Usage: test_zita_lrx.sh <path-to-staged-bin-dir> <path-to-work-dir>

set -u

BIN_DIR="$1"
WORK_DIR="$2"

fail()
{
    echo "FAIL: $1" >&2
    exit 1
}

[ -x "$BIN_DIR/zita-lrx" ] || fail "zita-lrx not found in $BIN_DIR"
[ -d "$WORK_DIR" ] || fail "work directory missing: $WORK_DIR"

# ---- LOADER/PARSER layer ----------------------------------------------

# 1) zita-lrx -h must print the version banner (exit code 1 is expected
#    upstream: help() calls exit(1)).
"$BIN_DIR/zita-lrx" -h > "$WORK_DIR/help_out.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "zita-lrx -h returned $rc, expected 1"
grep -q "zita-lrx-0.1.2" "$WORK_DIR/help_out.txt" || fail "-h banner missing"
echo "ZITA_LRX_TEST_PASS case=load-banner banner=zita-lrx-0.1.2 exit_code=1"

# 2) zita-lrx with no argument must print the banner and return 1
#    (not 127 = shared-library load failure, not a crash).
"$BIN_DIR/zita-lrx" > "$WORK_DIR/noargs_out.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "zita-lrx (no args) returned $rc, expected 1"
grep -q "zita-lrx-0.1.2" "$WORK_DIR/noargs_out.txt" || fail "no-args banner missing"
echo "ZITA_LRX_TEST_PASS case=load-noargs exit_code=1"

# 3) A nonexistent config file must report the load failure and return 1 —
#    exercises the Lrxconf::load parser error path.
"$BIN_DIR/zita-lrx" "$WORK_DIR/missing.zlrx" > "$WORK_DIR/missing_out.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "zita-lrx missing-config returned $rc, expected 1"
grep -q "Can't load configuration" "$WORK_DIR/missing_out.txt" || fail "missing-config error signature absent"
echo "ZITA_LRX_TEST_PASS case=load-missing-conf exit_code=1 signature=Cant-load-configuration"

# ---- CAPABILITY layer -------------------------------------------------

# 4) A valid config file must be parsed to completion and main() must reach
#    the JACK client construction. With no JACK server on the build host the
#    observed failure is "Can't connect to JACK" with exit 1 — exit code 1
#    (not 127/126) proves the whole closure loaded and the parser ran.
cat > "$WORK_DIR/smoke.zlrx" <<'EOF'
/zita-lrx  2  2
/xover/freq   1  2000
/xover/shape  1  -6.0
EOF
"$BIN_DIR/zita-lrx" "$WORK_DIR/smoke.zlrx" > "$WORK_DIR/jack_out.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "zita-lrx valid-config returned $rc, expected 1"
grep -q "Can't connect to JACK" "$WORK_DIR/jack_out.txt" || fail "JACK boundary signature absent"
echo "ZITA_LRX_TEST_PASS case=process-valid-conf exit_code=1 signature=Cant-connect-to-JACK"

# 5) The real-time DSP path needs a live JACK audio graph; declared SKIP
#    with reason, never recorded as a pass.
echo "ZITA_LRX_TEST_SKIP case=realtime-dsp reason=no-live-jack-audio-graph-on-build-host"

echo "ZITA_LRX_SMOKE_PASS load=3 process=1 skipped=1 failed=0"
exit 0
