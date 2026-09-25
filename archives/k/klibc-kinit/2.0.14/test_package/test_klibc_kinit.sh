#!/bin/sh
# klibc-kinit 2.0.14 — test_package 消费者断言（鸿蒙特有测试）
#
# usage: sh test_klibc_kinit.sh <package_bindir>
#
# kinit 是 initramfs 的 PID 1 程序：main() 里 open("/dev/console")、mount /proc 与 /sys，
# 失败路径 umount2("/proc")/umount2("/sys")，成功路径经 initrd.c / run-init 用 MS_MOVE
# 重挂根 + chroot + exec init。在非 PID 1 的在线 HarmonyOS 上执行它属破坏性操作
# （理由记在 test_package/MANIFEST.yml），因此消费者对交付物做**装载前静态校验**：
# ELF 头字段、静态链接证据（无解释器路径）、以及 kinit 真的把 ipconfig/run-init
# 等上游目标文件链进来的字面量证据。
#
# 字面量匹配走 `od -v -tx1` 十六进制流：toybox 的 grep 对二进制文件不做行匹配、
# `tr -c '[:print:]'` 在 toybox 0.8.12 上又是恒等操作，只有 od + tr -d 到处都可用。
#
# 所有路径都由传入的包 bindir 推导，隐藏 bindir 即整体失败（R34/L1e）。
set -u

BIN_DIR="${1:?usage: test_klibc_kinit.sh <package_bindir>}"
KINIT="$BIN_DIR/kinit"
PKG_ROOT="$(dirname "$BIN_DIR")"

PASS=0
FAIL=0
TOTAL=0

check() { # check <desc> <condition-result>
  TOTAL=$((TOTAL + 1))
  if [ "$2" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "ok $TOTAL - $1"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL $TOTAL - $1"
  fi
}

elf_byte() { # elf_byte <offset> -> 该偏移字节的十进制值
  od -An -j "$1" -N 1 -tu1 "$KINIT" | tr -d ' \n'
}

HEX=""
load_hex() { HEX=$(od -An -v -tx1 "$KINIT" | tr -d ' \n'); }

has_literal() { # has_literal <literal> -> 0 表示二进制里存在该可打印串
  [ -n "$HEX" ] || load_hex
  needle=$(printf '%s' "$1" | od -An -v -tx1 | tr -d ' \n')
  case "$HEX" in
    *"$needle"*) return 0 ;;
    *) return 1 ;;
  esac
}

echo "== klibc-kinit consumer checks =="

check "bindir exists: $BIN_DIR" "$([ -d "$BIN_DIR" ] && echo 0 || echo 1)"
check "bin/kinit installed" "$([ -f "$KINIT" ] && echo 0 || echo 1)"
check "bin/kinit is executable" "$([ -x "$KINIT" ] && echo 0 || echo 1)"

SIZE=$(wc -c < "$KINIT" 2>/dev/null || echo 0)
check "bin/kinit non-trivial size ($SIZE bytes)" \
      "$([ "$SIZE" -gt 40000 ] && echo 0 || echo 1)"

MAGIC=$(od -An -N4 -tx1 "$KINIT" | tr -d ' \n')
check "ELF magic 0x7f454c46" "$([ "$MAGIC" = "7f454c46" ] && echo 0 || echo 1)"

B4=$(elf_byte 4)
check "ELFCLASS64 (64-bit object)" "$([ "$B4" = "2" ] && echo 0 || echo 1)"

B5=$(elf_byte 5)
check "ELFDATA2LSB (little endian)" "$([ "$B5" = "1" ] && echo 0 || echo 1)"

B16=$(elf_byte 16)
B17=$(elf_byte 17)
check "e_type=ET_EXEC (bytes16-17=$B16,$B17；非依赖解释器的 DYN)" \
      "$([ "$B16" = "2" ] && [ "$B17" = "0" ] && echo 0 || echo 1)"

B18=$(elf_byte 18)
B19=$(elf_byte 19)
check "e_machine=EM_AARCH64 0xb7 (bytes18-19=$B18,$B19)" \
      "$([ "$B18" = "183" ] && [ "$B19" = "0" ] && echo 0 || echo 1)"

# 交付的是上游 static/kinit：二进制里不得出现任何动态装载器/共享 klibc 路径。
for marker in "ld-musl" "ld-linux" "/lib/klibc-"; do
  if has_literal "$marker"; then
    RC=1
  else
    RC=0
  fi
  check "no '$marker' interpreter path embedded (static kinit, not shared/kinit)" $RC
done

# 上游 usr/kinit/Kbuild 把 ipconfig/ nfsmount/ run-init/ 的 lib.a 链进 kinit；
# 以下字面量证明链接确实发生，而不是装了一个空壳。
has_literal "IP-Config"
check "ipconfig objects linked into kinit" $?

has_literal "rootfs not a ramfs or tmpfs"
check "run-init objects linked into kinit" $?

has_literal "usr/kinit/run-init/runinitlib.c"
check "kinit built from upstream usr/kinit sources (debug path record)" $?

has_literal "kinit_mount="
check "kinit root= / cmdline option parser linked" $?

if [ -f "$PKG_ROOT/res/upstream-tests-summary.txt" ] \
   && grep -q "failures=0" "$PKG_ROOT/res/upstream-tests-summary.txt"; then
  RC=0
else
  RC=1
fi
check "packaged upstream self-test evidence reports failures=0" $RC

check "license packaged" "$([ -f "$PKG_ROOT/licenses/LICENSE" ] && echo 0 || echo 1)"

echo "ASSERTIONS: $TOTAL, FAILURES: $FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "Running test: klibc-kinit consumer PASS"
  echo "HMBS_TEST_PACKAGE_RESULT: PASS"
  exit 0
fi
echo "Running test: klibc-kinit consumer FAIL"
echo "HMBS_TEST_PACKAGE_RESULT: FAIL"
exit 1
