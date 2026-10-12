#!/data/service/hnp/bin/bash
# detect.sh — 老旧 autotools tarball 缺失构建引导脚本检测
#
# 共性问题（KB-ATBOOT）：
#   2008~2015 年代的上游 autotools 源码包存在两类引导缺陷：
#   A. tarball 根本不含 config.guess / config.sub（或只含其一），
#      configure 一跑即报 "cannot guess build type"。
#   B. 含 maintainer-mode 时间戳链（Makefile.in:Makefile.am / configure:configure.ac
#      的 mtime 序在解包后倒挂，或 patch 触碰 .am 后倒挂），
#      make 触发 missing automake / aclocal 重生成，设备无 automake 直接 exit 127。
#
# 用法：
#   detect.sh --src <源码目录> [--log <构建日志文件>] [--json]
#   退出码：0=未命中  1=命中A（缺 config.guess/sub）  2=命中B（时间戳倒挂）  3=同时命中
#   --json 时输出 JSON 摘要到 stdout（诊断信息走 stderr）。
#
# 本脚本只读，不修改任何文件； OHOS aarch64 环境用 /data/service/hnp/bin/bash。

set -u

SRC=""
LOG=""
JSON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --src) SRC="$2"; shift 2 ;;
        --log) LOG="$2"; shift 2 ;;
        --json) JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

[ -z "$SRC" ] && { echo "ERROR: --src required" >&2; exit 64; }
[ -d "$SRC" ] || { echo "ERROR: not a directory: $SRC" >&2; exit 64; }

HIT_A=0   # missing config.guess/sub
HIT_B=0   # maintainer-mode mtime inversion
DETAIL_A=""
DETAIL_B=""

# ---------- 通道 A：源码特征扫描 ----------
# 在 configure 脚本所在目录及其 build-aux / config / 等常见位置找 config.guess/sub。
CONF_DIR=""
for c in "$SRC/configure" "$SRC"/*/configure; do
    [ -f "$c" ] && CONF_DIR="$(dirname "$c")" && break
done

if [ -n "$CONF_DIR" ]; then
    FOUND_GUESS=0
    FOUND_SUB=0
    for d in "$CONF_DIR" "$CONF_DIR/build-aux" "$CONF_DIR/config" \
             "$CONF_DIR/autoconf" "$CONF_DIR/aux" "$CONF_DIR/scripts"; do
        [ -f "$d/config.guess" ] && FOUND_GUESS=1
        [ -f "$d/config.sub" ]   && FOUND_SUB=1
    done
    if [ "$FOUND_GUESS" -eq 0 ] || [ "$FOUND_SUB" -eq 0 ]; then
        HIT_A=1
        MISSING=""
        [ "$FOUND_GUESS" -eq 0 ] && MISSING="config.guess"
        [ "$FOUND_SUB" -eq 0 ]   && MISSING="${MISSING:+$MISSING,}config.sub"
        DETAIL_A="missing autotools bootstrap scripts: $MISSING (searched configure dir + build-aux/config/autoconf/aux/scripts)"
    fi

    # ---------- 通道 B：maintainer-mode 时间戳倒挂 ----------
    # 规则：被生成者 mtime 必须 >= 生成者。检查对：
    #   configure >= configure.ac|configure.in
    #   Makefile.in >= Makefile.am（仅限与 configure 同级的直系对）
    #   aclocal.m4 >= configure.ac
    # 任一倒挂即命中（若设备无 automake 则该倒挂致命）。
    check_pair() {
        # $1=generated $2=generator  返回0=倒挂
        [ -f "$1" ] && [ -f "$2" ] || return 1
        g1="$(stat -c %Y "$1" 2>/dev/null)" || return 1
        g2="$(stat -c %Y "$2" 2>/dev/null)" || return 1
        [ "$g1" -lt "$g2" ]
    }
    INV=""
    check_pair "$CONF_DIR/configure" "$CONF_DIR/configure.ac" && INV="$INV configure<configure.ac"
    check_pair "$CONF_DIR/configure" "$CONF_DIR/configure.in" && INV="$INV configure<configure.in"
    check_pair "$CONF_DIR/aclocal.m4" "$CONF_DIR/configure.ac" && INV="$INV aclocal.m4<configure.ac"
    for am in "$CONF_DIR"/Makefile.am; do
        [ -f "$am" ] || continue
        check_pair "${am%.am}.in" "$am" && INV="$INV Makefile.in<Makefile.am"
    done
    # 递归一级子目录的 Makefile.am 对（常见 src/ test/）
    for sub in "$CONF_DIR"/*/; do
        [ -d "$sub" ] || continue
        [ -f "$sub/Makefile.am" ] || continue
        check_pair "$sub/Makefile.in" "$sub/Makefile.am" && INV="$INV ${sub#$CONF_DIR/}Makefile.in<Makefile.am"
    done
    [ -n "$INV" ] && { HIT_B=1; DETAIL_B="maintainer-mode mtime inversion:$INV"; }
fi

# ---------- 通道 C：构建日志特征扫描（可选） ----------
LOG_HIT=""
if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    # A 类日志特征
    if grep -qE "cannot guess build type|unable to guess system type|Invalid configuration .*(guess|machine)|config\.gues.*unable" "$LOG" 2>/dev/null; then
        LOG_HIT="A:configure-cannot-guess"
        HIT_A=1
        DETAIL_A="${DETAIL_A:+$DETAIL_A; }log: cannot guess build type"
    fi
    # B 类日志特征
    if grep -qE "missing automake|automake-[0-9.]+: command not found|aclocal-[0-9.]+: command not found|WARNING.*automake.*missing|configure.*error.*newer than|attempting to restart" "$LOG" 2>/dev/null; then
        LOG_HIT="$LOG_HIT B:automake-missing-regen"
        HIT_B=1
        DETAIL_B="${DETAIL_B:+$DETAIL_B; }log: missing automake regeneration"
    fi
fi

RC=$(( HIT_A + HIT_B * 2 ))
if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-ATBOOT","hit_a":%d,"hit_b":%d,"rc":%d,"detail_a":"%s","detail_b":"%s","log_hit":"%s"}\n' \
        "$HIT_A" "$HIT_B" "$RC" "$DETAIL_A" "$DETAIL_B" "${LOG_HIT}"
else
    if [ "$RC" -eq 0 ]; then
        echo "KB-ATBOOT: no hit (autotools bootstrap looks healthy)"
    else
        [ "$HIT_A" -eq 1 ] && echo "KB-ATBOOT HIT-A: $DETAIL_A"
        [ "$HIT_B" -eq 1 ] && echo "KB-ATBOOT HIT-B: $DETAIL_B"
    fi
fi
exit "$RC"
