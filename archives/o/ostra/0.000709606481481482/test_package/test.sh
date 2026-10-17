#!/usr/bin/env sh
set -eu

command -v ostra-sysctl >/dev/null 2>&1

human_output="$(ostra-sysctl)"
case "$human_output" in
  *"Ostra System Status"*) ;;
  *)
    echo "missing human-readable header"
    exit 1
    ;;
esac

tmpdir="${TMPDIR:-${HOME}/tmp}"
mkdir -p "$tmpdir"
json_file="$tmpdir/ostra-sysctl-$$.json"
trap 'rm -f "$json_file"' EXIT

ostra-sysctl --help >/dev/null
ostra-sysctl --json > "$json_file"

python3 - "$json_file" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text())

required_fields = {
    "hostname",
    "kernel",
    "cpu_usage_percent",
    "memory_total_bytes",
    "memory_used_bytes",
    "swap_total_bytes",
    "swap_used_bytes",
    "root_total_bytes",
    "root_used_bytes",
    "data_disk_available",
    "data_total_bytes",
    "data_used_bytes",
    "load_1m",
    "load_5m",
    "load_15m",
    "uptime_seconds",
    "temperature_c",
}

missing = required_fields - payload.keys()
if missing:
    raise SystemExit(f"Missing JSON fields: {sorted(missing)}")

if not payload["hostname"]:
    raise SystemExit("Hostname is empty")

if not 0.0 <= float(payload["cpu_usage_percent"]) <= 100.0:
    raise SystemExit("CPU usage is outside the valid range")

if payload["memory_used_bytes"] > payload["memory_total_bytes"]:
    raise SystemExit("Memory usage exceeds total memory")

if payload["root_used_bytes"] > payload["root_total_bytes"]:
    raise SystemExit("Root usage exceeds total capacity")

if payload["data_disk_available"]:
    if payload["data_total_bytes"] <= 0:
        raise SystemExit("Ostra data capacity is invalid")

    if payload["data_used_bytes"] > payload["data_total_bytes"]:
        raise SystemExit("Ostra data usage exceeds capacity")

print("JSON validation: PASSED")
PY
