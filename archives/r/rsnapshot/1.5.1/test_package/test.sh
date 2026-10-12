#!/bin/bash
# rsnapshot 1.5.1 — test_package 测试脚本 (R34 实质测试)
# 依赖工具 (rsnapshot/rsync/ssh) 通过 conanrun.sh 的 PATH 从依赖包解析。
set -euo pipefail

cd "$(dirname "$0")"

echo "== rsnapshot --version"
rsnapshot --version

echo "== rsync --version"
rsync --version

WORK="$(mktemp -d "${TMPDIR:-/tmp}/rsnapshot-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

CONF="$WORK/rsnapshot-test.conf"
SRC="$WORK/backup-src"
ROOT="$WORK/snapshots"
mkdir -p "$SRC/data"
echo "rsnapshot ohos test" > "$SRC/data/hello.txt"

cat > "$CONF" <<EOF
config_version	1.2
snapshot_root	$ROOT
cmd_rsync	$(command -v rsync)
cmd_ssh	$(command -v ssh)
interval	hourly	2
verbose	3
lockfile	$WORK/rsnapshot.pid
backup	$SRC/	localhost/
EOF

echo "== configtest"
rsnapshot -c "$CONF" configtest

echo "== hourly snapshot"
rsnapshot -c "$CONF" hourly

test -d "$ROOT/hourly.0/localhost"
# rsnapshot uses rsync --relative: the absolute source path is replicated
# under hourly.0/localhost/ (leading '/' stripped).
test -f "$ROOT/hourly.0/localhost$SRC/data/hello.txt"
test "$(cat "$ROOT/hourly.0/localhost$SRC/data/hello.txt")" = "rsnapshot ohos test"

echo "rsnapshot test_package: ALL PASSED"
