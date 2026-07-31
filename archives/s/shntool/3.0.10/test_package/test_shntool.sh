#!/bin/bash
# Verify the packaged shntool binary and generated mode aliases.

set -euo pipefail

SHNTOOL_BIN="${1:-}"

if [ -z "$SHNTOOL_BIN" ]; then
    echo "ERROR: shntool binary path is required"
    exit 1
fi

if [ ! -x "$SHNTOOL_BIN" ]; then
    echo "ERROR: $SHNTOOL_BIN not found or not executable"
    exit 1
fi

pkg_root="$(CDPATH= cd -- "$(dirname -- "$SHNTOOL_BIN")/.." && pwd)"

run_capture() {
    local output_file status_file pid watchdog status
    output_file="${TMPDIR:-/tmp}/shntool-test-output-$$-$RANDOM"
    status_file="${TMPDIR:-/tmp}/shntool-test-status-$$-$RANDOM"
    (
        "$@" </dev/null >"$output_file" 2>&1
        printf "%s" "$?" >"$status_file"
    ) &
    pid=$!
    (
        sleep 20
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
            printf "124" >"$status_file"
        fi
    ) &
    watchdog=$!

    wait "$pid" 2>/dev/null || true
    kill "$watchdog" 2>/dev/null || true
    wait "$watchdog" 2>/dev/null || true

    if [ -f "$status_file" ]; then
        status="$(cat "$status_file")"
    else
        status=125
    fi
    cat "$output_file" 2>/dev/null || true
    rm -f "$output_file" "$status_file"
    return "$status"
}

version_output="$(run_capture "$SHNTOOL_BIN" -v || true)"
case "$version_output" in
    *"shntool 3.0.10"*)
        printf "%s\n" "$version_output"
        ;;
    *)
        echo "ERROR: unexpected shntool version output"
        printf "%s\n" "$version_output"
        exit 1
        ;;
esac

mode_output="$(run_capture "$SHNTOOL_BIN" -m || true)"
case "$mode_output" in
    *"len"*split*|*"split"*len*)
        ;;
    *)
        echo "ERROR: expected len and split modes"
        printf "%s\n" "$mode_output"
        exit 1
        ;;
esac

format_output="$(run_capture "$SHNTOOL_BIN" -f || true)"
case "$format_output" in
    *"wav"*)
        ;;
    *)
        echo "ERROR: expected wav format"
        printf "%s\n" "$format_output"
        exit 1
        ;;
esac

if [ ! -x "$pkg_root/bin/shnlen" ]; then
    echo "ERROR: shnlen alias was not installed or not executable"
    exit 1
fi

set +e
shnlen_no_input_output=$(run_capture "$pkg_root/bin/shnlen")
shnlen_no_input_status=$?
set -e

if [ "$shnlen_no_input_status" -eq 124 ]; then
    echo "ERROR: shnlen without input timed out"
    printf "%s\n" "$shnlen_no_input_output"
    exit 1
fi

if [ "$shnlen_no_input_status" -ne 0 ]; then
    echo "ERROR: shnlen without input failed with status $shnlen_no_input_status"
    printf "%s\n" "$shnlen_no_input_output"
    exit 1
fi

case "$shnlen_no_input_output" in
    *"(0 files)"*)
        ;;
    *)
        echo "ERROR: shnlen empty-input summary is missing"
        printf "%s\n" "$shnlen_no_input_output"
        exit 1
        ;;
esac

set +e
shnlen_output=$(run_capture "$pkg_root/bin/shnlen" -h)
shnlen_status=$?
set -e

if [ "$shnlen_status" -eq 124 ]; then
    echo "ERROR: shnlen help timed out"
    printf "%s\n" "$shnlen_output"
    exit 1
fi

if [ "$shnlen_status" -gt 1 ]; then
    echo "ERROR: shnlen help failed with status $shnlen_status"
    printf "%s\n" "$shnlen_output"
    exit 1
fi

case "$shnlen_output" in
    *"shntool"*|*"Usage"*|*"usage"*)
        ;;
    *)
        echo "ERROR: shnlen help output is missing"
        printf "%s\n" "$shnlen_output"
        exit 1
        ;;
esac

echo "PASS: shntool version, modes, formats, and shnlen alias behavior are valid"
