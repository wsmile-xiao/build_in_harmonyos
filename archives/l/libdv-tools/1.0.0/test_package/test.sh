#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for encodedv / dubdv / dvconnect.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

for tool in encodedv dubdv dvconnect; do
    command -v "$tool" >/dev/null || { echo "$tool is not on PATH"; exit 1; }
done

# 1) popt --version / --help (both write to stderr for these programs).
echo "[test] encodedv --version"
VERSION_OUT="$(encodedv --version 2>&1)"
case "$VERSION_OUT" in
    *version*) echo "        [ok] $VERSION_OUT" ;;
    *) echo "encodedv --version did not report a version: $VERSION_OUT"; exit 1 ;;
esac

echo "[test] encodedv --help"
HELP_OUT="$(encodedv --help 2>&1)"
for opt in "start-frame" "end-frame" "vlc-passes"; do
    case "$HELP_OUT" in
        *"$opt"*) ;;
        *) echo "encodedv --help does not mention --$opt"; echo "$HELP_OUT"; exit 1 ;;
    esac
done
echo "        [ok] help lists the real popt option table"

echo "[test] dubdv --help"
dubdv --help >/dev/null 2>&1
echo "        [ok] dubdv --help exit status 0"

# 2) Regression guard for the "configure did not find popt" failure mode.
#    Without HAVE_LIBPOPT the whole option parser disappears: -v/--version prints
#    nothing and exits 0, and a bare invocation dereferences argv[1] == NULL and
#    dies with SIGSEGV.  So a bare invocation must be an ordinary error exit, and
#    never a crash.
#
#    Two details worth pinning down before reading the loop below:
#      * exit(-1) is what encodedv and dubdv do for "no file name given", and the
#        shell reports that as 255, so only the shell's own signal statuses are
#        treated as a crash.
#      * dvconnect with an empty argument list does not go through that path at
#        all - it falls through to opening /dev/video1394/0 (absent on the OHOS
#        device) and reports 0.  Its -v is equally special: upstream handles
#        'v' in the popt loop but the option table does not route -v there, so
#        the tool walks on to the device open instead of printing a version.
#        Both are upstream behaviour, so dvconnect only gets the crash check.
for tool in encodedv dubdv dvconnect; do
    echo "[test] $tool <no arguments> (expected no crash)"
    set +e
    "$tool" >/dev/null 2>&1
    rc=$?
    set -e
    case "$rc" in
        134|135|136|137|138|139|141|143)
            echo "$tool died from a signal (exit status $rc) - it was built without popt"
            exit 1
            ;;
    esac
    if [ "$rc" -eq 0 ] && [ "$tool" != dvconnect ]; then
        echo "$tool reported success without any arguments"
        exit 1
    fi
    echo "        [ok] $tool exit status $rc"
done

# 3) Negative control: an unknown option must be rejected through popt's own
#    error path (this is the check that fails first when popt is missing, since
#    the option table itself is compiled out).
#
#    Deliberately *not* asserted here: a file-name pattern that matches nothing.
#    encodedv walks the pattern, encodes zero frames and exits 0 - that is
#    upstream behaviour, not a defect, and a device with no video input cannot
#    produce the files an honest positive test would need.
echo "[test] encodedv --definitely-not-an-option (expected failure)"
if encodedv --definitely-not-an-option >/dev/null 2>&1; then
    echo "encodedv accepted an unknown option"
    exit 1
fi
echo "        [ok] unknown option rejected"

echo "All tests passed."