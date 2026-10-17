#!/usr/bin/env bash
# test_package/test.sh — CrashMail II 真实消费者冒烟测试
#
# 在 conanrun 环境下执行：PATH 由 VirtualRunEnv 指向已安装的 bin/，
# 因此被测对象是 conan create 真正打包出来的那 8 个可执行文件，
# 而不是构建树里的副本（L1e 反向验证：移走 bin/ 后本脚本必须失败）。
#
# 场景与上游 tests/ 的夹具同源（nodelist/pointlist/cmnodelist.prefs/
# crashmail.prefs 逐字节复制自上游 tests/），但断言与夹具归本包所有，
# 产物全部落在 conan build_folder（$1）下。
#
# 各断言有意避免使用会与 pipefail 相互作用的管道：A5 的 le16 与 A7 的
# NUL 剥离都先把数据落到文件再读取，因为 `producer | grep -q` 在 grep
# 命中后立即退出会给 producer 发 SIGPIPE，配合 pipefail 会把一次成功
# 匹配变成非零退出（假失败）。
set -euo pipefail

D="${1:?usage: test.sh <workdir>}/crashmail-smoke"
rm -rf "$D"
mkdir -p "$D"

HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="$HERE/data"

PASS=0
fail() { echo "❌ $1"; exit 1; }
ok()   { PASS=$((PASS + 1)); echo "✅ $1"; }

# ── 夹具：沙箱 spool / areas / nodelist ───────────────────────────────
mkdir -p "$D/sandbox/spool/inbound" "$D/sandbox/spool/outbound" \
         "$D/sandbox/spool/temp" "$D/sandbox/spool/packets" \
         "$D/sandbox/areas/netmail" "$D/sandbox/areas/testarea" \
         "$D/sandbox/areas/bad" "$D/sandbox/nodelist"
cp "$DATA/crashmail.prefs" "$D/sandbox/crashmail.prefs"
cp "$DATA/nodelist.txt" "$DATA/pointlist.txt" "$DATA/cmnodelist.prefs" \
   "$D/sandbox/nodelist/"
cd "$D/sandbox"

# ── A1: 产物自报版本指纹 ─────────────────────────────────────────────
crashmail settings crashmail.prefs > "$D/settings.out" 2>&1
grep -q 'CrashMail II 1\.7 started successfully!' "$D/settings.out" \
  || fail "A1 crashmail 未自报 CrashMail II 1.7 版本行"
grep -q '^CrashMail end' "$D/settings.out" \
  || fail "A1 crashmail 未正常结束"
ok "A1 crashmail settings 自报版本 CrashMail II 1.7 并正常退出"

# ── A2: crashlist 真实生成 nodelist 索引 ─────────────────────────────
crashlist nodelist > "$D/crashlist.out" 2>&1
[ -s nodelist/cmnodelist.index ] \
  || fail "A2 crashlist 未生成非空 nodelist/cmnodelist.index"
grep -q 'Processing nodelist nodelist.txt' "$D/crashlist.out" \
  || fail "A2 crashlist 未处理 nodelist.txt"
ok "A2 crashlist 生成 nodelist/cmnodelist.index"

# ── A3/A4: crashgetnode 解析点位与节点 ───────────────────────────────
crashgetnode 99:99/1.1 nodelist > "$D/node-point.out" 2>&1
diff -u "$DATA/crashgetnode-point.expected" "$D/node-point.out" \
  || fail "A3 crashgetnode 点位输出与期望不符"
ok "A3 crashgetnode 99:99/1.1 输出与上游期望逐字节一致"

crashgetnode 99:99/99 nodelist > "$D/node-node.out" 2>&1
diff -u "$DATA/crashgetnode-node.expected" "$D/node-node.out" \
  || fail "A4 crashgetnode 节点输出与期望不符"
ok "A4 crashgetnode 99:99/99 输出与上游期望逐字节一致"

