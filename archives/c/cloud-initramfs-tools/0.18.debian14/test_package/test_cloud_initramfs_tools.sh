#!/data/service/hnp/bin/bash
# test_package/test_cloud_initramfs_tools.sh
# cloud-initramfs-tools 0.18.debian14 —— 消费者视角测试套件（对已安装包执行）
#
# 组 A 上游交付物验证：直接执行上游交付的 hook/脚本/CLI/配置（上游无自动化测试，见 MANIFEST.yml）
# 组 B 包布局契约
# 组 C 鸿蒙特有用例（≥1；本机为 HarmonyOS PC，全部实际执行）
#
# 用法: bash test_cloud_initramfs_tools.sh <package_folder>

set -u

PKG="${1:?usage: test_cloud_initramfs_tools.sh <package_folder>}"
HOOKS="$PKG/share/initramfs-tools/hooks"
SCRIPTS="$PKG/share/initramfs-tools/scripts"
CONF_HOOKS="$PKG/share/initramfs-tools/conf-hooks.d"
CLI="$PKG/bin/overlayroot-chroot"
MAN8="$PKG/share/man/man8/overlayroot-chroot.8"
RES_CONF="$PKG/res/etc/overlayroot.conf"
RES_MOTD="$PKG/res/etc/update-motd.d/97-overlayroot"
LICENSE="$PKG/licenses/COPYING"
SH=/bin/sh

# ── 计数器 ────────────────────────────────────────────────────────────
CASES=0; PASSED=0; FAILED=0; SKIPPED=0; ASSERTIONS=0
declare -a CASE_LOG=()
CUR=""

case_begin() { CUR="$1"; CASES=$((CASES+1)); echo "── [$(printf '%02d' $CASES)] $CUR"; }
case_pass()  { PASSED=$((PASSED+1)); CASE_LOG+=("PASS     $CUR"); echo "   ✅ PASS  $CUR"; }
case_fail()  { FAILED=$((FAILED+1)); CASE_LOG+=("FAIL     $CUR :: $1"); echo "   ❌ FAIL  $CUR :: $1"; }
case_skip()  { SKIPPED=$((SKIPPED+1)); CASE_LOG+=("SKIP     $CUR :: $1"); echo "   ⏭️  SKIP  $CUR :: $1"; }

a_true() { ASSERTIONS=$((ASSERTIONS+1)); if "$@" >/dev/null 2>&1; then return 0; fi
           echo "      · 断言失败: $*"; return 1; }
a_eq()   { ASSERTIONS=$((ASSERTIONS+1)); if [ "$1" = "$2" ]; then return 0; fi
           echo "      · 断言失败: 期望 [$1] 实际 [$2]"; return 1; }
a_has()  { ASSERTIONS=$((ASSERTIONS+1)); case "$1" in *"$2"*) return 0;; esac
           echo "      · 断言失败: [$1] 不含 [$2]"; return 1; }
a_absent(){ ASSERTIONS=$((ASSERTIONS+1)); case "$1" in *"$2"*) echo "      · 断言失败: [$1] 不应含 [$2]"; return 1;; esac
           return 0; }

# 平台判定（C 组用例是否适用）
IS_OHOS=0
uname -a 2>/dev/null | grep -qiE "harmonyos|hongmeng" && IS_OHOS=1
echo "平台: $(uname -s -m 2>/dev/null) | 内核: $(uname -r 2>/dev/null) | OHOS=$IS_OHOS | $SH=$($SH -c 'echo $0')"

