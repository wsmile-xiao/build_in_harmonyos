#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for exim (R34).
# Runs in conanrun env (PATH includes installed bin/).
# Note: exim prints version then exits non-zero when no config file exists
# (it reports "non-existent configuration file(s)"). That is expected here;
# we tolerate non-zero from --version and only inspect its stdout.
set -u

# Use a writable temp dir (OHOS /tmp is read-only).
WORKDIR="${TMPDIR:-/data/data/__tmp}"
[ -d "$WORKDIR" ] || WORKDIR="$(pwd)"
out="$WORKDIR/exim_bV.out"; err="$WORKDIR/exim_bV.err"

echo "[test] exim --version"
exim --version || true
version_line=$(exim --version 2>/dev/null | head -1 || true)
echo "[test] version line: $version_line"
case "$version_line" in
  *"Exim version 4.99.5"*) echo "✅ version 4.99.5 OK" ;;
  *) echo "❌ unexpected version: $version_line"; exit 1 ;;
esac

echo "[test] exim -bV (compiled-in configuration)"
exim -bV >"$out" 2>"$err" || true
config_dump=$(cat "$out" "$err" 2>/dev/null)
echo "$config_dump" | head -20

echo "[test] assert key build features"
echo "$config_dump" | grep -q "OpenSSL" || { echo "❌ missing OpenSSL TLS"; exit 1; }
echo "$config_dump" | grep -q "Berkeley DB" || { echo "❌ missing Berkeley DB"; exit 1; }
echo "$config_dump" | grep -q "DANE" || { echo "❌ missing DANE support"; exit 1; }
echo "✅ OpenSSL TLS + Berkeley DB + DANE present"

echo "[test] assert built-in transports/routers"
echo "$config_dump" | grep -q "Transports (built-in):.*smtp" || { echo "❌ missing smtp transport"; exit 1; }
echo "$config_dump" | grep -q "Routers (built-in):.*dnslookup" || { echo "❌ missing dnslookup router"; exit 1; }
echo "✅ transports/routers present"

echo "✅ all exim functional tests passed"