# ── A5: crashwrite 生成真实 FidoNet type-2+ 包 ───────────────────────
# 包头字段偏移取自上游 shared/fidonet.h 的 PKTHEADER_* 定义；
# 多字节字段按 getuword() 的小端序解读。
le16() {
  od -An -tu2 -j "$2" -N2 "$1" > "$D/le16.tmp"
  tr -d ' \n' < "$D/le16.tmp"
}

printf 'This is a test netmail message.\n' > "$D/body.txt"
crashwrite dir spool/inbound FROMNAME "Test User" FROMADDR "99:99/999" \
  TONAME "Test Sysop" TOADDR "99:99/1" SUBJECT "Test netmail message" \
  TEXT "$D/body.txt" > "$D/crashwrite.out" 2>&1
find spool/inbound -type f -name '*.pkt' > "$D/pkt.list"
PKT_COUNT=$(wc -l < "$D/pkt.list")
[ "$PKT_COUNT" -eq 1 ] || fail "A5 crashwrite 生成的 .pkt 数量为 $PKT_COUNT，期望 1"
PKT=$(cat "$D/pkt.list")
[ "$(le16 "$PKT" 18)" = "2" ] \
  || fail "A5 包头 PKTTYPE(偏移18) 为 $(le16 "$PKT" 18)，期望 2（type-2+）"
[ "$(le16 "$PKT" 0)" = "999" ] \
  || fail "A5 包头 ORIGNODE(偏移0) 为 $(le16 "$PKT" 0)，期望 999"
[ "$(le16 "$PKT" 2)" = "1" ] \
  || fail "A5 包头 DESTNODE(偏移2) 为 $(le16 "$PKT" 2)，期望 1"
YEAR=$(le16 "$PKT" 4)
[ "$YEAR" -ge 2020 ] && [ "$YEAR" -le 2100 ] \
  || fail "A5 包头 YEAR(偏移4) 为 $YEAR，不是合理年份"
ok "A5 crashwrite 生成 1 个 type-2+ 包（PKTTYPE=2 ORIGNODE=999 DESTNODE=1 YEAR=$YEAR）"

# ── A6/A7: crashmail 把入站包 toss 进 netmail 区 ─────────────────────
crashmail settings crashmail.prefs toss > "$D/toss.out" 2>&1
grep -q 'Area NETMAIL -- 1 messages' "$D/toss.out" \
  || fail "A6 toss 未报告 NETMAIL 区 1 条消息"
ok "A6 crashmail toss 报告 Area NETMAIL -- 1 messages"

[ -f areas/netmail/2.msg ] || fail "A7 toss 未生成 areas/netmail/2.msg"
# 注意：`*.msg` 是定长头 + NUL 填充的二进制格式，不能直接对它 grep。
# toybox grep 不在含 NUL 的二进制文件里匹配（即使字符串确实存在也返回 1，
# `-a` 亦无效），而 coreutils grep 会返回 0——CI worker 上没有 coreutils grep，
# 直接用 grep 会在 worker 上假失败。先 tr 去掉 NUL 落成文本再匹配，
# 该写法在 toybox 与 coreutils 两套工具链下均实测通过。
tr -d '\000' < areas/netmail/2.msg > "$D/2msg.txt"
grep -q 'Test netmail message' "$D/2msg.txt" \
  || fail "A7 areas/netmail/2.msg 不含投递的主题"
ok "A7 投递结果 areas/netmail/2.msg 含主题 Test netmail message"

# ── A8: crashstats 读取 toss 生成的统计文件 ──────────────────────────
[ -s crashmail.stats ] || fail "A8 toss 未生成非空 crashmail.stats"
crashstats crashmail.stats sort a > "$D/stats.out" 2>&1
grep -q 'CrashStats 1\.7' "$D/stats.out" || fail "A8 crashstats 未自报版本"
grep -q 'NETMAIL' "$D/stats.out" || fail "A8 crashstats 输出未包含 NETMAIL 区"
ok "A8 crashstats 解析 crashmail.stats 并输出 NETMAIL 统计"

cd "$D"
rm -rf "$D/sandbox"
echo "✅ crashmail test_package PASSED (assertions=$PASS)"
