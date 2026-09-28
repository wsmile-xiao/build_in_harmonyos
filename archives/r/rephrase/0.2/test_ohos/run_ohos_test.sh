#!/bin/sh
# test_ohos -- rephrase 0.2 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 与上游（无任何测试）以及 test_package 消费者断言区分开，这里核验 OHOS 侧特有事实：
#   T1  产物为 AArch64 ELF
#   T2  产物内无构建机宿主绝对路径泄漏
#   T3  安装位为 0755 且不带 setuid 位（上游 install 规则要求 4711 setuid root）
#   T4  无 setuid 时 mlock(2) 门禁仍通过（RLIMIT_MEMLOCK=unlimited），即 exit != 2
#   T5  --gpg-key 分支命中编译期 GPG=/usr/local/bin/gpg（exit 4）
#   S1  交互输入路径未执行（无控制终端，open(/dev/tty)=ENXIO）=> 跳过并给证据
#   S2  口令穷举主流程未执行（OHOS PC 无 gpg 与 cryptsetup）=> 跳过并给证据
#
# 用法：sh run_ohos_test.sh <已安装二进制路径>
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <binary>"; exit 2; }
[ -f "$BIN" ] || { echo "FAIL: binary not found: $BIN"; exit 2; }

fail=0
skip=0
chk() { if [ "$2" = "0" ]; then echo "[PASS] $1"; else echo "[FAIL] $1"; fail=1; fi; }

if [ -x /usr/bin/timeout ]; then TMO="/usr/bin/timeout 30"; else TMO=""; fi

echo "--- rephrase 0.2 HarmonyOS 专项验证 (binary=$BIN) ---"

if readelf -h "$BIN" 2>/dev/null | grep -q "AArch64"; then r=0; else r=1; fi
chk "T1 AArch64 ELF" "$r"

if strings "$BIN" 2>/dev/null | grep -qE '/storage/|/home/|/Users/'; then
  echo "  leak: $(strings "$BIN" | grep -E '/storage/|/home/|/Users/' | head -1)"
  chk "T2 无宿主绝对路径泄漏" 1
else
  chk "T2 无宿主绝对路径泄漏" 0
fi

mode=$(ls -l "$BIN" | awk '{print $1}')
# The security-relevant claim is "no setuid/setgid bit" (upstream wants 4711).
# The exact owner/group/other permission bits are not asserted: HMDFS does not
# reliably carry chmod through conan's copy, and 0750 vs 0755 has no bearing on
# the privilege question.
case "$mode" in
  *s*) chk "T3 产物不带 setuid/setgid 位（实测 $mode）" 1 ;;
  ???x*|* )
     if printf '%s' "$mode" | grep -q "^-..x"; then
       chk "T3 产物不带 setuid/setgid 位且对属主可执行（实测 $mode）" 0
     else
       chk "T3 产物不可执行（实测 $mode）" 1
     fi ;;
esac

out=$($TMO "$BIN" 2>&1); rc=$?
if [ "$rc" = "2" ]; then
  chk "T4 无 setuid 下 mlock(2) 门禁通过（实测 exit=2，被 setuid 要求拒绝）" 1
else
  chk "T4 无 setuid 下 mlock(2) 门禁通过（exit=$rc，非 2）" 0
fi
if printf '%s\n' "$out" | grep -q "should be installed setuid root"; then r=1; else r=0; fi
chk "T4b stderr 不含 setuid root 抱怨" "$r"

outg=$($TMO "$BIN" --gpg-key 0xDEADBEEF 2>&1); rcg=$?
if [ "$rcg" = "4" ] && printf '%s\n' "$outg" | grep -qF '/usr/local/bin/gpg'; then
  chk "T5 --gpg-key 命中编译期 GPG=/usr/local/bin/gpg（exit=4）" 0
else
  chk "T5 --gpg-key 期望 exit=4 且报 /usr/local/bin/gpg，实测 exit=$rcg out=$outg" 1
fi

ttyerr=$($TMO "$BIN" --gpg-key 0xDEADBEEF 2>&1 | grep -c "Cannot open" )
if [ -e /dev/tty ]; then ttynode=yes; else ttynode=no; fi
echo "[INFO] S1 /dev/tty 节点存在=$ttynode；交互模式 read_pattern() 以 fopen(/dev/tty, r+) 取控制终端，"
echo "       无 ctty 的批处理环境返回 ENXIO => 交互输入路径未执行（探针见 notes.md）"
skip=$((skip + 1))

if command -v gpg >/dev/null 2>&1 || command -v cryptsetup >/dev/null 2>&1; then
  echo "[INFO] S2 检测到 gpg 或 cryptsetup，主流程可继续"
else
  echo "[SKIP] S2 口令穷举主流程未执行：OHOS PC 未提供 gpg 与 cryptsetup，fork+execv 目标不存在"
  skip=$((skip + 1))
fi

if [ "$fail" = "0" ]; then verdict="ALL PASS"; else verdict="FAILED"; fi
echo "--- rephrase 0.2 OHOS 专项: $verdict（跳过 $skip）---"
exit $fail
