#!/usr/bin/env bash
set -euo pipefail

test -x "$RSBACKUP_BIN"
test -x "$RSYNC_BIN"
mkdir -p "$RSBACKUP_TEST_DIR/source" "$RSBACKUP_TEST_DIR/store" "$RSBACKUP_TEST_DIR/logs"
printf 'HarmonyOS rsbackup integration\n' > "$RSBACKUP_TEST_DIR/source/payload.txt"
printf 'device1\n' > "$RSBACKUP_TEST_DIR/store/device-id"

cat > "$RSBACKUP_TEST_DIR/config" <<EOF
store --no-mounted $RSBACKUP_TEST_DIR/store
device device1
public true
logs $RSBACKUP_TEST_DIR/logs
lock $RSBACKUP_TEST_DIR/lock
rsync-command $RSYNC_BIN
host local
  hostname localhost
  volume data $RSBACKUP_TEST_DIR/source
EOF

"$RSBACKUP_BIN" --version | grep -F '10.0'
"$RSBACKUP_BIN" --config "$RSBACKUP_TEST_DIR/config" --backup
copied=$(find "$RSBACKUP_TEST_DIR/store" -type f -name payload.txt | head -1)
test -n "$copied"
test "$(cat "$copied")" = 'HarmonyOS rsbackup integration'
echo 'PASS: rsbackup copied the payload through the published rsync binary'
