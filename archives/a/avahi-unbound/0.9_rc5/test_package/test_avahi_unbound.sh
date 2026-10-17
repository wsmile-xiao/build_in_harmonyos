#!/usr/bin/env zsh
# test_avahi_unbound.sh — Verify avahi-unbound config file content
# Run by test_package/conanfile.py test() method.
# Argument 1: package folder path
set -euo pipefail

PKG_DIR="${1:?Usage: test_avahi_unbound.sh <package_folder>}"
CONFIG_FILE="$PKG_DIR/etc/unbound/unbound.conf.d/avahi.conf"

PASS=0
FAIL=0

# ── Test 1: Config file exists at expected path ──
if [ -f "$CONFIG_FILE" ]; then
        echo "        [ok] Config file exists at etc/unbound/unbound.conf.d/avahi.conf"
        PASS=$((PASS + 1))
else
        echo "        [fail] Config file not found at $CONFIG_FILE"
        FAIL=$((FAIL + 1))
fi

# ── Test 2: Contains forward-zone section ──
if grep -q '^forward-zone:' "$CONFIG_FILE" 2>/dev/null; then
        echo "        [ok] forward-zone section present"
        PASS=$((PASS + 1))
else
        echo "        [fail] forward-zone section missing"
        FAIL=$((FAIL + 1))
fi

# ── Test 3: Forward zone name is "local" ──
if grep -q 'name: "local"' "$CONFIG_FILE" 2>/dev/null; then
        echo '        [ok] forward-zone name is "local"'
        PASS=$((PASS + 1))
else
        echo '        [fail] forward-zone name is not "local"'
        FAIL=$((FAIL + 1))
fi

# ── Test 4: Forward address is 127.0.0.1@5354 (avahi DNS proxy port) ──
if grep -q 'forward-addr: 127.0.0.1@5354' "$CONFIG_FILE" 2>/dev/null; then
        echo "        [ok] forward-addr is 127.0.0.1@5354 (avahi DNS proxy)"
        PASS=$((PASS + 1))
else
        echo "        [fail] forward-addr is not 127.0.0.1@5354"
        FAIL=$((FAIL + 1))
fi

# ── Test 5: Contains server section ──
if grep -q '^server:' "$CONFIG_FILE" 2>/dev/null; then
        echo "        [ok] server section present"
        PASS=$((PASS + 1))
else
        echo "        [fail] server section missing"
        FAIL=$((FAIL + 1))
fi

# ── Test 6: do-not-query-localhost is set to no (allow forwarding to localhost) ──
if grep -q 'do-not-query-localhost: no' "$CONFIG_FILE" 2>/dev/null; then
        echo "        [ok] do-not-query-localhost is no"
        PASS=$((PASS + 1))
else
        echo "        [fail] do-not-query-localhost is not no"
        FAIL=$((FAIL + 1))
fi

# ── Test 7: domain-insecure is set to "local" (no DNSSEC for mDNS) ──
if grep -q 'domain-insecure: "local"' "$CONFIG_FILE" 2>/dev/null; then
        echo '        [ok] domain-insecure is "local"'
        PASS=$((PASS + 1))
else
        echo '        [fail] domain-insecure is not "local"'
        FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"

if [ "$FAIL" -gt 0 ]; then
        exit 1
fi
