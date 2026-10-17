#!/data/service/hnp/bin/bash
# test_package/test.sh — rio 1.07 功能测试（消费者视角，真实执行包内二进制）
#
# 参数: $1 = 被测包内 rio 二进制的路径（缺省用 PATH 中的 rio）
#
# 断言（6 条）：
#   1  `rio` 无参数输出版本横幅 "Rio utility v1.07"
#   2  `rio` 无参数输出完整用法表（15 个开关全部列出）
#   3  用法表回显默认端口基址 0x378 与默认 IO 延时 20000/100/2
#   4  未知选项不崩溃，回退打印用法表
#   5  `rio -p 0x278 -d` 解析自定义端口基址后进入端口层（确定性诊断，非信号退出）
#   6  `rio -o "5 4 3 2 1" -d -dr 4` 解析引号参数与 rx 延时后不崩溃
set -euo pipefail

BIN="${1:-rio}"
[ -f "$BIN" ] || { echo "FAIL: rio binary not found: $BIN" >&2; exit 1; }
RUN=("$BIN")

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL: $1"; exit 1; }

# 端口设备可用性：无 ISA I/O 端口空间的架构（aarch64/OHOS）上没有 /dev/port
port_device_present() { [ -e /dev/port ] && [ -r /dev/port ] && [ -w /dev/port ]; }

# 1 版本横幅
OUT="$("${RUN[@]}" 2>&1 || true)"
echo "$OUT" | grep -q "Rio utility v1.07 - The Snowblind Alliance (c) 1999" \
  || fail "1: version banner missing"
ok "1: 版本横幅 Rio utility v1.07"

# 2 完整用法表
MISSING=""
for sw in "-d" "-iy" "-in" "-x" "-u" "-g" "-f" "-z" "-za" "-o" "-p" "-v" "-di" "-dt" "-dr"; do
  echo "$OUT" | grep -q -- "$sw" || MISSING="$MISSING $sw"
done
[ -z "$MISSING" ] || fail "2: usage table is missing switches:$MISSING"
ok "2: 用法表列出全部 15 个开关"

# 3 默认值
echo "$OUT" | grep -q "default=0x378"                            || fail "3a: default port base 0x378 missing"
echo "$OUT" | grep -q "initialization delay (default is 20000)"  || fail "3b: default -di 20000 missing"
echo "$OUT" | grep -q "tx delay (default is 100)"                || fail "3c: default -dt 100 missing"
echo "$OUT" | grep -q "rx delay (default is 2)"                  || fail "3d: default -dr 2 missing"
ok "3: 默认端口 0x378 与默认延时 20000/100/2"

# 4 未知选项 -> 回退打印用法表
set +e
OUT4="$("${RUN[@]}" --not-a-real-switch 2>&1)"
rc4=$?
set -e
[ "$rc4" -lt 128 ] || fail "4: killed by signal (rc=$rc4)"
echo "$OUT4" | grep -q "command line switches available" || fail "4: no usage fallback"
ok "4: 未知选项回退打印用法表（rc=$rc4，未被信号终止）"

# 5 自定义端口基址
set +e
OUT5="$("${RUN[@]}" -p 0x278 -d 2>&1)"
rc5=$?
set -e
[ "$rc5" -lt 128 ] || fail "5: killed by signal (rc=$rc5)"
[ -n "$OUT5" ] || fail "5: no diagnostic after '-p 0x278 -d'"
if port_device_present; then
  echo "$OUT5" | grep -q "device not found" || fail "5: unexpected diagnostic: $OUT5"
else
  echo "$OUT5" | grep -q "open( /dev/port ) failed" || fail "5: unexpected diagnostic: $OUT5"
fi
ok "5: -p 0x278 -d 解析端口基址并进入端口层（确定性诊断）"

# 6 引号参数 + rx 延时
set +e
OUT6="$("${RUN[@]}" -o "5 4 3 2 1" -d -dr 4 2>&1)"
rc6=$?
set -e
[ "$rc6" -lt 128 ] || fail "6: killed by signal (rc=$rc6)"
[ -n "$OUT6" ] || fail "6: no diagnostic"
ok "6: -o \"5 4 3 2 1\" -d -dr 4 参数解析正常"

echo "PASS: test.sh ${PASS}/6"
