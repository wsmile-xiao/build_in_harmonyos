#!/usr/bin/env bash
# test_chkboot.sh —— chkboot 1.3 消费者测试套件（对已安装的 Conan 包执行）
#
# 用例来源：
#   [pkg-layout-*]  包布局契约（bin/ 可执行 + res/ 配置与开机集成资产）
#   [dist-000N]     Debian autopkgtest 4 用例（debian/tests/0001..0004）的场景等价移植
#                   （上游无自动化测试套件：Makefile 的 .PHONY 仅 all/install/install-*
#                    ，无 test/check 目标 —— 清点证据见 reports/test-report.md）
#   [ohos-*]        鸿蒙平台特有用例：/etc 只读下的配置覆盖、脚本在 OHOS bash 下可解析、
#                   无 zenity/xmessage 时通知前端优雅降级
#
# 用法: bash test_chkboot.sh <package_folder> [source_folder]
# 注意：刻意**不用** `set -e`——本套件要跑完全部用例并汇总 PASS/FAIL/SKIP 计数，
# 单个用例失败不应中断后续用例；`-u`（未定义变量报错）与 `-o pipefail` 照常启用。
set -uo pipefail

PKG_DIR="${1:?用法: bash test_chkboot.sh <package_folder> [source_folder]}"
BIN_DIR="$PKG_DIR/bin"
CONF="$PKG_DIR/res/default/chkboot.conf"
# OHOS 上 /tmp 只读（E002），回退目录用 $HOME/tmp
WORK="$(mktemp -d "${TMPDIR:-$HOME/tmp}/chkboot-test-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
SKIP=0
CASE_NO=0

report() {  # report <name> <PASS|FAIL|SKIP> <detail>
    CASE_NO=$((CASE_NO + 1))
    case "$2" in
        PASS) PASS=$((PASS + 1)); echo "[ok]   case $CASE_NO $1 — $3" ;;
        FAIL) FAIL=$((FAIL + 1)); echo "[fail] case $CASE_NO $1 — $3" ;;
        SKIP) SKIP=$((SKIP + 1)); echo "[skip] case $CASE_NO $1 — $3" ;;
    esac
}

# 生成一个指向独立数据目录的临时配置（BOOTDIR 指向临时目录，避免触碰真实 /boot）
mk_conf() {  # mk_conf <file> <data_dir> <bootdir>
    cat > "$1" <<EOF
BOOTDISK=$WORK/disk.img
BOOTPART=$WORK/disk.img
BOOTDIR=$3
CHKBOOT_DATA=$2
CHANGES_ALERT="boot-differences"
CHANGES_LOG="boot-differences-log"
CHKBOOT_STYLES="issue,profile"
HIGHLIGHT_COLOUR="31"
EOF
}

echo "== chkboot 1.3 消费端测试 =="
echo "   package_folder = $PKG_DIR"
echo "   CHKBOOT_CONF   = ${CHKBOOT_CONF:-<未设置>}"
echo "   bash           = $(command -v bash) ($(bash --version | head -1))"
echo ""

# ── 1. 包布局：bin/ 三个可执行文件 + 包内配置 ──
missing=""
for f in chkboot chkboot-check chkboot-desktopalert; do
    [ -x "$BIN_DIR/$f" ] || missing="$missing bin/$f"
done
[ -f "$CONF" ] || missing="$missing res/default/chkboot.conf"
if [ -z "$missing" ]; then
    report "pkg-layout-bin-and-conf" PASS "3 个可执行文件可执行 + 配置存在"
else
    report "pkg-layout-bin-and-conf" FAIL "缺失:$missing"
fi

# ── 2. 包布局：上游开机集成资产随包保留 ──
missing=""
for f in res/profile.d/chkboot-profilealert.sh res/systemd/system/chkboot.service \
         res/systemd/scripts/chkboot-bootcheck res/initcpio/chkboot \
         res/libalpm-hooks/80-chkboot-check.hook res/libalpm-hooks/99-chkboot-update.hook; do
    [ -f "$PKG_DIR/$f" ] || missing="$missing $f"
done
if [ -z "$missing" ]; then
    report "pkg-layout-boot-integration-assets" PASS "profile.d/systemd/initcpio/pacman 资产齐全"
else
    report "pkg-layout-boot-integration-assets" FAIL "缺失:$missing"
