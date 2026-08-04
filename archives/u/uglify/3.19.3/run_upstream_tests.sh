#!/usr/bin/env bash
set -euo pipefail

command -v node >/dev/null 2>&1 || {
    echo "UglifyJS tests require Node.js in PATH" >&2
    exit 1
}

jobs="${UGLIFY_TEST_JOBS:-4}"
case "$jobs" in
    ''|*[!0-9]*)
        echo "UGLIFY_TEST_JOBS must be a positive integer" >&2
        exit 1
        ;;
esac
if [ "$jobs" -lt 1 ]; then
    echo "UGLIFY_TEST_JOBS must be at least 1" >&2
    exit 1
fi

log_root="${UGLIFY_TEST_TMPDIR:?UGLIFY_TEST_TMPDIR is required}"
run_logs="$log_root/run-$$"
mkdir -p "$run_logs"

compress_files=(test/compress/*.js)
if [ ! -e "${compress_files[0]}" ]; then
    echo "No compression fixtures found" >&2
    exit 1
fi

batch_pids=()
batch_logs=()
batch_files=()
compress_failed=0
compress_passed=0

wait_batch() {
    local index
    local failed=0
    for index in "${!batch_pids[@]}"; do
        if wait "${batch_pids[$index]}"; then
            compress_passed=$((compress_passed + 1))
        else
            echo "Compression fixture failed: ${batch_files[$index]}" >&2
            failed=1
        fi
        cat "${batch_logs[$index]}"
    done
    return "$failed"
}

for fixture_path in "${compress_files[@]}"; do
    fixture="${fixture_path##*/}"
    fixture_log="$run_logs/${fixture%.js}.log"
    node test/compress.js "$fixture" >"$fixture_log" 2>&1 &
    batch_pids+=("$!")
    batch_logs+=("$fixture_log")
    batch_files+=("$fixture")

    if [ "${#batch_pids[@]}" -ge "$jobs" ]; then
        if ! wait_batch; then
            compress_failed=1
        fi
        batch_pids=()
        batch_logs=()
        batch_files=()
    fi
done

if [ "${#batch_pids[@]}" -gt 0 ]; then
    if ! wait_batch; then
        compress_failed=1
    fi
fi

printf 'Compression fixture files passed: %d/%d\n' \
    "$compress_passed" "${#compress_files[@]}"
if [ "$compress_failed" -ne 0 ]; then
    exit 1
fi

node test/mocha.js
