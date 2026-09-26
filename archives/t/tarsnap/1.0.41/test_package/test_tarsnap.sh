#!/bin/sh
# 消费者视角验证（R34，工具类 = 真实执行被适配的 tarsnap 工具）。
# 全部步骤离线运行，不连接 Tarsnap 服务器。
#
# 说明：tarsnap-keygen 的完整流程必须向 Tarsnap 服务器注册真实账号
# （keygen/keygen_actual.c 的 keygen_network_register()，实测无账号报
# "No such user"），无法离线验证；因此密钥相关路径使用上游测试夹具
# tests/fake.keys 的副本（与上游场景 03-c-dry-run-fake-keyfile 同款），
# keygen 等其余工具做 --version 冒烟。
#
# 注意：不使用 set -e —— check() 模式需要收集全部失败项后统一报告。

BIN="${TARSNAP_BIN:?TARSNAP_BIN not set}"
T="$BIN/tarsnap"
KG="$BIN/tarsnap-keygen"
KM="$BIN/tarsnap-keymgmt"
KRG="$BIN/tarsnap-keyregen"
RC="$BIN/tarsnap-recrypt"
for tool in "$T" "$KG" "$KM" "$KRG" "$RC"; do
	test -x "$tool" || { echo "FAIL: missing binary: $tool"; exit 1; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
fails=0

check() {
	if [ "$1" -eq 0 ]; then
		echo "PASS: $2"
	else
		echo "FAIL: $2"
		fails=$((fails + 1))
	fi
}

# 上游 tests/fake.keys 的副本（随 test_package 分发的测试夹具）
keyfile="$(dirname "$0")/fake.keys"

# 1) tarsnap --version 真实执行且输出包含 tarsnap
v="$($T --version)"
check $? "tarsnap --version runs"
printf '%s\n' "$v" | grep -q "tarsnap 1"
check $? "version output contains tarsnap"

# 2) --help 真实执行
$T --help > /dev/null 2>&1
check $? "tarsnap --help runs"

# 3) 其余四个工具 --version 冒烟（完整 keygen/keyregen 需联网注册账号）
"$KG" --version > /dev/null 2>&1
check $? "tarsnap-keygen --version runs"
"$KRG" --version > /dev/null 2>&1
check $? "tarsnap-keyregen --version runs"
"$RC" --version > /dev/null 2>&1
check $? "tarsnap-recrypt --version runs"

# 4) 密钥管理工具读取上游 fake 密钥（离线）
id="$("$KM" --print-key-id "$keyfile" 2>/dev/null)"
check $? "tarsnap-keymgmt --print-key-id"
[ -n "$id" ] && [ "$id" -gt 0 ] 2>/dev/null
check $? "key id is a positive number"

"$KM" --print-key-permissions "$keyfile" 2>/dev/null | grep -q "reading"
check $? "tarsnap-keymgmt --print-key-permissions"

# 5) 离线派生只读密钥（keymgmt 真实密钥变换，不联网）
"$KM" --outkeyfile "$work/restricted.key" -r "$keyfile" > /dev/null 2>&1
check $? "tarsnap-keymgmt --outkeyfile -r"
rid="$("$KM" --print-key-id "$work/restricted.key" 2>/dev/null)"
[ "$rid" = "$id" ]
check $? "restricted keyfile valid (same key id)"

# 6) 缓存目录初始化（fake 密钥，离线；上游场景 03 同款）
$T --no-default-config --keyfile "$keyfile" \
	--cachedir "$work/cache" --initialize-cachedir \
	2> "$work/init.err"
check $? "tarsnap --initialize-cachedir"
grep -q "created for" "$work/init.err"
check $? "cachedir init message"

# 7) dry-run 模拟归档（真实加密/分块路径，不联网）
$T --no-default-config --keyfile "$keyfile" \
	--cachedir "$work/cache" -c --dry-run --print-stats "$keyfile" \
	2> "$work/dry.err"
check $? "tarsnap -c --dry-run --print-stats"
grep -q "Removing leading" "$work/dry.err"
check $? "dry-run output message"

if [ "$fails" -eq 0 ]; then
	echo "tarsnap test_package: all checks passed"
	exit 0
fi
echo "tarsnap test_package: $fails check(s) failed"
exit 1
