#!/bin/bash
# Smoke test for acpitool CLI
# HarmonyOS PC lacks /proc/acpi and /sys/bus/acpi, so acpitool -h
# exits with code 255 but prints help text. This is expected.
set -euo pipefail

# Run acpitool -h, capture output and exit code
# Use set +e to capture exit code without || true swallowing it
set +e
output=$(acpitool -h 2>&1)
exit_code=$?
set -e

# Check that help text was printed (non-empty output)
if [ -z "$output" ]; then
    echo "FAIL: acpitool -h produced no output" >&2
    exit 1
fi

# Accept exit 0 (success) or 255 (ACPI missing on HarmonyOS) as valid
if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 255 ]; then
    echo "FAIL: acpitool -h exited with unexpected code $exit_code" >&2
    echo "Output: $output" >&2
    exit 1
fi

echo "PASS: acpitool -h (exit=$exit_code)"
echo "$output" | head -5