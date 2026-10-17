#!/bin/sh
# Run consumer checks against the xpar binary from the Conan package.
set -euo pipefail

BIN=${1:-}
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "xpar test: packaged executable missing: $BIN" >&2
    exit 1
fi

PASSED=0
FAILED=0
pass() {
    PASSED=$((PASSED + 1))
    echo "PASS: $1"
}
fail() {
    FAILED=$((FAILED + 1))
    echo "FAIL: $1" >&2
}

TMP_ROOT=${TMPDIR:-${HOME:-.}/tmp}
mkdir -p "$TMP_ROOT" || exit 1
WORK=$(mktemp -d "$TMP_ROOT/xpar-test.XXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

if version_output=$("$BIN" -V 2>&1) && printf '%s' "$version_output" | grep -q '1\.1'; then
    pass 'packaged binary reports version 1.1'
else
    fail 'packaged binary reports version 1.1'
fi

if ! python3 - "$WORK/input.bin" <<'PY'
import sys
with open(sys.argv[1], "wb") as f:
    f.write((b"xpar 1.1 package round trip\n" * 512) + bytes(range(256)))
PY
then
    echo 'xpar test: failed to create input fixture' >&2
    exit 2
fi

if "$BIN" -Jef "$WORK/input.bin" >"$WORK/joint-encode.log" 2>&1 \
        && [ -s "$WORK/input.bin.xpa" ]; then
    pass 'joint mode creates a parity archive'
else
    cat "$WORK/joint-encode.log" >&2
    fail 'joint mode creates a parity archive'
fi

if "$BIN" -Jdf "$WORK/input.bin.xpa" "$WORK/joint.out" >/dev/null 2>&1 \
        && cmp -s "$WORK/input.bin" "$WORK/joint.out"; then
    pass 'joint mode decodes the original bytes'
else
    fail 'joint mode decodes the original bytes'
fi

if "$BIN" -Jtf "$WORK/input.bin.xpa" >/dev/null 2>&1; then
    pass 'integrity check accepts an intact archive'
else
    fail 'integrity check accepts an intact archive'
fi

if "$BIN" -Jsef "$WORK/input.bin" >/dev/null 2>&1 && [ -s "$WORK/input.bin.xpa" ]; then
    pass 'systematic mode creates a parity-only sidecar'
else
    fail 'systematic mode creates a parity-only sidecar'
fi

if ! cp "$WORK/input.bin" "$WORK/corrupt.bin"; then
    echo 'xpar test: failed to copy corruption fixture' >&2
    exit 2
fi
if ! python3 - "$WORK/corrupt.bin" <<'PY'
import sys
with open(sys.argv[1], "r+b") as f:
    f.seek(100)
    original = f.read(10)
    f.seek(100)
    f.write(bytes(value ^ 0xA5 for value in original))
PY
then
    echo 'xpar test: failed to corrupt the input fixture' >&2
    exit 2
fi
if "$BIN" -Jsdf "$WORK/corrupt.bin" "$WORK/input.bin.xpa" >"$WORK/recovered.out" 2>"$WORK/recovery.err" \
        && cmp -s "$WORK/input.bin" "$WORK/recovered.out"; then
    pass 'systematic mode repairs damaged user data from its sidecar'
else
    fail 'systematic mode repairs damaged user data from its sidecar'
fi

if ! python3 - "$WORK/input.bin.xpa" "$WORK/truncated.xpa" <<'PY'
import sys
with open(sys.argv[1], "rb") as source, open(sys.argv[2], "wb") as target:
    target.write(source.read(8))
PY
then
    echo 'xpar test: failed to create truncated archive fixture' >&2
    exit 2
fi
if "$BIN" -Jdf "$WORK/truncated.xpa" "$WORK/should-not-exist" >/dev/null 2>&1; then
    fail 'decoder rejects a truncated archive'
else
    pass 'decoder rejects a truncated archive'
fi

if system_name=$(uname -s 2>/dev/null); then
    :
else
    system_name='unknown'
fi
if [ "$system_name" = 'HarmonyOS' ]; then
    case "$WORK/" in
        "${HOME%/}/tmp/"*)
            mkdir -p "$HOME/tmp/xpar HarmonyOS"
            HARMONY_INPUT="$HOME/tmp/xpar HarmonyOS/鸿蒙 文件.bin"
            HARMONY_ARCHIVE="$HARMONY_INPUT.xpa"
            HARMONY_OUTPUT="$HOME/tmp/xpar HarmonyOS/恢复 文件.bin"
            if ! python3 - "$HARMONY_INPUT" <<'PY'
import sys
with open(sys.argv[1], "wb") as f:
    f.write("HarmonyOS 用户目录读写验证\n".encode("utf-8") * 128)
PY
            then
                echo 'xpar test: failed to create HarmonyOS fixture' >&2
                exit 2
            fi
            if "$BIN" -Jef "$HARMONY_INPUT" >/dev/null 2>&1 \
                    && "$BIN" -Jdf "$HARMONY_ARCHIVE" "$HARMONY_OUTPUT" >/dev/null 2>&1 \
                    && cmp -s "$HARMONY_INPUT" "$HARMONY_OUTPUT"; then
                pass 'HarmonyOS user storage round-trip supports Unicode and spaces'
                echo 'HMBS_HARMONYOS_TEST=PASS: HarmonyOS user storage round-trip'
            else
                fail 'HarmonyOS user storage round-trip supports Unicode and spaces'
                echo 'HMBS_HARMONYOS_TEST=FAIL: HarmonyOS user storage round-trip'
            fi
            rm -f "$HARMONY_INPUT" "$HARMONY_ARCHIVE" "$HARMONY_OUTPUT"
            rmdir "$HOME/tmp/xpar HarmonyOS" 2>/dev/null || true  # Keep non-empty directories if unrelated files remain.
            ;;
        *)
            fail 'HarmonyOS test directory is under writable HOME/tmp'
            echo "HMBS_HARMONYOS_TEST=FAIL: unexpected temporary directory $WORK" >&2
            ;;
    esac
fi

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
