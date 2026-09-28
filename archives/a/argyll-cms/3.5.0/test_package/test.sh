#!/data/service/hnp/bin/bash
# test_package/test.sh — argyll-cms 3.5.0 功能测试（上游行为视角）
#
# 参数: $1 = 包内 bin 目录，$2 = 包内 ref 目录
# 所有工具都在 conanrun 环境下真实执行；任何断言失败立即非零退出。
#
# 断言（8 条）：
#   1  iccdump ref/sRGB.icm            解析真实 ICC profile（Profile size / Version）
#   2  iccdump ref/ClayRGB1998.icm     解析第二个出厂 profile（Display class）
#   3  icclu -ff -ir -pl sRGB.icm      RGB→Lab 正向着色转换引擎（矩阵 profile）
#   4  icclu -fb -ir -pl sRGB.icm      Lab→RGB 反向转换（矩阵 profile）
#   5  icclu RGB→Lab→RGB              三组颜色往返一致性（|Δ| < 1e-6）
#   6  iccgamut sRGB.icm               色域引擎产出 CGATS .gam 文件（非空）
#   7  targen -d2 -n16 chart          测试图表生成器产出 .ti1 图表（非空）
#   8  dispwin --version               X11 链接的 GUI 二进制可加载并运行
set -euo pipefail

BINDIR="${1:-}"
REFDIR="${2:-}"
[ -n "$BINDIR" ] && [ -n "$REFDIR" ] \
  || { echo "FAIL: usage: test.sh <pkg>/bin <pkg>/ref" >&2; exit 1; }
[ -d "$BINDIR" ] || { echo "FAIL: bindir missing: $BINDIR" >&2; exit 1; }
[ -d "$REFDIR" ] || { echo "FAIL: refdir missing: $REFDIR" >&2; exit 1; }

# 工具查找：先查 PATH，再查 OHOS 固定位置（/system/bin/sh 环境可能很贫瘠）
find_tool() {
  local name="$1" p
  p="$(command -v "$name" 2>/dev/null || true)"
  if [ -n "$p" ]; then printf '%s' "$p"; return 0; fi
  for c in /data/service/hnp/bin/"$name" /usr/bin/"$name" /bin/"$name"; do
    [ -f "$c" ] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

TIMEOUT="$(find_tool timeout || true)"
if [ -n "$TIMEOUT" ]; then
  run_tool() { "$TIMEOUT" 300 "$@"; }
else
  run_tool() { "$@"; }
fi

# 可写临时目录（OHOS 的 /tmp 只读，优先 TMPDIR/$HOME/tmp）
WORKDIR=""
for base in "${TMPDIR:-}" "${HOME:-}/tmp" "${HOME:-}" /tmp; do
  [ -n "$base" ] || continue
  mkdir -p "$base" 2>/dev/null || continue
  if WORKDIR="$(mktemp -d "$base/argyll-cms-test.XXXXXX" 2>/dev/null)"; then break; fi
done
[ -n "$WORKDIR" ] || { echo "FAIL: no writable temp directory" >&2; exit 1; }
trap 'rm -rf "$WORKDIR"' EXIT HUP INT TERM

cd "$WORKDIR"
cp "$REFDIR/sRGB.icm" "$REFDIR/ClayRGB1998.icm" .

PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; exit 1; }

# ── 断言 1: iccdump ref/sRGB.icm ────────────────────────────────────────
DUMP="$(run_tool "$BINDIR/iccdump" sRGB.icm 2>&1)" || fail "1/8 iccdump sRGB.icm rc=$?"
case "$DUMP" in
  *"Profile size    = 3004 bytes"*) ok "1/8 iccdump parses sRGB.icm (Profile size 3004 bytes)" ;;
  *) printf '%s\n' "$DUMP" | head -20; fail "1/8 iccdump output lacks 'Profile size    = 3004 bytes'" ;;
esac

# ── 断言 2: iccdump ref/ClayRGB1998.icm ─────────────────────────────────
DUMP2="$(run_tool "$BINDIR/iccdump" ClayRGB1998.icm 2>&1)" || fail "2/8 iccdump ClayRGB1998.icm rc=$?"
case "$DUMP2" in
  *"Device Class    = Display"*) ok "2/8 iccdump parses ClayRGB1998.icm (Device Class Display)" ;;
  *) printf '%s\n' "$DUMP2" | head -20; fail "2/8 iccdump output lacks 'Device Class    = Display'" ;;
