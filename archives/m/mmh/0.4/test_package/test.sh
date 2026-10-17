#!/bin/sh
# mmh 0.4 消费者冒烟测试 — 4 例
# 运行环境：conan test_package（VirtualRunEnv 已注入包内 bin/）
# 独立上下文（MH 指向临时 context），不触碰 $HOME/Mail。

set -u
fail=0
ok()  { echo "PASS [$1] $2"; }
bad() { echo "FAIL [$1] $2"; fail=1; }

workdir="$PWD/smoke-work"
rm -rf "$workdir"
mkdir -p "$workdir/mail" "$workdir/.mmh"
printf 'Path: %s\nInbox: +inbox\n' "$workdir/mail" > "$workdir/.mmh/profile"
export MMH="$workdir/.mmh"

# 1) mhparam -Version 输出应包含 0.4（mmh 的版本开关为大写 V）
v1=$(mhparam -Version 2>&1)
echo "$v1" | grep -q '0\.4' \
	&& ok 1 "mhparam -Version: $v1" \
	|| bad 1 "mhparam -Version: $v1"

# 2) mhparam version 组件应精确为 mmh-0.4（-DVERSION 由 version.sh 注入）
v2=$(mhparam version 2>&1)
[ "$v2" = "mmh-0.4" ] \
	&& ok 2 "mhparam version = $v2" \
	|| bad 2 "mhparam version = $v2"

# 3) folder -create 创建新文件夹（落盘于 context Path 下）
folder -create +smoke >/dev/null 2>&1
[ -d "$workdir/mail/smoke" ] \
	&& ok 3 "folder -create +smoke -> mail/smoke" \
	|| bad 3 "folder -create +smoke（mail/smoke 不存在）"

# 4) folders 能列出该文件夹
folders 2>/dev/null | grep -q 'smoke' \
	&& ok 4 "folders lists smoke" \
	|| bad 4 "folders does not list smoke"

echo "== test.sh: $( [ $fail -eq 0 ] && echo ALL-PASS || echo FAILED ) =="
exit $fail
