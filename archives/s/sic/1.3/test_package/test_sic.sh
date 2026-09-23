#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for sic 1.3 (installed bin/sic).
#
# Really runs the installed binary:
#   * version banner and usage/error paths;
#   * a full IRC registration handshake against a local TCP server, checking
#     that sic sends NICK/USER and answers the server PING with PONG.
#
# Env: SIC_BIN = path to the installed sic executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

BIN="${SIC_BIN:-sic}"
HERE=$(dirname "$0")
WORK="${TMPDIR:-.}/sic-consumer.$$"
umask 000
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
SRV=""
trap 'rm -rf "$WORK"; [ -n "$SRV" ] && kill "$SRV" 2>/dev/null || true' EXIT

checks=0
fails=0
check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

# 1. version banner (sic -v prints via eprint -> stderr and exits 1 by design)
got=$( ("$BIN" -v 2>&1 || true) | head -n 1 )
case "$got" in
	sic-1.3,*) res=ok ;;
	*)         res=bad ;;
esac
check "sic -v reports version 1.3" "$res" "ok"

# 2. usage on an unknown option
got=$( ("$BIN" -Z 2>&1 || true) | head -n 1 )
case "$got" in
	"usage: sic "*) res=ok ;;
	*)              res=bad ;;
esac
check "sic prints usage on an unknown option" "$res" "ok"

# 3. connection error path (nothing listens on 127.0.0.1:1)
got=$( ("$BIN" -h 127.0.0.1 -p 1 2>&1 || true) | head -n 1 )
case "$got" in
	*"cannot connect to host"*) res=ok ;;
	*)                          res=bad ;;
esac
check "sic reports a failed connection" "$res" "ok"

# 4-6. IRC registration handshake against a local server
PORT=$(( ($$ % 15000) + 41000 ))
python3 "$HERE/sic_ircsrv.py" "$PORT" "$WORK/capture.bin" &
SRV=$!
sleep 1
# keep stdin open (sleep) so sic can read the server's PING and answer it
sleep 5 | timeout 20 "$BIN" -h 127.0.0.1 -p "$PORT" -n consumertest \
	> "$WORK/sic.out" 2>&1 || true
wait "$SRV" 2>/dev/null || true
SRV=""

capture=$(cat "$WORK/capture.bin" 2>/dev/null || true)
case "$capture" in
	*"NICK consumertest"*) res=ok ;;
	*)                     res=bad ;;
esac
check "sic sends its NICK on connect" "$res" "ok"

case "$capture" in
	*"USER consumertest"*) res=ok ;;
	*)                     res=bad ;;
esac
check "sic sends its USER on connect" "$res" "ok"

case "$capture" in
	*PONG*) res=ok ;;
	*)      res=bad ;;
esac
check "sic answers the server PING with PONG" "$res" "ok"

echo "SIC_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