esac

# ── 断言 3: icclu 正向 RGB→Lab ──────────────────────────────────────────
FWD="$(printf '0.200000 0.400000 0.600000\n' | run_tool "$BINDIR/icclu" -ff -ir -pl sRGB.icm 2>&1)" \
  || fail "3/8 icclu forward rc=$?"
case "$FWD" in
  *"41.521285 -4.574172 -33.493694"*) ok "3/8 icclu forward RGB(0.2,0.4,0.6) -> Lab as expected" ;;
  *) fail "3/8 icclu forward unexpected output: $FWD" ;;
esac

# ── 断言 4: icclu 反向 Lab→RGB ──────────────────────────────────────────
BWD="$(printf '49.000000 20.000000 -30.000000\n' | run_tool "$BINDIR/icclu" -fb -ir -pl sRGB.icm 2>&1)" \
  || fail "4/8 icclu backward rc=$?"
case "$BWD" in
  *"0.510883 0.413898 0.657908"*) ok "4/8 icclu backward Lab(49,20,-30) -> RGB as expected" ;;
  *) fail "4/8 icclu backward unexpected output: $BWD" ;;
esac

# ── 断言 5: RGB→Lab→RGB 往返一致性（3 组颜色）────────────────────────────
for rgb in "0.200000 0.400000 0.600000" "0.900000 0.100000 0.500000" "0.050000 0.950000 0.250000"; do
  F="$(printf '%s\n' "$rgb" | run_tool "$BINDIR/icclu" -ff -ir -pl sRGB.icm 2>&1)" || fail "5/8 forward rc=$?"
  LAB="$(printf '%s\n' "$F" | awk '{printf "%s %s %s", $(NF-3), $(NF-2), $(NF-1)}')"
  B="$(printf '%s\n' "$LAB" | run_tool "$BINDIR/icclu" -fb -ir -pl sRGB.icm 2>&1)" || fail "5/8 backward rc=$?"
  OUT="$(printf '%s\n' "$B" | awk '{printf "%s %s %s", $(NF-3), $(NF-2), $(NF-1)}')"
  [ "$OUT" = "$rgb" ] || fail "5/8 round trip $rgb -> $LAB -> $OUT differs"
done
ok "5/8 icclu RGB->Lab->RGB round trip exact for 3 colours"

# ── 断言 6: iccgamut 产出 CGATS .gam ────────────────────────────────────
GAM="$(run_tool "$BINDIR/iccgamut" sRGB.icm 2>&1)" || fail "6/8 iccgamut rc=$?"
[ -s sRGB.gam ] || { printf '%s\n' "$GAM" | head -20; fail "6/8 iccgamut did not produce sRGB.gam"; }
grep -q "^GAMUT" sRGB.gam || fail "6/8 sRGB.gam is not a CGATS gamut file: $(head -n 1 sRGB.gam)"
grep -q 'DESCRIPTOR "Argyll Gamut surface' sRGB.gam || fail "6/8 sRGB.gam descriptor unexpected"
ok "6/8 iccgamut produced CGATS gamut sRGB.gam ($(wc -c < sRGB.gam) bytes)"

# ── 断言 7: targen 产出 .ti1 图表 ───────────────────────────────────────
TARG="$(run_tool "$BINDIR/targen" -d2 -n16 chart 2>&1)" || fail "7/8 targen rc=$?"
[ -s chart.ti1 ] || { printf '%s\n' "$TARG" | head -20; fail "7/8 targen did not produce chart.ti1"; }
grep -q "^CTI1" chart.ti1 || fail "7/8 chart.ti1 is not a CGATS file"
ok "7/8 targen produced test chart chart.ti1 ($(wc -c < chart.ti1) bytes)"

# ── 断言 8: X11 链接的 GUI 二进制可加载并运行 ───────────────────────────
set +e
DWIN="$(run_tool "$BINDIR/dispwin" --version 2>&1)"
set -e
case "$DWIN" in
  *"Error loading shared library"*|*"cannot link"*|*"not found"*)
    fail "8/8 dispwin failed to load its X11 dependencies: $DWIN" ;;
  *"Version 3.5.0"*)
    ok "8/8 dispwin (X11 GUI binary) loads its Conan X11 libs and runs" ;;
  *) fail "8/8 dispwin unexpected output: $DWIN" ;;
esac

echo "[test.sh] all 8 assertions passed"
