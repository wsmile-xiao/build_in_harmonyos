#!/data/service/hnp/bin/bash
# test_package/test_ohos.sh — rio 1.07 鸿蒙特有测试
#
# 参数: $1 = 被测包的 package_folder
#
# 断言（15 条）：
#   1  平台身份：uname -s = HarmonyOS
#   2  平台架构：uname -m = aarch64
#   3  产物为 64 位 ELF（ELF64 —— LP64 数据模型，32 位协议结构需专门适配）
#   4  ELF 机器类型为 AArch64
#   5  ELF 类型为 DYN（PIE）
#   6  解释器为 /lib/ld-musl-aarch64.so.1（musl libc，非 glibc 的 ld-linux-aarch64）
#   7  无 glibc 专有 NEEDED（libc.so.6/libm.so.6/libpthread.so.0/libdl.so.2/librt.so.1）
#   8  带 OHOS ELF 标识段 .note.ohos.ident
#   9  无 ISA I/O 端口空间时优雅降级：rio -d 未被信号终止且给出确定性诊断
#  10  诊断文本经 strerror() 取得（sys_errlist 已被 musl 移除）
#  11  自定义端口基址 -p 0x278 同样优雅降级
#  12  端口后端正向路径（RIO_PORT_DEVICE 指向测试替身）：Set() 通过，进入设备探测
#  13  端口偏移写语义：替身文件中数据口 0x378 / 控制口 0x37a 偏移被写入
#  14  二进制在任意 cwd 下可运行（不依赖构建目录）
#  15  包载荷完整：bin/rio 存在、非空且为 ELF 可执行文件
set -euo pipefail

PKG="${1:-}"
[ -n "$PKG" ] || { echo "FAIL: usage: test_ohos.sh <package_folder>" >&2; exit 1; }
BINDIR="$PKG/bin"
RIO="$BINDIR/rio"
[ -d "$BINDIR" ] || { echo "FAIL: $BINDIR missing" >&2; exit 1; }

