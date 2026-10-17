#!/bin/sh
set -eu

package=$1
run_binary=$2
binary="$package/bin/activity-log-manager"
desktop="$package/share/applications/activity-log-manager.desktop"
icon="$package/share/icons/hicolor/48x48/apps/activity-log-manager.svg"

test -x "$binary"
test -s "$desktop"
test -s "$icon"
grep -q '^Name=Activity Log Manager$' "$desktop"
grep -q '^Exec=activity-log-manager$' "$desktop"
grep -q '^Type=Application$' "$desktop"

if [ "$run_binary" = 1 ]; then
    "$binary" --help >/dev/null 2>&1
fi

echo "activity-log-manager package smoke test: OK"
