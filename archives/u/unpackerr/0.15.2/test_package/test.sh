#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-unpackerr>" >&2
    exit 2
fi

unpackerr_bin="$1"

if [ ! -f "$unpackerr_bin" ]; then
    echo "unpackerr binary not found: $unpackerr_bin" >&2
    exit 1
fi

echo "[step] Testing 'unpackerr --version'..."
version_output="$("$unpackerr_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "unpackerr" >/dev/null
printf '%s\n' "$version_output" | grep -F "0.15.2" >/dev/null
echo "        [ok] version check passed (unpackerr 0.15.2 embedded via golift.io/version ldflags)"

echo "[step] Testing 'unpackerr --help'..."
"$unpackerr_bin" --help >/dev/null 2>&1
echo "        [ok] help check passed"

echo "[step] Testing config-parse + daemon startup with a minimal TOML config..."
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
cat > "$tmpdir/unpackerr.conf" <<'EOF'
debug = true
quiet = false
interval = "2m"
start_delay = "1s"
EOF
# The daemon runs forever; start it, verify the startup log line, then stop it.
"$unpackerr_bin" -c "$tmpdir/unpackerr.conf" >"$tmpdir/startup.log" 2>&1 &
pid=$!
sleep 4
kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
cat "$tmpdir/startup.log"
grep -F "Starting!" "$tmpdir/startup.log" >/dev/null
echo "        [ok] daemon startup check passed (config parsed, 'Starting!' log emitted)"

echo "[ok] All tests passed."