fi

# ── 3. OHOS 特有用例：全部 shell 脚本在 OHOS bash 下语法可解析 ──
bad=""
for f in "$BIN_DIR/chkboot" "$BIN_DIR/chkboot-check" "$BIN_DIR/chkboot-desktopalert" \
         "$PKG_DIR/res/profile.d/chkboot-profilealert.sh" \
         "$PKG_DIR/res/systemd/scripts/chkboot-bootcheck" \
         "$PKG_DIR/res/initcpio/chkboot"; do
    bash -n "$f" 2>"$WORK/syntax.err" || bad="$bad ${f##*/}"
done
if [ -z "$bad" ]; then
    report "ohos-script-syntax-all" PASS "6 个脚本 bash -n 全部通过（$(bash --version | head -1)）"
else
    report "ohos-script-syntax-all" FAIL "语法失败:$bad"
fi

# ── 4. dist-0001（等价 Debian autopkgtest 0001-no-changes）：无变更 → chkboot-check rc=0 ──
D1="$WORK/data1"; mkdir -p "$D1"
mk_conf "$WORK/conf1" "$D1" "$WORK/boot1"; mkdir -p "$WORK/boot1"
out="$(CHKBOOT_CONF="$WORK/conf1" "$BIN_DIR/chkboot-check" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && [ -z "$out" ]; then
    report "dist-0001-no-changes" PASS "无告警文件 → rc=0 且无输出"
else
    report "dist-0001-no-changes" FAIL "期望 rc=0/空输出，实际 rc=$rc out=$(echo "$out" | head -2 | tr '\n' ' ')"
fi

# ── 5. dist-0003（等价 0003-unack-changes）：存在未确认变更 → rc=1 且列出变更文件 ──
D3="$WORK/data3"; mkdir -p "$D3"
printf 'boot-differences\n/boot/vmlinuz 3f2b9c\n' > "$D3/boot-differences"
mk_conf "$WORK/conf3" "$D3" "$WORK/boot3"; mkdir -p "$WORK/boot3"
out="$(CHKBOOT_CONF="$WORK/conf3" "$BIN_DIR/chkboot-check" 2>&1)"; rc=$?
if [ "$rc" -eq 1 ] && echo "$out" | grep -q "CHKBOOT ALERT" && echo "$out" | grep -q "/boot/vmlinuz 3f2b9c"; then
    report "dist-0003-unack-changes" PASS "rc=1 且告警正文含变更文件与 sha512"
else
    report "dist-0003-unack-changes" FAIL "期望 rc=1 + 告警内容，实际 rc=$rc out=$(echo "$out" | head -3 | tr '\n' ' ')"
fi

# ── 6. dist-0002（等价 0002-ack-changes）：baseline → 变更 → chkboot -u 确认 → 告警消失 ──
#     chkboot 有 root 门禁（上游语义），非 root 环境无法执行 → SKIP 并给原因
if [ "${EUID:-1}" -ne 0 ]; then
    report "dist-0002-ack-changes" SKIP "chkboot 需 root（上游门禁，非 root 时 rc=1）；本环境 EUID=${EUID:-1}"
else
    D2="$WORK/data2"; B2="$WORK/boot2"; mkdir -p "$D2" "$B2"
    printf 'vmlinuz' > "$B2/vmlinuz"; printf 'diskhead' > "$WORK/disk.img"
    mk_conf "$WORK/conf2" "$D2" "$B2"
    CHKBOOT_CONF="$WORK/conf2" "$BIN_DIR/chkboot" >/dev/null 2>&1; base_rc=$?
    printf 'vmlinuz-modified' > "$B2/vmlinuz"
    CHKBOOT_CONF="$WORK/conf2" "$BIN_DIR/chkboot" >/dev/null 2>&1; chg_rc=$?
    CHKBOOT_CONF="$WORK/conf2" "$BIN_DIR/chkboot" -u >/dev/null 2>&1; upd_rc=$?
    CHKBOOT_CONF="$WORK/conf2" "$BIN_DIR/chkboot-check" >/dev/null 2>&1; chk_rc=$?
    if [ "$base_rc" -eq 0 ] && [ "$chg_rc" -eq 1 ] && [ "$upd_rc" -eq 0 ] && [ "$chk_rc" -eq 0 ]; then
        report "dist-0002-ack-changes" PASS "baseline rc=0 / 变更 rc=1 / -u rc=0 / check rc=0"
    else
        report "dist-0002-ack-changes" FAIL "baseline=$base_rc 变更=$chg_rc -u=$upd_rc check=$chk_rc（期望 0/1/0/0）"
    fi
