#!/usr/bin/env bash
# R34: real smoke test for abcde 2.9.3 — exercises the packaged artifact.
# abcde is a bash script (uses =~ regex), so we verify presence, executable
# bit, shebang and bash syntax instead of a C build/test cycle.
set -u

BIN_DIR="${1:?usage: test_abcde.sh <package bin dir>}"

FAIL=0

for f in abcde cddb-tool abcde-musicbrainz-tool; do
    if [ ! -x "$BIN_DIR/$f" ]; then
        echo "FAIL: $f missing or not executable in $BIN_DIR"
        FAIL=1
    fi
done

ABCDE="$BIN_DIR/abcde"
if [ -f "$ABCDE" ]; then
    SHEBANG=$(head -1 "$ABCDE")
    if [[ "$SHEBANG" != *bash* ]]; then
        echo "FAIL: unexpected shebang: $SHEBANG"
        FAIL=1
    fi
    if ! bash -n "$ABCDE"; then
        echo "FAIL: abcde bash syntax check failed"
        FAIL=1
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "abcde smoke test: OK"
fi
exit "$FAIL"
