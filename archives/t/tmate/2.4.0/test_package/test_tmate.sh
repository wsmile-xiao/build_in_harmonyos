#!/data/service/hnp/bin/bash
# test_package/test_tmate.sh — real smoke test for the packaged tmate binary.
#
# Requirements:
#   - MUST actually execute the packaged `tmate -V` and STRICTLY assert that the
#     output is exactly `tmate 2.4.0` (L0c: no fake/empty/echo-only tests).
#   - Runs under the Conan run environment (env="conanrun"), which provides the
#     runtime LD_LIBRARY_PATH for dependency shared libraries (libevent.so).
set -eu

expected="tmate 2.4.0"

# Resolve the installed binary: prefer explicit path, then PATH lookup.
binary="${TMATE_BIN:-}"
if [ -z "$binary" ]; then
    if ! command -v tmate >/dev/null 2>&1; then
        echo "❌ tmate binary not found on PATH" >&2
        exit 1
    fi
    binary="$(command -v tmate)"
fi

if [ ! -x "$binary" ]; then
    echo "❌ tmate binary not executable: $binary" >&2
    exit 1
fi
echo "[test] binary=$binary"

# Capture stdout+stderr and exit code of the real binary invocation.
output="$( "$binary" -V 2>&1 )" || {
    echo "❌ tmate -V failed (rc=$?)" >&2
    echo "output: $output" >&2
    exit 1
}
echo "[test] tmate -V output: [$output]"

if [ "$output" != "$expected" ]; then
    echo "❌ version mismatch: expected exactly '$expected', got '$output'" >&2
    exit 1
fi

echo "✅ TMATE_VERSION_OK=$output"
