#!/data/service/hnp/bin/bash
# test_package/test.sh — xfel 1.3.5 包级测试（消费者视角）
#
# 在 conanrun 环境（PATH 含已安装的 bin/）中真实执行包内二进制并对输出断言：
#   T1        xfel 已安装且可执行
#   T2  [OHOS] 产物为 AArch64 ELF、由 /lib/ld-musl-aarch64.so.1 加载
#   T3  [OHOS] 可在鸿蒙上真实运行：xfel --help rc=0 且打印版本横幅
#   T4        上游 usage 入口（无参 / -h / --help）均 rc=0
#   T5  [OHOS] 设备类子命令不再崩溃：24 条入口全部 rc=255（非 139 SIGSEGV）并打印 ERROR
#   T6  [OHOS] 链接的是 Conan 管理的 libusb（NEEDED libusb-1.0.so.0），无宿主库污染
#   T7  [OHOS] ELF 安全属性：PIE + full RELRO + NX（GNU_STACK 不可执行）
#   T8        随包数据完整：share/xfel/99-xfel.rules 与 licenses/LICENSE
#   T9        usage 横幅列出全部文档化子命令
#
# 被测设备类命令按设计以 rc=255 退出，故所有外部命令一律经 run_it 显式捕获
# rc/输出后再断言（rc 本身即断言对象），不依赖 `set -e` 的失败即退出语义。
set -euo pipefail

PASS=0
FAIL=0
SKIP=0
NAMES=()
STATUS=()

report() { # report <status> <name> [detail]
  local st="$1" name="$2" detail="${3:-}"
  case "$st" in
    PASS) PASS=$((PASS+1)) ;;
    FAIL) FAIL=$((FAIL+1)) ;;
    *)    SKIP=$((SKIP+1)) ;;
  esac
  NAMES+=("$name"); STATUS+=("$st")
  printf '[%s] %-58s %s\n' "$st" "$name" "$detail"
}

# run_it <cmd...> — 执行命令并把输出/退出码写入全局 OUT / RC
run_it() {
  RC=0
  OUT=$("$@" 2>&1) || RC=$?
}

READELF="$(command -v readelf || true)"  # readelf 缺失时下面默认值兜底，故忽略其退出码
READELF="${READELF:-/data/service/hnp/bin/readelf}"
WORK="$(pwd)/xfel-testwork"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
rm -rf "$WORK"; mkdir -p "$WORK"

echo "==== xfel test_package ===="
echo "PATH=$PATH"
# command -v 未命中时返回非 0（T1 会给出 FAIL），此处显式忽略
XFL="$(command -v xfel || true)"
echo "xfel -> ${XFL:-not found}"

# ---------- T1 ----------
if [ -n "$XFL" ] && [ -x "$XFL" ]; then
  report PASS "T1 xfel installed and executable" "$XFL"
else
  report FAIL "T1 xfel installed and executable" "missing binary"
  echo "---- test_package summary: pass=$PASS fail=$FAIL skip=$SKIP ----"
  exit 1
fi
PKGROOT=$(cd "$(dirname "$XFL")/.." && pwd)

# ---------- T2 [OHOS] ----------
em=$(od -An -tx1 -N20 "$XFL" | tr -d ' \n'); em="${em:36:4}"
interp=$("$READELF" -l "$XFL" | sed -n 's/.*Requesting program interpreter: \(.*\)\]/\1/p')
interp="${interp%%$'\n'*}"
if [ "$em" = "b700" ] && [ "$interp" = "/lib/ld-musl-aarch64.so.1" ]; then
  report PASS "[OHOS] T2 AArch64 ELF + musl loader" "e_machine=$em interp=$interp"
else
  report FAIL "[OHOS] T2 AArch64 ELF + musl loader" "e_machine=$em interp=${interp:-none}"
fi

# ---------- T3 [OHOS] ----------
run_it "$XFL" --help
USAGE_OUT="$OUT"
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'xfel(v1\.3\.5)'; then
  report PASS "[OHOS] T3 runs on OHOS: xfel --help rc=0 + banner" "rc=$RC"
else
  report FAIL "[OHOS] T3 runs on OHOS: xfel --help rc=0 + banner" "rc=$RC"
fi

# ---------- T4 ----------
t4ok=1; t4det=""
for a in "" "-h" "--help"; do
  run_it "$XFL" $a; r=$RC
  printf '%s' "$OUT" | grep -q 'xfel(v1\.3\.5)' || t4ok=0
  [ "$r" -eq 0 ] || t4ok=0
  t4det="$t4det [$a rc=$r]"
done
if [ "$t4ok" = 1 ]; then
  report PASS "T4 upstream usage entries rc=0 (no-arg/-h/--help)" "$t4det"
else
  report FAIL "T4 upstream usage entries rc=0 (no-arg/-h/--help)" "$t4det"
fi

