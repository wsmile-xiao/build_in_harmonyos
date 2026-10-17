#!/bin/sh
# lpac 消费者测试：以库使用者身份执行被测二进制并按行为断言（R34/PF3：非空壳、非只打印）
# 用法: sh test.sh <lpac 路径>
#
# 环境变量见源码 src/main.c:35-36：
#   ENV_APDU_DRIVER = "LPAC_APDU"   ENV_HTTP_DRIVER = "LPAC_HTTP"
# 可选后端名见 driver/*.c 的 `.name`：pcsc / at / stdio（APDU），curl / stdio（HTTP）
set -u
BIN="${1:?usage: sh test.sh <lpac>}"
TOTAL=0; PASSN=0; FAILED=0
ck() {  # ck <描述> <0=通过>
  TOTAL=$((TOTAL+1))
  if [ "$2" -eq 0 ]; then PASSN=$((PASSN+1)); echo "PASS $1"; else FAILED=$((FAILED+1)); echo "FAIL $1"; fi
}

[ -x "$BIN" ]; ck "0 lpac 存在且可执行" $?

# ── 1) 默认后端（本包 LPAC_WITH_APDU_PCSC=ON ⇒ 首选 pcsc）
#     OHOS PC 无 PCSC 上下文 ⇒ 确定性失败路径：SCardEstablishContext 报错 + 非零退出。
#     这条同时是"能力面如实披露"：本平台没有智能卡通道。
OUT1=$("$BIN" 2>&1); RC1=$?
echo "--- [1] default rc=$RC1 ---"; printf '%s\n' "$OUT1" | head -6
[ "$RC1" -ne 0 ]; ck "1 默认后端退出码非 0（实测 rc=$RC1）" $?
[ -n "$OUT1" ]; ck "2 默认后端给出可读诊断输出（非静默失败）" $?
printf '%s\n' "$OUT1" | grep -qE "APDU driver init failed|SCardEstablishContext"
ck "3 诊断指向 APDU 后端初始化（设备能力面，见 notes 已知限制）" $?

# ── 2) 显式选 stdio 后端：跳过设备探测，走到 applet 入口（argc<2 → return -1 → 255）
OUT2=$(LPAC_APDU=stdio LPAC_HTTP=stdio "$BIN" 2>&1); RC2=$?
echo "--- [2] LPAC_APDU=stdio rc=$RC2 ---"; printf '%s\n' "$OUT2" | head -8
[ "$RC2" -ne 0 ]; ck "4 stdio 后端无参数退出码非 0（实测 rc=$RC2）" $?
printf '%s\n' "$OUT2" | grep -q "Usage:"
ck "5 stdio 后端打印 Usage 行（证明后端选择与 applet 入口都通）" $?
printf '%s\n' "$OUT2" | grep -q "lpac"
ck "6 Usage 回显程序名" $?

# ── 3) 未知子命令：applet_entry 未知分支（printf Unknown command + Usage + return -1）
OUT3=$(LPAC_APDU=stdio LPAC_HTTP=stdio "$BIN" __shouwei6_no_such_applet__ 2>&1); RC3=$?
echo "--- [3] bad-cmd rc=$RC3 ---"; printf '%s\n' "$OUT3" | head -8
[ "$RC3" -ne 0 ]; ck "7 未知子命令退出码非 0（实测 rc=$RC3）" $?
printf '%s\n' "$OUT3" | grep -q "Unknown command: __shouwei6_no_such_applet__"
ck "8 未知子命令回显 Unknown command" $?

echo "ASSERTION TOTAL=$TOTAL PASSED=$PASSN FAILED=$FAILED"
if [ "$FAILED" -eq 0 ]; then echo "RESULT: PASS"; exit 0; fi
echo "RESULT: FAIL"; exit 1
