#!/bin/sh
set -eu
B="${1?"Usage: $0 <nerdfetch-path>"}"
P=0; F=0
echo "[test] exists"; [ -f "$B" ] && P=$((P+1)) || { echo FAIL; exit 1; }
echo "[test] sh -n"; sh -n "$B" && P=$((P+1)) || F=$((F+1))
echo "[test] output"; O=$(sh "$B" -e 2>&1) || true; [ -n "$O" ] && P=$((P+1)) || F=$((F+1))
echo "[test] exit 0"; sh "$B" -e >/dev/null 2>&1 && P=$((P+1)) || F=$((F+1))
U=${USER:-$(whoami 2>/dev/null || echo unknown)}
case "$O" in
    *"$U"*) P=$((P+1)) ;;
    *) echo "FAIL: output does not contain current user '$U'"; F=$((F+1)) ;;
esac
echo "--- $P passed, $F failed ---"
[ "$F" -gt 0 ] && exit 1
exit 0