# ---------- T5 [OHOS] 设备类子命令不崩溃 ----------
cd "$WORK" || exit 1
printf 'xfel-fixture' > in.bin
DEV_CMDS=(
  "version"
  "hexdump 0x1000 16"
  "dump 0x1000 16"
  "read32 0x1000"
  "write32 0x1000 0x1234"
  "read 0x1000 16 out.bin"
  "write 0x1000 in.bin"
  "exec 0x1000"
  "reset"
  "sid"
  "jtag"
  "ddr"
  "sign 000000000000000000000000000000000000000000000000000000000000000000 0000000000000000000000000000000000000000000000000000000000000000 sig.bin"
  "spinor"
  "spinor erase 0 0x1000"
  "spinor read 0 16 nor.bin"
  "spinor write 0 in.bin"
  "spinand"
  "spinand erase 0 0x1000"
  "spinand read 0 16 nand.bin"
  "spinand write 0 in.bin"
  "spinand splwrite 0x800 0 in.bin"
  "extra"
  "not-a-real-command"
)
t5ok=1; t5crash=0; t5bad=0; t5n=0
for c in "${DEV_CMDS[@]}"; do
  t5n=$((t5n+1))
  run_it "$XFL" $c; r=$RC
  if [ "$r" -eq 139 ]; then t5crash=$((t5crash+1)); t5ok=0; fi
  if [ "$r" -ne 255 ]; then t5bad=$((t5bad+1)); t5ok=0; fi
  printf '%s' "$OUT" | grep -q '^ERROR: ' || { t5bad=$((t5bad+1)); t5ok=0; }
done
# 用例表长度与声明数量必须自洽（防申报/事实漂移）
[ "$t5n" -eq 24 ] || { t5ok=0; t5bad=$((t5bad+1)); }
if [ "$t5ok" = 1 ]; then
  report PASS "[OHOS] T5 24 device entries rc=255, no SIGSEGV" "cases=$t5n crash=0 bad=0"
else
  report FAIL "[OHOS] T5 24 device entries rc=255, no SIGSEGV" "cases=$t5n crash=$t5crash bad=$t5bad"
fi

# ---------- T6 [OHOS] ----------
needed=$("$READELF" -d "$XFL" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p')
if printf '%s\n' "$needed" | grep -qx "libusb-1.0.so.0" \
   && ! printf '%s\n' "$needed" | grep -qE '^lib(z|udev|usb-1\.0\.so$|c\.so\.6)'; then
  report PASS "[OHOS] T6 links Conan-managed libusb, no host libs" "$(printf '%s' "$needed" | tr '\n' ',')"
else
  report FAIL "[OHOS] T6 links Conan-managed libusb, no host libs" "$(printf '%s' "$needed" | tr '\n' ',')"
fi

# ---------- T7 [OHOS] 安全属性 ----------
# grep -c 无匹配时退出码为 1，属预期（计数为 0），故统一 `|| true` 兜底
seg=$("$READELF" -lW "$XFL")
dyn=$("$READELF" -dW "$XFL")
norm=$(printf '%s' "$seg" | grep -c 'GNU_RELRO' || true)
stack=$(printf '%s' "$seg" | grep 'GNU_STACK' | grep -c 'RW ' || true)
pie=$(printf '%s' "$dyn" | grep -c 'Flags: NOW PIE' || true)
bindnow=$(printf '%s' "$dyn" | grep -c 'BIND_NOW' || true)
if [ "$norm" -ge 1 ] && [ "$stack" -ge 1 ] && [ "$pie" -ge 1 ] && [ "$bindnow" -ge 1 ]; then
  report PASS "[OHOS] T7 PIE + full RELRO + NX stack" "relro=$norm nx_stack=$stack pie_now=$pie"
else
  report FAIL "[OHOS] T7 PIE + full RELRO + NX stack" "relro=$norm nx_stack=$stack pie_now=$pie bindnow=$bindnow"
fi

# ---------- T8 ----------
if [ -f "$PKGROOT/share/xfel/99-xfel.rules" ] && [ -f "$PKGROOT/licenses/LICENSE" ]; then
  report PASS "T8 shipped data present (99-xfel.rules + LICENSE)" "share/xfel, licenses"
else
  report FAIL "T8 shipped data present (99-xfel.rules + LICENSE)" "missing files"
fi

# ---------- T9 ----------
t9ok=1; t9miss=""; t9n=0
for sub in version hexdump dump read32 write32 read write exec reset sid jtag ddr sign spinor spinand splwrite extra; do
  t9n=$((t9n+1))
  printf '%s' "$USAGE_OUT" | grep -qw -- "$sub" || { t9ok=0; t9miss="$t9miss $sub"; }
done
if [ "$t9ok" = 1 ]; then
  report PASS "T9 usage banner lists all documented subcommands" "$t9n/$t9n"
else
  report FAIL "T9 usage banner lists all documented subcommands" "missing:$t9miss"
fi

echo "---- test_package summary: pass=$PASS fail=$FAIL skip=$SKIP ----"
if [ "${#NAMES[@]}" -gt 0 ]; then
  for i in "${!NAMES[@]}"; do printf '  %-4s %s\n' "${STATUS[$i]}" "${NAMES[$i]}"; done
fi

[ "$FAIL" -eq 0 ] || exit 1
exit 0
