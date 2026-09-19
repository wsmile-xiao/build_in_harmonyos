#!/bin/sh
# munin-c 0.0.13 消费者测试（真机运行）。
# R34：以使用者身份真实运行被测包构建的程序并断言行为——
# ok_plugin（上游自带的 munin 插件协议模拟器）的 fetch/config 输出、
# munin-plugins-c 多合一分发（argv0 basename → cpu 子命令读 /proc/stat，
# 安装于 libexec/munin-c/，pkglibexec_PROGRAMS）、munin-node-c/munin-inetd-c
# 存在性与 inetd 的 getopt 错误路径（node 为常驻服务，不纳入自动断言）。
# $1 = 被测包 sbin 目录

SBIN="$1"
PLUG="$SBIN/../libexec/munin-c/munin-plugins-c"
fails=0
n=0

ok() { n=$((n+1)); echo "PASS: $1"; }
bad() { n=$((n+1)); echo "FAIL: $1"; fails=$((fails+1)); }

# 1. ok_plugin 无参数 = fetch 模式：退出码 0 且输出协议值行
out=$("$SBIN/ok_plugin" 2>/dev/null); rc=$?
[ $rc -eq 0 ] && echo "$out" | grep -q 'first_f.value 1234.567'     && ok "ok_plugin fetch prints value" || bad "ok_plugin fetch prints value"

# 2. ok_plugin config：graph_title 与 label 行
out=$("$SBIN/ok_plugin" config 2>/dev/null)
echo "$out" | grep -q 'graph_title' && echo "$out" | grep -q 'first_f.label This is the first field'     && ok "ok_plugin config prints protocol" || bad "ok_plugin config prints protocol"

# 3. 多合一插件就位（pkglibexec 布局）
[ -f "$PLUG" ] && ok "munin-plugins-c installed under libexec/munin-c"     || bad "munin-plugins-c installed under libexec/munin-c"

# 4. argv0 分发：cpu 子命令读 /proc/stat 输出值行
cp "$PLUG" ./cpu 2>/dev/null
out=$(./cpu 2>/dev/null); rc=$?
[ $rc -eq 0 ] && echo "$out" | grep -Eq '\.value [0-9]+'     && ok "plugins-c argv0 dispatch (cpu) reads /proc" || bad "plugins-c argv0 dispatch (cpu) reads /proc"

# 5. cpu config 模式输出 graph_title
out=$(./cpu config 2>/dev/null)
echo "$out" | grep -q 'graph_title'     && ok "cpu config prints graph_title" || bad "cpu config prints graph_title"

# 6. munin-node-c 交付存在（常驻服务不自动拉起）
[ -f "$SBIN/munin-node-c" ] && ok "munin-node-c delivered" || bad "munin-node-c delivered"

# 7. munin-inetd-c 非法选项走 getopt 错误路径（非零退出，程序真实执行）
"$SBIN/munin-inetd-c" -Z >/dev/null 2>&1
[ $? -ne 0 ] && ok "munin-inetd-c rejects unknown option" || bad "munin-inetd-c rejects unknown option"

rm -f ./cpu
echo "checks=$n failures=$fails"
[ "$fails" -eq 0 ]
