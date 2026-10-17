#!/bin/sh
# test_wmcalc.sh — wmcalc/0.7 消费者测试（R34：真实执行被测二进制）
#
# 6 条断言，计数与 test_package/MANIFEST.yml 的 assertion_count、
# reports/test-report.md、notes.md 四载体同口径。
# 设备实测：/bin/bash 与 /usr/bin/python3 均 MISSING，只有 /bin/sh（toybox ash）
# ⇒ POSIX sh 写法，不用 set -eu / pipefail（xidle、xeyes 已过门禁同款）。
#
# 用法: sh test_wmcalc.sh <path-to-wmcalc-binary>

BIN="$1"
pass=0
fail=0

ok() {
    pass=$((pass + 1))
    echo "PASS $1"
}

ko() {
    fail=$((fail + 1))
    echo "FAIL $1"
}

# A1 —— 被测包真的产出了非空二进制
if [ -n "$BIN" ] && [ -f "$BIN" ] && [ -s "$BIN" ]; then
    ok "A1 binary-present"
else
    ko "A1 binary-present ($BIN)"
fi

# A2 —— `wmcalc -h` 退出码 0（show_usage() 在 XOpenDisplay 之前 exit(OKAY)）
HELP_OUT=`"$BIN" -h 2>&1`
HELP_RC=$?
if [ "$HELP_RC" = "0" ]; then
    ok "A2 help-exit0"
else
    ko "A2 help-exit0 (rc=$HELP_RC)"
    echo "--- help output ---"
    echo "$HELP_OUT"
fi

# A3 —— 输出含程序名（app_name 常量，wmcalc.c:78）
case "$HELP_OUT" in
    *wmcalc*) ok "A3 banner-app-name" ;;
    *) ko "A3 banner-app-name" ;;
esac

# A4 —— 输出含编译期版本宏 PACKAGE_VERSION=0.7（configure DEFS 注入，非脚本回显）
case "$HELP_OUT" in
    *"wmcalc 0.7"*) ok "A4 banner-version" ;;
    *) ko "A4 banner-version" ;;
esac

# A5 —— usage 面板与 man page 同源（-g/-d/-f/-v/-h 五个选项齐全）
if echo "$HELP_OUT" | grep -q "usage:" &&
   echo "$HELP_OUT" | grep -q -- "-g  <geometry>" &&
   echo "$HELP_OUT" | grep -q -- "-d  <display>" &&
   echo "$HELP_OUT" | grep -q -- "-f  <filename>" &&
   echo "$HELP_OUT" | grep -q -- "-v  " &&
   echo "$HELP_OUT" | grep -q -- "-h  "; then
    ok "A5 usage-option-panel"
else
    ko "A5 usage-option-panel"
    echo "--- help output ---"
    echo "$HELP_OUT"
fi

# A6 —— 无 X display 的真实失败形态：非 0 退出 + error_handler 的 display 报错
#       （wmcalc.c:153 XOpenDisplay 失败 -> ERR_X_DISPLAY -> exit(err_code)）
DISP_OUT=`"$BIN" -d :99 2>&1`
DISP_RC=$?
if [ "$DISP_RC" != "0" ] && echo "$DISP_OUT" | grep -qi "display"; then
    ok "A6 headless-display-failure (rc=$DISP_RC)"
else
    ko "A6 headless-display-failure (rc=$DISP_RC)"
    echo "--- display attempt output ---"
    echo "$DISP_OUT"
fi

echo "SUMMARY assertions=$pass/$((pass + fail)) passed, $fail failed"
if [ "$fail" != "0" ]; then
    exit 1
fi
exit 0