# 可写临时目录（OHOS /tmp 只读 → 优先 $TMPDIR / $HOME/tmp）
pick_tmp() {
  for d in "${TMPDIR:-}" "$HOME/tmp" /tmp; do
    [ -n "$d" ] && [ -d "$d" ] && [ -w "$d" ] && { echo "$d"; return; }
  done
  echo "$(pwd)"
}
TMPROOT="$(pick_tmp)/cift-suite-$$"
mkdir -p "$TMPROOT" || { echo "无法创建临时目录"; exit 1; }
cleanup() { rm -rf "$TMPROOT" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# ═══════════════════════════════════════════════════════════════════════
# 组 A —— 上游交付物验证（真实执行上游交付的入口）
# ═══════════════════════════════════════════════════════════════════════

# A1 上游 4 个 initramfs hook 的 prereqs 协议
case_begin "A1 upstream-hook-prereqs-protocol"
if [ ! -x "$HOOKS/overlayroot" ]; then
  case_fail "缺少可执行 hook $HOOKS/overlayroot"
else
  r=""; ok=1
  out=$($SH "$HOOKS/overlayroot" prereqs 2>&1); rc=$?
  { a_eq 0 "$rc" && a_eq "cryptsetup" "$out"; } || ok=0
  for h in growroot rescuevol cloud-initramfs-dyn-netconf; do
    out=$($SH "$HOOKS/$h" prereqs 2>&1); rc=$?
    { a_eq 0 "$rc" && a_eq "" "$out"; } || ok=0
  done
  [ $ok -eq 1 ] && case_pass || case_fail "hook prereqs 协议不符"
fi

# A2 上游 5 个 initramfs 阶段脚本的 prereqs 协议
case_begin "A2 upstream-stage-script-prereqs-protocol"
ok=1
for rel in init-bottom/overlayroot init-bottom/cloud-initramfs-dyn-netconf \
           init-top/cloud-initramfs-dyn-netconf local-bottom/growroot \
           local-premount/rescuevol; do
  [ -x "$SCRIPTS/$rel" ] || { echo "      · 缺少 $SCRIPTS/$rel"; ok=0; continue; }
  out=$($SH "$SCRIPTS/$rel" prereqs 2>&1); rc=$?
  a_eq 0 "$rc" || ok=0
done
out=$($SH "$SCRIPTS/init-top/cloud-initramfs-dyn-netconf" prereqs 2>&1)
a_eq "udev" "$out" || ok=0
[ $ok -eq 1 ] && case_pass || case_fail "阶段脚本 prereqs 协议不符"

# A3 上游 CLI overlayroot-chroot：无 overlayroot 挂载时确定性失败路径
case_begin "A3 upstream-cli-failpath-without-overlayroot"
if [ ! -x "$CLI" ]; then
  case_fail "缺少可执行 CLI $CLI"
else
  out=$($SH "$CLI" /bin/true 2>&1); rc=$?
  ok=1
  a_eq 1 "$rc" || ok=0
  a_has "$out" "Unable to find an overlayroot filesystem" || ok=0
  [ $ok -eq 1 ] && case_pass || case_fail "CLI 失败路径不符 (rc=$rc)"
fi

# A4 上游 CLI 补丁引入的 xcmd()：优先原名，缺名回退 busybox applet
case_begin "A4 upstream-cli-xcmd-resolver-both-branches"
FN="$(awk '/^xcmd\(\) \{/,/^\}/' "$CLI" 2>/dev/null)"
if [ -z "$FN" ]; then
  case_fail "无法从包内 CLI 提取 xcmd() 函数体"
else
  ok=1
  D="$TMPROOT/resolver"; mkdir -p "$D/plain" "$D/multi"
  printf '#!/bin/sh\necho "PLAIN-CALL $*"\nexit 0\n' > "$D/plain/umount"; chmod +x "$D/plain/umount"
  printf '#!/bin/sh\necho "BUSYBOX-CALL $*"\nexit 0\n' > "$D/multi/busybox"; chmod +x "$D/multi/busybox"
  # (a) 原名存在 → 走原名（与上游行为一致）
  out=$(PATH="$D/plain" $SH -c "fail(){ exit 1; }; $FN
xcmd umount --probe" 2>&1)
  { a_eq "PLAIN-CALL --probe" "$out"; } || ok=0
  # (b) 原名缺失、busybox 可用 → 回退 busybox <applet>
  out=$(PATH="$D/multi" $SH -c "fail(){ exit 1; }; $FN
xcmd umount --probe" 2>&1)
  { a_eq "BUSYBOX-CALL umount --probe" "$out"; } || ok=0
  [ $ok -eq 1 ] && case_pass || case_fail "xcmd 解析分支不符"
fi

# A5 上游配置文件默认值（overlayroot 默认 disabled → overlayroot=""）
case_begin "A5 upstream-overlayroot-conf-default-disabled"
if [ ! -f "$RES_CONF" ]; then
  case_fail "缺少 $RES_CONF"
else
  out=$($SH -c '. "$1" >/dev/null 2>&1; printf "%s" "${overlayroot-UNSET}"' _ "$RES_CONF" 2>&1); rc=$?
  ok=1
  a_eq 0 "$rc" || ok=0
  a_eq "" "$out" || ok=0
  [ $ok -eq 1 ] && case_pass || case_fail "配置默认值不符 (rc=$rc out=[$out])"
fi

# ═══════════════════════════════════════════════════════════════════════
# 组 B —— 包布局契约
# ═══════════════════════════════════════════════════════════════════════

# B1 hooks（4 个且可执行）
case_begin "B1 pkg-layout-initramfs-hooks"
ok=1
for h in overlayroot growroot rescuevol cloud-initramfs-dyn-netconf; do
  { a_true test -f "$HOOKS/$h" && a_true test -x "$HOOKS/$h"; } || ok=0
done
[ $ok -eq 1 ] && case_pass || case_fail "hooks 缺失或不可执行"

# B2 阶段脚本（5 个且可执行）
case_begin "B2 pkg-layout-initramfs-stage-scripts"
ok=1
for rel in init-bottom/overlayroot init-bottom/cloud-initramfs-dyn-netconf \
           init-top/cloud-initramfs-dyn-netconf local-bottom/growroot \
           local-premount/rescuevol; do
  { a_true test -f "$SCRIPTS/$rel" && a_true test -x "$SCRIPTS/$rel"; } || ok=0
done
[ $ok -eq 1 ] && case_pass || case_fail "阶段脚本缺失或不可执行"

# B3 conf-hooks.d 片段内容
case_begin "B3 pkg-layout-conf-hooks-d-content"
if [ ! -f "$CONF_HOOKS/overlayroot" ]; then
  case_fail "缺少 $CONF_HOOKS/overlayroot"
else
  content="$(tr -d '\r\n' < "$CONF_HOOKS/overlayroot")"
  { a_eq "export CRYPTSETUP=y" "$content"; } && case_pass || case_fail "内容不符 [$content]"
fi

# B4 唯一可执行件 bin/overlayroot-chroot
case_begin "B4 pkg-layout-cli-binary"
{ a_true test -f "$CLI" && a_true test -x "$CLI"; } && case_pass || case_fail "CLI 缺失或不可执行"

# B5 man 手册
case_begin "B5 pkg-layout-man-page"
ok=1
a_true test -s "$MAN8" || ok=0
a_has "$(head -1 "$MAN8" 2>/dev/null)" ".TH" || ok=0
[ $ok -eq 1 ] && case_pass || case_fail "man 页缺失或非 roff"

# B6 OHOS 可写位置配置资产（res/etc）
case_begin "B6 pkg-layout-res-etc-assets"
ok=1
a_true test -s "$RES_CONF" || ok=0
sz=$(wc -c < "$RES_CONF" 2>/dev/null || echo 0)
a_true test "$sz" -ge 1000 || ok=0
{ a_true test -f "$RES_MOTD" && a_true test -x "$RES_MOTD"; } || ok=0
[ $ok -eq 1 ] && case_pass || case_fail "res/etc 资产缺失 (conf=${sz}B)"

# B7 许可证随包
case_begin "B7 pkg-layout-license"
{ a_true test -s "$LICENSE"; } && case_pass || case_fail "licenses/COPYING 缺失"

# ═══════════════════════════════════════════════════════════════════════
# 组 C —— 鸿蒙特有用例（OHOS PC 实际执行；非 OHOS 平台显式 SKIP 并说明原因）
# ═══════════════════════════════════════════════════════════════════════

# C1 平台 shell 为 Toybox（非 bash 系）时，全部 11 个 shell 交付物语法自洽
case_begin "C1 ohos-toybox-sh-syntax-all-artifacts"
if [ "$IS_OHOS" -ne 1 ]; then
  case_skip "非 HarmonyOS 平台（uname 无 harmonyos/hongmeng）——鸿蒙 shell 语法检查不适用"
else
  ok=1
  n=0
  for f in "$HOOKS"/* "$SCRIPTS"/*/* "$RES_MOTD" "$CLI"; do
    [ -f "$f" ] || continue
    head -1 "$f" 2>/dev/null | grep -q '^#!' || continue
    $SH -n "$f" || { echo "      · sh -n 失败: $f"; ok=0; }
    n=$((n+1))
  done
  a_eq 11 "$n" || ok=0          # 4 hook + 5 阶段脚本 + motd + CLI
  [ $ok -eq 1 ] && case_pass || case_fail "Toybox sh 语法检查失败（覆盖 $n 个交付物）"
fi

# C2 OHOS 多调用用户态：无同名命令时 xcmd 经真实 busybox applet 回退执行
case_begin "C2 ohos-multicall-applet-fallback-real"
if [ "$IS_OHOS" -ne 1 ]; then
  case_skip "非 HarmonyOS 平台——多调用用户态同名入口缺失现象不适用"
elif ! command -v busybox >/dev/null 2>&1; then
  case_skip "平台无 busybox，无法验证 applet 回退"
else
  ok=1
  for t in umount chroot; do
    if command -v "$t" >/dev/null 2>&1; then
      echo "      · 观测: $t 由平台提供（$(command -v "$t")）—— 原生 PATH 场景可直接解析"
    else
      echo "      · 观测: $t 无同名入口（需 applet 回退）"
    fi
    busybox --list 2>/dev/null | grep -qx "$t" || { echo "      · busybox 无 $t applet"; ok=0; }
  done
  FN2="$(awk '/^xcmd\(\) \{/,/^\}/' "$CLI" 2>/dev/null)"
  D="$TMPROOT/realmulti"; mkdir -p "$D"
  ln -sf "$(command -v busybox)" "$D/busybox"
  # PATH 中只有 busybox（无 umount 同名入口）→ 必须回退到 busybox applet（--help 不触发 syscall）
  out=$(PATH="$D" $SH -c "fail(){ echo RESOLVE-FAILED; exit 9; }; $FN2
xcmd umount --help 2>&1" 2>&1); rc=$?
  a_eq 0 "$rc" || ok=0
  a_absent "$out" "not found" || ok=0
  a_absent "$out" "RESOLVE-FAILED" || ok=0
  # 记录（不断言）真实 umount syscall 在该内核沙箱中的行为（E051: 未实现 syscall → SIGSYS 159）
  out2=$(PATH="$D" $SH -c "fail(){ exit 9; }; $FN2
xcmd umount /cift-no-such-mount" 2>&1); rc2=$?
  echo "      · 观测: 真实 umount 调用 rc=$rc2（159=SIGSYS，OHOS 沙箱未放行 umount syscall → 平台能力限制，非命令解析问题）"
  [ $ok -eq 1 ] && case_pass || case_fail "busybox applet 回退真实执行失败 (rc=$rc out=[$out])"
fi

# C3 OHOS 系统路径只读 → 佐证「配置资产放包内 res/」的适配决策
case_begin "C3 ohos-readonly-system-paths-evidence"
if [ "$IS_OHOS" -ne 1 ]; then
  case_skip "非 HarmonyOS 平台——只读系统路径前提不适用"
else
  ok=1
  probe="/etc/cift-ro-probe-$$"
  ( echo x > "$probe" ) >/dev/null 2>&1 && { echo "      · /etc 可写（与预期不符）"; rm -f "$probe"; ok=0; }
  probe2="/tmp/cift-ro-probe-$$"
  ( echo x > "$probe2" ) >/dev/null 2>&1 && { echo "      · /tmp 可写（与预期不符）"; rm -f "$probe2"; ok=0; }
  # 配置资产必须落在包内可写派发位置
  a_true test -f "$RES_CONF" || ok=0
  [ $ok -eq 1 ] && case_pass || case_fail "只读系统路径证据不符"
fi

# C4 OHOS install(1) 可见性差异 + build() 所用 busybox install shim 机制真实可用
case_begin "C4 ohos-install-shim-mechanism-real"
if [ "$IS_OHOS" -ne 1 ]; then
  case_skip "非 HarmonyOS 平台——install(1) 可见性差异不适用"
elif ! command -v busybox >/dev/null 2>&1; then
  case_skip "平台无 busybox，无法验证 install shim 机制"
else
  ok=1
  if command -v install >/dev/null 2>&1; then
    echo "      · 观测: 当前 PATH 可解析 install(1) → $(command -v install)（build() 的条件 shim 不会启用）"
  else
    echo "      · 观测: 当前 PATH 无 install(1)（需 shim；上游 make install 会以 Error 127 失败）"
  fi
  # 平台 install 是否可完成上游 Makefile 的 4 种 install 调用形式（可解析时逐项实测）
  D="$TMPROOT/shim"; mkdir -p "$D/src" "$D/dst"
  printf 'shim-payload\n' > "$D/src/f1"
  if command -v install >/dev/null 2>&1; then
    install -m 644 "$D/src/f1" "$D/dst/n1" || { echo "      · install -m 644 失败"; ok=0; }
    install -m 755 -d "$D/dst/nd"          || { echo "      · install -m 755 -d 失败"; ok=0; }
    install -m 644 -t "$D/dst" "$D/src/f1" || { echo "      · install -m 644 -t 失败"; ok=0; }
  fi
  # shim 机制：仅含 install 入口（指向 busybox）的 PATH 下完成同样的安装语义
  D_shim="$TMPROOT/shim-bin"; mkdir -p "$D_shim"
  ln -sf "$(command -v busybox)" "$D_shim/install"
  if PATH="$D_shim" $SH -c 'command -v install >/dev/null 2>&1'; then
    resolved=$(PATH="$D_shim" $SH -c 'command -v install')
    a_eq "$D_shim/install" "$resolved" || ok=0
  else
    echo "      · shim 未能提供 install 入口"; ok=0
  fi
  PATH="$D_shim" $SH -c 'install -m 644 "$1" "$2/m1"'      _ "$D/src/f1" "$D/dst" || { echo "      · shim install -m 644 失败"; ok=0; }
  PATH="$D_shim" $SH -c 'install -m 755 -d "$1"'           _ "$D/dst/msub"        || { echo "      · shim install -m 755 -d 失败"; ok=0; }
  PATH="$D_shim" $SH -c 'install -m 644 -t "$1" "$2"'      _ "$D/dst" "$D/src/f1" || { echo "      · shim install -m 644 -t 失败"; ok=0; }
  PATH="$D_shim" $SH -c 'install -m 755 "$1" "$2/m2"'      _ "$D/src/f1" "$D/dst" || { echo "      · shim install -m 755 失败"; ok=0; }
  a_true test -f "$D/dst/m1" || ok=0
  a_true test -d "$D/dst/msub" || ok=0
  a_true test -f "$D/dst/f1" || ok=0
  a_true test -x "$D/dst/m2" || ok=0
  a_eq "shim-payload" "$(cat "$D/dst/m1" 2>/dev/null)" || ok=0
  cmp -s "$D/src/f1" "$D/dst/m1" || { echo "      · shim 产物与源字节不一致"; ok=0; }
  [ $ok -eq 1 ] && case_pass || case_fail "busybox install shim 机制不可用"
fi

# ═══════════════════════════════════════════════════════════════════════
echo
echo "══════════════════════════════════════════════════════════════"
echo " 用例统计: 总计=$CASES 通过=$PASSED 失败=$FAILED 跳过=$SKIPPED 断言=$ASSERTIONS"
echo "──────────────────────────────────────────────────────────────"
for l in "${CASE_LOG[@]}"; do echo "  $l"; done
echo "══════════════════════════════════════════════════════════════"
[ $FAILED -eq 0 ] || exit 1
exit 0
