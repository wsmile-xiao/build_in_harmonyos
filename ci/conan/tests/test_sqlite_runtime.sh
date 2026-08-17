#!/usr/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../sqlite_runtime.sh"

TEST_TMP_ROOT="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TEST_TMP_ROOT"
TEST_ROOT=$(mktemp -d "$TEST_TMP_ROOT/sqlite-runtime-test.XXXXXX")
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
    echo "[fail] $1"
    exit 1
}

assert_equal() {
    local expected="$1"
    local actual="$2"
    local message="$3"
    [ "$actual" = "$expected" ] || fail "$message: expected '$expected', got '$actual'"
}

python3() {
    if [ "${FAKE_PYTHON_HEALTHY:-0}" = "1" ]; then
        return 0
    fi

    local first_library_dir="${LD_LIBRARY_PATH:-}"
    first_library_dir="${first_library_dir%%:*}"
    [ -n "$first_library_dir" ] && [ -e "$first_library_dir/libsqlite3.so.0" ]
}

export CI_PYTHON3_BIN=python3

# A healthy Python must leave the caller's environment untouched.
export FAKE_PYTHON_HEALTHY=1
export LD_LIBRARY_PATH="$TEST_ROOT/existing"
unset CI_SQLITE_SEARCH_DIR CI_SQLITE_SHIM_ROOT
ensure_python_sqlite_runtime
assert_equal "$TEST_ROOT/existing" "$LD_LIBRARY_PATH" "healthy Python changed LD_LIBRARY_PATH"

# An exact SONAME can be used from its original directory.
export FAKE_PYTHON_HEALTHY=0
local_exact_dir="$TEST_ROOT/exact"
mkdir -p "$local_exact_dir"
touch "$local_exact_dir/libsqlite3.so.0"
export CI_SQLITE_SEARCH_DIR="$local_exact_dir"
export CI_SQLITE_SHIM_ROOT="$TEST_ROOT/exact-shims"
unset LD_LIBRARY_PATH
ensure_python_sqlite_runtime
assert_equal "$local_exact_dir" "$LD_LIBRARY_PATH" "exact sqlite SONAME was not used directly"

# A second call models another consumer in the same step and must be idempotent.
local_first_path="$LD_LIBRARY_PATH"
ensure_python_sqlite_runtime
assert_equal "$local_first_path" "$LD_LIBRARY_PATH" "runtime recovery is not idempotent"

# HarmonyOS libsqlite.z.so needs a libsqlite3.so.0 compatibility runtime.
local_ohos_dir="$TEST_ROOT/ohos"
mkdir -p "$local_ohos_dir"
print -r -- "sqlite-runtime-marker" > "$local_ohos_dir/libsqlite.z.so"
export CI_SQLITE_SEARCH_DIR="$local_ohos_dir"
export CI_SQLITE_SHIM_ROOT="$TEST_ROOT/ohos-shims"
unset LD_LIBRARY_PATH
ensure_python_sqlite_runtime

local_shim_dir="${LD_LIBRARY_PATH%%:*}"
local_shim="$local_shim_dir/libsqlite3.so.0"
[ -e "$local_shim" ] || fail "compatibility runtime was not created"
local_payload=$(< "$local_shim")
assert_equal "sqlite-runtime-marker" "$local_payload" "compatibility runtime has the wrong content"
echo "[ok] sqlite runtime recovery tests passed"
