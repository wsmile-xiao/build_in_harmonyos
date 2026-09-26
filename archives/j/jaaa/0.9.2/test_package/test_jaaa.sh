#!/bin/sh
# jaaa-0.9.2 packaged-tool smoke test.
#
# jaaa is an X11 GUI audio analyser with JACK and ALSA inputs.  The device is
# headless and runs no JACK server, so "runs the GUI" is not a reachable pass
# condition.  The assertions are layered instead, and every layer reports its
# own machine-readable verdict:
#
#   LOAD   : `jaaa -h` must print the upstream version banner.  help() is
#            reached before any X or JACK call, so printing it proves the ELF
#            was accepted by the loader and the whole shared-library closure
#            (libclxclient/libclthreads/libzita-alsa-pcmi/libasound/libfftw3f/
#            libjack/libXft/libX11) resolved.  Upstream help() calls exit(1),
#            so exit 1 is the expected value here.
#   PROCESS: `jaaa` with no argument must reach X_display() and fail there.
#            The expected signature is "Can't open display !" with exit 1 --
#            explicitly NOT 127 ("Error loading shared library"), which would
#            mean the loader, not the missing display, is what broke.
#   SKIP   : `jaaa -J` (JACK) and `jaaa -A` (ALSA) need a display first, so on
#            a headless device the audio paths are never entered.  These are
#            declared per-case SKIP with the observed signature, not PASS.
#
# NOTE: /bin/sh on OHOS is toybox ash; this script avoids command substitution
# and here-strings, mirroring the aliki/clxclient OHOS test pattern.
#
# Usage: test_jaaa.sh <path-to-bin-dir> <writable-work-dir>

set -u

BIN_DIR="$1"
WORK_DIR="$2"
BIN="$BIN_DIR/jaaa"

if [ ! -x "$BIN" ]; then
    echo "FAIL: jaaa not found or not executable in $BIN_DIR" >&2
    echo "JAAA_TEST_FAIL load reason=missing-binary" >&2
    exit 1
fi

# ---- LOAD layer -----------------------------------------------------------
# The banner proves we got past the dynamic loader and into main().
if ! "$BIN" -h 2>&1 | grep -q "Jaaa-0.9.2"; then
    echo "JAAA_TEST_FAIL load reason=no-version-banner" >&2
    "$BIN" -h 2>&1 | head -n 5 >&2
    exit 1
fi
echo "JAAA_TEST_PASS load banner=Jaaa-0.9.2"

# The banner path exits 1 upstream; anything else (127/126/SIGSEGV) is a
# loader or execution failure, not a normal early exit.
"$BIN" -h >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "JAAA_TEST_FAIL load exit_code=$rc expected=1" >&2
    exit 1
fi
echo "JAAA_TEST_PASS load exit_code=1"

# ---- PROCESS layer --------------------------------------------------------
# No argument: X_resman init succeeds, then X_display() must be what stops us.
"$BIN" > /dev/null 2>"$WORK_DIR/jaaa-noarg.err"
rc=$?
if [ "$rc" -eq 127 ] || [ "$rc" -eq 126 ]; then
    echo "JAAA_TEST_FAIL process exit_code=$rc reason=loader-rejected" >&2
    head -n 5 "$WORK_DIR/jaaa-noarg.err" >&2
    exit 1
fi
if ! grep -q "Can't open display" "$WORK_DIR/jaaa-noarg.err"; then
    echo "JAAA_TEST_FAIL process exit_code=$rc reason=no-x-layer-signature" >&2
    head -n 5 "$WORK_DIR/jaaa-noarg.err" >&2
    exit 1
fi
echo "JAAA_TEST_PASS process exit_code=$rc signature=Cant-open-display"

# ---- CAPABILITY-DEPENDENT cases (declared skipped, with signatures) -------
# -J selects the JACK client path and -A the ALSA path, but both are reached
# only after X_display() has succeeded, so neither audio backend can be
# exercised on a headless device without a JACK server.  Report them honestly.
"$BIN" -J >/dev/null 2>&1
echo "JAAA_TEST_SKIP case=jack-client-connect exit_code=$? reason=headless-no-x-display-and-no-jack-server"
"$BIN" -A >/dev/null 2>&1
echo "JAAA_TEST_SKIP case=alsa-capture-open exit_code=$? reason=headless-no-x-display-and-no-audio-device"
"$BIN" >/dev/null 2>&1
rc=$?
echo "JAAA_TEST_SKIP case=gui-render exit_code=$rc reason=headless-no-x-display"

echo "JAAA_SMOKE_PASS load=2 process=1 skipped=3 failed=0"
exit 0
