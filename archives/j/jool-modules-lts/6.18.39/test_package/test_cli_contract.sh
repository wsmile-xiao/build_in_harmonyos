#!/usr/bin/env bash
# test_cli_contract.sh — jool-modules-lts 6.18.39 上游 CLI 行为契约测试
#
# 全部断言执行**包内真实交付的二进制**（R34：实质依赖被测包；L1e：删除/破坏包内
# 文件时本脚本必须失败）。断言对象是上游源码可稽核的行为：
#   - show_usage/show_help/show_version（src/usr/argp/main.c）
#   - JOOL_VERSION_STR = "4.1.14.0"（src/common/xlat.h：4.1.14.0）
#   - joold 无参退出码 EINVAL=22 + "Not enough arguments"（src/usr/joold/joold.c）
#   - 内核模块缺失时的 -ESRCH 优雅降级契约（src/usr/nl/core.c:277 注释：
#     "Contract: The result will contain 0 on success, -ESRCH on module likely
#     not loaded"）：打印可行动提示（"Jool's socket family doesn't seem to
#     exist" 或 socket 建立失败提示）、非零退出、不崩溃。
set -u

PKG="${1:?usage: test_cli_contract.sh <package_folder>}"
BIN="$PKG/bin"
JOOL="$BIN/jool"
JOOL_SIIT="$BIN/jool_siit"
JOOLD="$BIN/joold"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  [ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

# 运行被测命令并捕获合并输出与退出码（预期非零的场合不受 set -e 影响）
run_cmd() {
    OUT_FILE="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/jool-cli-test.$$")"
    RC=0
    "$@" >"$OUT_FILE" 2>&1 || RC=$?
    OUT="$(cat "$OUT_FILE")"
    rm -f "$OUT_FILE"
}

assert_contains() { # desc haystack needle
    case "$2" in
        *"$3"*) ok "$1" ;;
        *) bad "$1 (expected to contain: '$3')" ;;
    esac
}

assert_not_contains() { # desc haystack needle
    case "$2" in
        *"$3"*) bad "$1 (must NOT contain: '$3')" ;;
        *) ok "$1" ;;
    esac
}

assert_is_elf() { # desc file
    local magic=""
    IFS= read -r -n 4 magic < "$2" 2>/dev/null
    LC_ALL=C
    if [ "$magic" = "$(printf '\177ELF')" ]; then
        ok "$1"
    else
        bad "$1 (not an ELF executable)"
    fi
}

echo "== jool CLI 契约（上游行为实测） =="

# A. 三件套存在且可执行
for b in "$JOOL" "$JOOL_SIIT" "$JOOLD"; do
    if [ -x "$b" ]; then ok "存在且可执行: $(basename "$b")"; else bad "缺失或不可执行: $b"; fi
done

# B. ELF 魔数（交付的是真二进制，非脚本占位）
assert_is_elf "ELF 魔数: jool"        "$JOOL"
assert_is_elf "ELF 魔数: jool_siit"   "$JOOL_SIIT"
assert_is_elf "ELF 魔数: joold"       "$JOOLD"

# C. jool 无参 → show_help（main.c: argc==1 → show_help, return 0）
run_cmd "$JOOL"
[ "$RC" -eq 0 ] && ok "jool（无参）退出码 0" || bad "jool（无参）退出码 $RC（期望 0）"
assert_contains "jool（无参）打印 Usage" "$OUT" "Usage"

# D. jool --help
run_cmd "$JOOL" --help
[ "$RC" -eq 0 ] && ok "jool --help 退出码 0" || bad "jool --help 退出码 $RC（期望 0）"
assert_contains "jool --help 打印 Usage" "$OUT" "Usage"
assert_contains "jool --help 列出 --instance" "$OUT" "--instance"

# E. jool --usage（show_usage: main.c --usage → val 1000）
run_cmd "$JOOL" --usage
[ "$RC" -eq 0 ] && ok "jool --usage 退出码 0" || bad "jool --usage 退出码 $RC（期望 0）"
assert_contains "jool --usage 提及 --version" "$OUT" "--version"

# F. jool --version → JOOL_VERSION_STR（xlat.h: 4.1.14.0；show_version 纯用户态）
run_cmd "$JOOL" --version
[ "$RC" -eq 0 ] && ok "jool --version 退出码 0" || bad "jool --version 退出码 $RC（期望 0）"
[ "$OUT" = "4.1.14.0" ] && ok "jool --version 输出 4.1.14.0" \
    || bad "jool --version 输出 '$OUT'（期望 4.1.14.0）"

# G. jool_siit --version
run_cmd "$JOOL_SIIT" --version
[ "$RC" -eq 0 ] && ok "jool_siit --version 退出码 0" || bad "jool_siit --version 退出码 $RC（期望 0）"
[ "$OUT" = "4.1.14.0" ] && ok "jool_siit --version 输出 4.1.14.0" \
    || bad "jool_siit --version 输出 '$OUT'（期望 4.1.14.0）"

# H. jool_siit --help
run_cmd "$JOOL_SIIT" --help
[ "$RC" -eq 0 ] && ok "jool_siit --help 退出码 0" || bad "jool_siit --help 退出码 $RC（期望 0）"
assert_contains "jool_siit --help 打印 Usage" "$OUT" "Usage"

# I. joold 无参 → EINVAL=22 + 弃用提示 + 参数不足提示（joold.c main）
run_cmd "$JOOLD"
[ "$RC" -eq 22 ] && ok "joold（无参）退出码 22（EINVAL）" \
    || bad "joold（无参）退出码 $RC（期望 22）"
assert_contains "joold 打印弃用警告" "$OUT" "deprecated"
assert_contains "joold 打印参数不足提示" "$OUT" "Not enough arguments"

# J. 内核模块缺失时的优雅降级（-ESRCH 契约）：jool instance display
run_cmd "$JOOL" instance display
if [ "$RC" -ne 0 ] && [ "$RC" -ne 139 ] && [ "$RC" -ne 134 ]; then
    ok "jool instance display 非崩溃非零退出（rc=$RC）"
else
    bad "jool instance display 退出码 $RC（期望非零且非 139/134 崩溃）"
fi
case "$OUT" in
    *"Jool's socket family doesn't seem to exist"*|*"Could not open the socket to kernelspace"*)
        ok "jool instance display 打印可行动的降级提示" ;;
    *) bad "jool instance display 缺少降级提示，输出: $OUT" ;;
esac
assert_not_contains "jool instance display 无段错误" "$OUT" "Segmentation fault"

# K. 同一契约作用于 jool_siit instance display
run_cmd "$JOOL_SIIT" instance display
if [ "$RC" -ne 0 ] && [ "$RC" -ne 139 ] && [ "$RC" -ne 134 ]; then
    ok "jool_siit instance display 非崩溃非零退出（rc=$RC）"
else
    bad "jool_siit instance display 退出码 $RC（期望非零且非 139/134 崩溃）"
fi
case "$OUT" in
    *"Jool's socket family doesn't seem to exist"*|*"Could not open the socket to kernelspace"*)
        ok "jool_siit instance display 打印可行动的降级提示" ;;
    *) bad "jool_siit instance display 缺少降级提示，输出: $OUT" ;;
esac
assert_not_contains "jool_siit instance display 无段错误" "$OUT" "Segmentation fault"

echo "== test_cli_contract.sh 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
