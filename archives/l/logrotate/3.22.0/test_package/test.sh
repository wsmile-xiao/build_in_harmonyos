#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the logrotate binary.
# Runs in conanrun env (PATH includes the installed sbin/).
#
# This is a real behavioural test (R34): it drives logrotate through a full
# rotation cycle and asserts the rotated file is produced — not a print-only stub.
set -euo pipefail

echo "[test] logrotate --version"
logrotate --version

# Isolated working area under the (writable) build dir — never /tmp (OHOS E002).
WORK="$PWD/lr_work"
rm -rf "$WORK"
mkdir -p "$WORK"

LOG="$WORK/test.log"
CONF="$WORK/logrotate.conf"
STATE="$WORK/state"

printf 'line1\nline2\nline3\n' > "$LOG"

cat > "$CONF" <<EOF
"$LOG" {
    rotate 3
    missingok
    notifempty
    nocompress
}
EOF
chmod 644 "$CONF"

echo "[test] forcing a rotation"
logrotate -f -s "$STATE" "$CONF"

if [ -f "$LOG.1" ]; then
    echo "✅ rotation produced $LOG.1"
else
    echo "❌ expected rotated file $LOG.1 was not created"
    ls -la "$WORK"
    exit 1
fi
