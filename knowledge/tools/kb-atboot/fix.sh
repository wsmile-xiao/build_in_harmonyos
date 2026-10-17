#!/data/service/hnp/bin/bash
# fix.sh — KB-ATBOOT 修复器：config.guess/sub 注入 + maintainer-mode 时间戳序修复
#
# 处理策略（对应 detect.sh 的两类命中）：
#   A 类（缺 config.guess/config.sub）→ 从 autoconf 归档注入（官方上游脚本，
#      非 fork、无本地路径依赖），注入后 chmod +x。
#   B 类（mtime 倒挂）→ os.utime 对齐：被生成者 mtime = max(生成者 mtime, 被生成者现值)
#      保证 Makefile.in: Makefile.am / configure: configure.ac 依赖序成立，
#      掐断 make 对 missing automake 的重生成触发。
#
# 用法：
#   fix.sh --src <源码目录> [--autoconf-dir <含config.guess/sub的目录>]
#   退出码：0=已修复或无需修复  非0=修复失败
#
# 幂等：重复运行安全。只动 autotools 引导文件，不碰库源码逻辑。
# OHOS aarch64 环境：使用 /data/service/hnp/bin/bash。

set -u

SRC=""
AUTOCONF_DIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --src) SRC="$2"; shift 2 ;;
        --autoconf-dir) AUTOCONF_DIR="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

[ -z "$SRC" ] && { echo "ERROR: --src required" >&2; exit 64; }
[ -d "$SRC" ] || { echo "ERROR: not a directory: $SRC" >&2; exit 64; }

# ---------- 定位 autoconf 归档源 ----------
# 优先级：SKILL 自带 vendor/（随本 PR 入仓，任何机器可用）> 显式 --autoconf-dir
#   > 环境变量 KB_ATBOOT_AUTOCONF_DIR > 常见系统位置。
# 禁止写死设备本地绝对路径作为唯一来源：全部落空时按"降级模式"继续
# （只修时间戳，不注入 config.guess/sub，并在 stderr 明确告警）。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
find_autoconf_dir() {
    if [ -f "$SCRIPT_DIR/vendor/config.guess" ] && [ -f "$SCRIPT_DIR/vendor/config.sub" ]; then
        echo "$SCRIPT_DIR/vendor"; return 0
    fi
    if [ -n "$AUTOCONF_DIR" ] && [ -f "$AUTOCONF_DIR/config.guess" ]; then
        echo "$AUTOCONF_DIR"; return 0
    fi
    if [ -n "${KB_ATBOOT_AUTOCONF_DIR:-}" ] && [ -f "$KB_ATBOOT_AUTOCONF_DIR/config.guess" ]; then
        echo "$KB_ATBOOT_AUTOCONF_DIR"; return 0
    fi
    for d in /data/service/hnp/share/autoconf \
             /usr/share/autoconf \
             /usr/share/misc; do
        [ -f "$d/config.guess" ] && { echo "$d"; return 0; }
    done
    return 1
}

FIXED_A=0
FIXED_B=0

CONF_DIR=""
for c in "$SRC/configure" "$SRC"/*/configure; do
    [ -f "$c" ] && CONF_DIR="$(dirname "$c")" && break
done
[ -z "$CONF_DIR" ] && { echo "no configure found under $SRC; nothing to fix" >&2; exit 0; }

# ---------- A 类修复：注入 config.guess / config.sub ----------
NEED_GUESS=1; NEED_SUB=1
for d in "$CONF_DIR" "$CONF_DIR/build-aux" "$CONF_DIR/config" "$CONF_DIR/autoconf"; do
    [ -f "$d/config.guess" ] && NEED_GUESS=0
    [ -f "$d/config.sub" ]   && NEED_SUB=0
done
if [ "$NEED_GUESS" -eq 1 ] || [ "$NEED_SUB" -eq 1 ]; then
    AC_DIR="$(find_autoconf_dir)" || AC_DIR=""
    if [ -z "$AC_DIR" ]; then
        echo "WARN: no autoconf archive found (set KB_ATBOOT_AUTOCONF_DIR); skipping config.guess/sub injection" >&2
    else
        TARGET=""
        # 优先 build-aux/（现代惯例），否则 configure 同级
        for d in "$CONF_DIR/build-aux" "$CONF_DIR/config" "$CONF_DIR"; do
            [ -d "$d" ] && TARGET="$d" && break
        done
        [ -z "$TARGET" ] && TARGET="$CONF_DIR" && mkdir -p "$TARGET"
        if [ "$NEED_GUESS" -eq 1 ]; then
            cp "$AC_DIR/config.guess" "$TARGET/config.guess" \
                && chmod 755 "$TARGET/config.guess" \
                && echo "FIX-A: injected config.guess -> $TARGET" \
                && FIXED_A=$((FIXED_A+1))
        fi
        if [ "$NEED_SUB" -eq 1 ]; then
            cp "$AC_DIR/config.sub" "$TARGET/config.sub" \
                && chmod 755 "$TARGET/config.sub" \
                && echo "FIX-A: injected config.sub -> $TARGET" \
                && FIXED_A=$((FIXED_A+1))
        fi
    fi
fi

# ---------- B 类修复：时间戳序对齐 ----------
# B 类配套（HMDFS/E046）：老 config.status 内嵌 `umask 077` 建临时目录，
# HMDFS 下 700 目录不可写，config.status 半途失败 → Makefile 全部缺失。
# 与 commoncpp2/io_lib 的 0002 补丁同源：umask 077 → 022。
if [ -f "$CONF_DIR/configure" ] && grep -q "umask 077" "$CONF_DIR/configure" 2>/dev/null; then
    sed -i 's/umask 077/umask 022/g' "$CONF_DIR/configure" \
        && echo "FIX-B: configure umask 077 -> 022 (HMDFS tmpdir writable)" \
        && FIXED_B=$((FIXED_B+1))
fi

align() {
    # align <generated> <generator>：generated.mtime = max(generator.mtime, generated.mtime)
    [ -f "$1" ] && [ -f "$2" ] || return 0
    g1="$(stat -c %Y "$1" 2>/dev/null)" || return 0
    g2="$(stat -c %Y "$2" 2>/dev/null)" || return 0
    if [ "$g1" -lt "$g2" ]; then
        ns="$(stat -c %Y "$2")000000000"
        touch -d "@$g2" "$1" 2>/dev/null || touch -r "$2" "$1"
        echo "FIX-B: realigned $(basename "$1") >= $(basename "$2")"
        FIXED_B=$((FIXED_B+1))
    fi
}

align "$CONF_DIR/configure" "$CONF_DIR/configure.ac"
align "$CONF_DIR/configure" "$CONF_DIR/configure.in"
align "$CONF_DIR/aclocal.m4" "$CONF_DIR/configure.ac"
for am in "$CONF_DIR"/Makefile.am; do
    [ -f "$am" ] && align "${am%.am}.in" "$am"
done
for sub in "$CONF_DIR"/*/; do
    [ -f "$sub/Makefile.am" ] && align "$sub/Makefile.in" "$sub/Makefile.am"
done

echo "KB-ATBOOT fix done: A=$FIXED_A file(s) injected, B=$FIXED_B pair(s) realigned"
[ "$FIXED_A" -gt 0 ] || [ "$FIXED_B" -gt 0 ] || [ "$NEED_GUESS" -eq 0 -a "$NEED_SUB" -eq 0 ]
