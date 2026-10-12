#!/bin/sh
# Runtime assertions for the packaged tucnak binary.
#
# Usage: test_version.sh [path-to-tucnak]
#
# Standalone companion to test_package/conanfile.py: run it by hand against an
# extracted package to re-check the banner.  conanfile.py performs the same
# assertions in-process during CI.

set -e

BINARY="${1:-tucnak}"

if ! command -v "$BINARY" >/dev/null 2>&1 && [ ! -x "$BINARY" ]; then
    echo "FAIL: tucnak binary not found: $BINARY" >&2
    exit 1
fi

# tucnak has no getopt_long options.  "-i" (system info) is the flag that prints
# the banner and exits non-interactively; "--version" reaches the same branch
# through getopt's letter matching.  Never use "--help": 'h' takes an argument,
# so getopt consumes "elp" as the home directory and the program aborts while
# trying to create it.
VERSION_OUT="$("$BINARY" --version 2>&1 || true)"
echo "tucnak --version: $VERSION_OUT"

case "$VERSION_OUT" in
    *4.67*)
        echo "PASS: banner reports 4.67"
        ;;
    *)
        echo "FAIL: banner did not report 4.67" >&2
        exit 1
        ;;
esac

# info() also prints the svn revisions; requiring them keeps this from passing
# on a stubbed-out banner that happens to contain the version string.
case "$VERSION_OUT" in
    *"tucnak svn version:"*)
        echo "PASS: svn revision line present"
        ;;
    *)
        echo "FAIL: info banner is missing the svn revision line" >&2
        exit 1
        ;;
esac

echo "All tucnak tests passed."
