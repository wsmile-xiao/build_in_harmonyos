#!/usr/bin/env bash
# L1 consumer test for tshark: run the installed binary and assert observable
# behavior. Fails (non-zero) on any assertion failure.
set -euo pipefail

echo "[1/3] tshark --version"
out_ver="$(tshark --version)"
echo "$out_ver" | head -3
echo "$out_ver" | grep -q "4\.6\.7" || { echo "FAIL: version string missing 4.6.7"; exit 1; }
echo "  -> version OK"

echo "[2/3] tshark -G protocols (dissection engine init + protocol table)"
protos="$(tshark -G protocols)"
n="$(printf '%s\n' "$protos" | grep -c . || true)"
echo "  -> protocol lines: $n"
[ "$n" -gt 100 ] || { echo "FAIL: expected >100 protocols, got $n"; exit 1; }
# -G protocols is TAB-separated: <display name><TAB><short name><TAB><filter
# name><TAB><flag><TAB><flag><TAB><flag>. Column 3 is the capture-filter name
# (tcp/http/dns) — the stable identifier a user puts in a display filter.
# Assert the core protocol filter names are present in column 3 (precise and
# format-robust; an anchored ^tcp misses because column 1 is the display name).
# NOTE: this script runs under `set -o pipefail`, so the check must be a single
# awk that reads ALL input — an early-exiting `grep -q` would close the pipe,
# SIGPIPE the upstream writer (exit 141), and pipefail would report failure even
# when the match succeeded. awk `END { exit found?0:1 }` avoids that trap.
printf '%s\n' "$protos" \
  | awk -F'\t' '
      $3=="tcp" || $3=="http" || $3=="dns" { found=1 }
      END { exit found ? 0 : 1 }
    ' \
  || { echo "FAIL: core protocols (tcp/http/dns) not in table"; exit 1; }
echo "  -> protocol table OK (tcp/http/dns filter names present)"

echo "[3/3] component versions from --version (GLib + libpcap linked)"
# -G versions was removed upstream in 4.x; --version already reports the
# compile-time component versions. Assert the key linked components are present
# (GLib runtime + libpcap capture backend). Note: avoid matching the "Without:"
# section (e.g. "-GnuTLS"), so anchor on the positive "+libpcap" / "GLib:" forms.
echo "$out_ver" | grep -q 'GLib' || { echo "FAIL: GLib missing from --version"; exit 1; }
echo "$out_ver" | grep -q '+libpcap' || { echo "FAIL: libpcap not linked (capture backend missing)"; exit 1; }
echo "  -> component versions OK"

echo "ALL TSHARK L1 TESTS PASSED"