fi

# ── 7. dist-0004（等价 0004-kernel-update）：apt 重装内核包触发钩子确认变更 ──
report "dist-0004-kernel-update" SKIP \
    "需 apt 重装 linux-image + 真实 /boot 分区 + 重启（Debian autopkgtest Restrictions: needs-root/needs-reboot/isolation-machine）；OHOS 无 apt、无 /boot 分区访问权限（实测 touch /boot → Permission denied）"

# ── 8. OHOS 特有用例：/etc 只读 → 必须能通过 CHKBOOT_CONF 使用包内配置 ──
#     依赖 conanrun 环境注入的 CHKBOOT_CONF（package_info 的 runenv_info）
if [ -z "${CHKBOOT_CONF:-}" ]; then
    report "ohos-conf-from-package-env" FAIL "conanrun 未注入 CHKBOOT_CONF（package_info runenv_info 缺失）"
else
    export CHKBOOT_CONF
    out="$("$BIN_DIR/chkboot-check" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ] && ! echo "$out" | grep -q "CHKBOOT ALERT" \
       && ! echo "$out" | grep -qE "No such file or directory|Permission denied"; then
        report "ohos-conf-from-package-env" PASS "使用包内配置 CHKBOOT_CONF=$CHKBOOT_CONF → rc=0 无误报"
    else
        report "ohos-conf-from-package-env" FAIL "rc=$rc out=$(echo "$out" | head -3 | tr '\n' ' ')"
    fi
fi

# ── 9. OHOS 特有用例：覆盖是载荷性的 —— 缺 CHKBOOT_CONF 时硬编码路径不可用会误报 ──
if [ -f /etc/default/chkboot.conf ]; then
    report "ohos-conf-override-required" SKIP "本环境存在 /etc/default/chkboot.conf，无法复现只读 /etc 场景"
else
    out="$(env -u CHKBOOT_CONF "$BIN_DIR/chkboot-check" 2>&1)"; rc=$?
    if [ "$rc" -ne 0 ] && echo "$out" | grep -q "CHKBOOT ALERT"; then
        report "ohos-conf-override-required" PASS \
            "无 CHKBOOT_CONF 时回落到上游硬编码路径 /etc/default/chkboot.conf（本平台不存在）→ 未定义变量塌缩为 / 造成误报 rc=$rc，证明覆盖必要"
    else
        report "ohos-conf-override-required" FAIL "期望回落路径下 rc≠0 且误报，实际 rc=$rc out=$(echo "$out" | head -3 | tr '\n' ' ')"
    fi
fi

# ── 10. OHOS 特有用例：无 zenity/xmessage 时通知前端优雅降级（不崩、不弹窗）──
if command -v zenity >/dev/null 2>&1 || command -v xmessage >/dev/null 2>&1; then
    report "ohos-desktopalert-degradation" SKIP "本环境存在 zenity/xmessage，跳过以避免弹出 GUI"
else
    D9="$WORK/data9"; mkdir -p "$D9"
    printf 'boot-differences\n/boot/vmlinuz 3f2b9c\n' > "$D9/boot-differences"
    mk_conf "$WORK/conf9" "$D9" "$WORK/boot9"; mkdir -p "$WORK/boot9"
    out="$(CHKBOOT_CONF="$WORK/conf9" "$BIN_DIR/chkboot-desktopalert" 2>&1)"; rc=$?
    if [ "$rc" -eq 1 ] && ! echo "$out" | grep -qiE "not found|No such file"; then
        report "ohos-desktopalert-degradation" PASS "无通知后端 → 干净退出 rc=1，无命令缺失报错"
    else
        report "ohos-desktopalert-degradation" FAIL "rc=$rc out=$(echo "$out" | head -3 | tr '\n' ' ')"
    fi
fi

echo ""
echo "== 汇总 =="
echo "TOTAL=$((PASS + FAIL + SKIP)) PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
[ "$FAIL" -eq 0 ] || exit 1