find_tool() {
  local name="$1" p
  p="$(command -v "$name" 2>/dev/null || true)"
  if [ -n "$p" ]; then printf '%s' "$p"; return 0; fi
  for c in /data/service/hnp/bin/"$name" /usr/bin/"$name" /bin/"$name"; do
    [ -f "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}
READELF="$(find_tool readelf)" || { echo "FAIL: readelf not found" >&2; exit 1; }

WORKDIR=""
for base in "${TMPDIR:-}" "${HOME:-}/tmp" "${HOME:-}" /tmp; do
  [ -n "$base" ] || continue
  mkdir -p "$base" 2>/dev/null || continue
  if WORKDIR="$(mktemp -d "$base/rio-ohos.XXXXXX" 2>/dev/null)"; then break; fi
done
[ -n "$WORKDIR" ] || { echo "FAIL: no writable temp directory" >&2; exit 1; }
trap 'rm -rf "$WORKDIR"' EXIT HUP INT TERM

PASS=0
SKIP=0
ok()   { echo "OK:   $1"; PASS=$((PASS+1)); }
skip() { echo "SKIP: $1"; SKIP=$((SKIP+1)); }
fail() { echo "FAIL: $1"; exit 1; }

# 无 ISA I/O 端口空间的架构（aarch64/OHOS）上没有 /dev/port
port_device_present() { [ -e /dev/port ] && [ -r /dev/port ] && [ -w /dev/port ]; }

[ -f "$RIO" ] || fail "15: packaged binary missing: $RIO"
ELF_HDR="$("$READELF" -h "$RIO" 2>/dev/null)"
ELF_PROG="$("$READELF" -l "$RIO" 2>/dev/null)"
ELF_DYN="$("$READELF" -d "$RIO" 2>/dev/null)"
ELF_SEC="$("$READELF" -S "$RIO" 2>/dev/null)"

# 1 平台身份
[ "$(uname -s)" = "HarmonyOS" ] || fail "1: uname -s = $(uname -s) (HarmonyOS expected)"
ok "1: 平台身份 HarmonyOS"

# 2 平台架构
[ "$(uname -m)" = "aarch64" ] || fail "2: uname -m = $(uname -m) (aarch64 expected)"
ok "2: 平台架构 aarch64"

# 3 ELF64（LP64 数据模型）
echo "$ELF_HDR" | grep -q "Class:.*ELF64" || fail "3: not ELF64: $(echo "$ELF_HDR" | grep Class)"
ok "3: 产物为 ELF64（LP64 数据模型）"

# 4 AArch64
echo "$ELF_HDR" | grep -q "Machine:.*AArch64" || fail "4: machine != AArch64"
ok "4: ELF 机器类型 AArch64"

# 5 PIE
echo "$ELF_HDR" | grep -q "Type:.*DYN" || fail "5: not DYN/PIE: $(echo "$ELF_HDR" | grep Type)"
ok "5: ELF 类型 DYN（PIE）"

# 6 musl 解释器
echo "$ELF_PROG" | grep -q "/lib/ld-musl-aarch64.so.1" \
  || fail "6: interpreter is not /lib/ld-musl-aarch64.so.1"
ok "6: 解释器 /lib/ld-musl-aarch64.so.1（musl）"

# 7 无 glibc 专有 NEEDED
GLIBC_NEEDED=""
for lib in libc.so.6 libm.so.6 libpthread.so.0 libdl.so.2 librt.so.1 ld-linux-aarch64.so.1; do
  echo "$ELF_DYN" | grep -q "\[$lib\]" && GLIBC_NEEDED="$GLIBC_NEEDED $lib"
done
[ -z "$GLIBC_NEEDED" ] || fail "7: glibc-only NEEDED present:$GLIBC_NEEDED"
ok "7: 无 glibc 专有 NEEDED"

# 8 OHOS ELF 标识段
echo "$ELF_SEC" | grep -q "\.note\.ohos\.ident" || fail "8: .note.ohos.ident section missing"
ok "8: 带 OHOS 标识段 .note.ohos.ident"

# 9 无端口设备时优雅降级
set +e
OUT9="$("$RIO" -d 2>&1)"
rc9=$?
set -e
[ "$rc9" -lt 128 ] || fail "9: killed by signal (rc=$rc9)"
if port_device_present; then
  echo "$OUT9" | grep -q "device not found" || fail "9: unexpected diagnostic: $OUT9"
else
  echo "$OUT9" | grep -q "open( /dev/port ) failed" || fail "9: unexpected diagnostic: $OUT9"
fi
ok "9: 无 ISA I/O 端口空间时优雅降级（rc=$rc9，未被信号终止）"

# 10 诊断文本来自 strerror()（sys_errlist 已从 musl 移除）
if port_device_present; then
  skip "10: 该平台存在 /dev/port，降级路径不触发，errno 文案断言不适用"
else
  echo "$OUT9" | grep -q "No such file or directory" \
    || fail "10: strerror() errno text missing: $OUT9"
  ok "10: 诊断文本经 strerror() 取得（'No such file or directory'）"
fi

# 11 自定义端口基址
set +e
OUT11="$("$RIO" -p 0x278 -d 2>&1)"
rc11=$?
set -e
[ "$rc11" -lt 128 ] || fail "11: killed by signal (rc=$rc11)"
if port_device_present; then
  echo "$OUT11" | grep -q "device not found" || fail "11: unexpected diagnostic: $OUT11"
else
  echo "$OUT11" | grep -q "open( /dev/port ) failed" || fail "11: unexpected diagnostic: $OUT11"
fi
ok "11: -p 0x278 自定义端口基址同样优雅降级"

# 12/13 端口后端正向路径：用普通文件作 /dev/port 的测试替身，
#         验证 pread/pwrite 端口偏移寻址在 aarch64 上真实可用。
PORTDEV="$WORKDIR/portdev.img"
: > "$PORTDEV"
set +e
OUT12="$(RIO_PORT_DEVICE="$PORTDEV" "$RIO" -d 2>&1)"
rc12=$?
set -e
[ "$rc12" -lt 128 ] || fail "12: killed by signal (rc=$rc12)"
if echo "$OUT12" | grep -q "open( "; then fail "12: Set() still failed: $OUT12"; fi
echo "$OUT12" | grep -q "device not found" || fail "12: unexpected diagnostic: $OUT12"
ok "12: 端口后端打开测试替身并通过 Set()，进入设备探测"

DELTA="$(python3 - "$PORTDEV" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
print("size=%d data=%s ctrl=%s" % (
    len(data),
    ("0x%02x" % data[0x378]) if len(data) > 0x378 else "none",
    ("0x%02x" % data[0x37a]) if len(data) > 0x37a else "none"))
PY
)"
echo "     测试替身端口映像: $DELTA"
[ "$DELTA" = "size=891 data=0xa0 ctrl=0x04" ] \
  || fail "13: port offset write semantics wrong ($DELTA)"
ok "13: 端口偏移写语义正确（0x378=0xa0 数据口，0x37a=0x04 控制口）"

# 14 任意 cwd 可运行
set +e
OUT14="$(cd / && "$RIO" 2>&1)"
rc14=$?
set -e
[ "$rc14" -lt 128 ] || fail "14: killed by signal (rc=$rc14)"
echo "$OUT14" | grep -q "Rio utility v1.07" || fail "14: not runnable from another cwd"
ok "14: 任意 cwd 可运行（不依赖构建目录）"

# 15 包载荷完整
SIZE="$(wc -c < "$RIO" | tr -d ' ')"
[ "$SIZE" -gt 0 ] || fail "15: bin/rio is empty"
file "$RIO" 2>/dev/null | grep -q "ELF" || fail "15: bin/rio is not an ELF binary"
ok "15: 包载荷完整（bin/rio = ${SIZE} bytes）"

echo "PASS: test_ohos.sh ${PASS}/15 (skipped ${SKIP})"
