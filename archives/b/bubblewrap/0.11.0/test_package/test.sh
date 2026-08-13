#!/bin/sh
# Upstream-binary smoke test for bubblewrap (bwrap).
# Called by test_package/conanfile.py via the package bin dir.
# Verifies bwrap runs and prints the expected version.
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "usage: $0 /path/to/bwrap" >&2
    exit 2
fi

BWRAP="$1"

if [ ! -x "$BWRAP" ]; then
    echo "bwrap binary not found: $BWRAP" >&2
    exit 1
fi

VERSION_OUT="$("$BWRAP" --version 2>&1)" || {
    echo "bwrap --version failed: $VERSION_OUT" >&2
    exit 1
}
echo "bwrap --version -> $VERSION_OUT"
case "$VERSION_OUT" in
    bubblewrap*0.11.0*) ;;
    *)
        echo "unexpected version output: $VERSION_OUT" >&2
        exit 1
        ;;
esac

# --help: exit 0/1 is normal (sandbox capabilities unavailable on OHOS);
# only a crash (rc > 1) is a failure. Capture the exit code via `||`
# short-circuit so set -e does not abort the script on non-zero.
rc=0
"$BWRAP" --help > /dev/null 2>&1 || rc=$?
if [ "$rc" -gt 1 ]; then
    echo "bwrap --help crashed (exit $rc)" >&2
    exit 1
fi
echo "bwrap --help: OK"
exit 0
