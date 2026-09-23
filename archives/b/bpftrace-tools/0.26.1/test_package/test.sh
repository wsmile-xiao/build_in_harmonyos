#!/usr/bin/env bash
set -euo pipefail

TOOLS_DIR="${1:-}"
if [ -z "$TOOLS_DIR" ]; then
  echo "[FAIL] TOOLS_DIR not provided"
  exit 1
fi

echo "[test] bpftrace-tools smoke test"
echo "[test] tools dir: $TOOLS_DIR"

if [ ! -d "$TOOLS_DIR" ]; then
  echo "[FAIL] tools dir missing: $TOOLS_DIR"
  exit 1
fi

# Count .bt files (excluding old)
count=$(find "$TOOLS_DIR" -maxdepth 1 -name "*.bt" | wc -l)
old_count=$(find "$TOOLS_DIR/old" -name "*.bt" 2>/dev/null | wc -l || echo 0)
echo "[test] discovered .bt in top: $count, old: $old_count"
if [ "$count" -lt 30 ]; then
  echo "[FAIL] too few tools: $count (<30)"
  exit 1
fi

# Check core tools existence
for f in opensnoop.bt execsnoop.bt biolatency.bt biosnoop.bt tcpconnect.bt; do
  if [ ! -f "$TOOLS_DIR/$f" ]; then
    echo "[FAIL] missing core tool: $f"
    exit 1
  fi
  echo "[test] found $f"
done

# Check README
if [ ! -f "$TOOLS_DIR/README.md" ]; then
  echo "[FAIL] README.md missing"
  exit 1
fi

# Verify probe syntax in representative tools (must contain bpftrace probe definitions)
check_probe() {
  local file="$1"
  local pattern="$2"
  if ! grep -qE "$pattern" "$file"; then
    echo "[FAIL] probe pattern not found in $file: $pattern"
    exit 1
  fi
}

check_probe "$TOOLS_DIR/opensnoop.bt" "tracepoint:syscalls:sys_enter_open|kprobe:"
check_probe "$TOOLS_DIR/execsnoop.bt" "tracepoint:syscalls:sys_enter_exec"
check_probe "$TOOLS_DIR/biolatency.bt" "kprobe:|tracepoint:block:"

echo "[test] probe syntax checks passed"

# Ensure tools are non-empty and not containing empty file edge case (toybox pitfall)
empty_found=0
for f in "$TOOLS_DIR"/*.bt; do
  if [ ! -s "$f" ]; then
    echo "[FAIL] empty tool file: $f"
    empty_found=1
  fi
done
if [ "$empty_found" -ne 0 ]; then
  exit 1
fi
echo "[test] non-empty check passed"

echo "[PASS] bpftrace-tools test_package passed: $count tools verified"
