#!/bin/sh
# test_package/test_ddate.sh — functional test for the ddate binary.
# Invoked as: sh test_ddate.sh <ddate-binary-path>
# Runs in conanrun env. Prints PASS/FAIL per case plus a final
# "RESULT: N passed, M failed" line parsed by test_package/conanfile.py
# into the HMBS_TEST_PACKAGE_RESULT marker (discovered/passedCount).
set -eu

DDATE_BIN="${1:?usage: test_ddate.sh <ddate-binary>}"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
}

echo "[test] ddate binary: $DDATE_BIN"

# 1. 无参调用：输出当前 Discordian 日期（含 "Today is" 与 "YOLD"）
OUT="$("$DDATE_BIN" 2>&1)" || { bad "no-arg run exited non-zero"; OUT=""; }
case "$OUT" in
    *"Today is"*YOLD*) ok "no-arg output contains Today is + YOLD ($OUT)" ;;
    *) bad "no-arg output missing Today is/YOLD (got: $OUT)" ;;
esac

# 2. 指定日期转换：2026-01-01 -> Chaos 1, YOLD 3192（2026+1166）
OUT="$("$DDATE_BIN" 1 1 2026 2>&1)" || { bad "explicit date run exited non-zero"; OUT=""; }
case "$OUT" in
    *Chaos*"3192 YOLD"*) ok "ddate 1 1 2026 -> Chaos 3192 YOLD ($OUT)" ;;
    *) bad "ddate 1 1 2026 unexpected output (got: $OUT)" ;;
esac

# 3. 格式化年号：+%Y -> 3192
OUT="$("$DDATE_BIN" "+%Y" 1 1 2026 2>&1)" || { bad "+%Y run exited non-zero"; OUT=""; }
if [ "$OUT" = "3192" ]; then
    ok "+%Y prints 3192"
else
    bad "+%Y expected 3192 (got: $OUT)"
fi

# 4. 格式化季节：+%B -> Chaos
OUT="$("$DDATE_BIN" "+%B" 1 1 2026 2>&1)" || { bad "+%B run exited non-zero"; OUT=""; }
if [ "$OUT" = "Chaos" ]; then
    ok "+%B prints Chaos"
else
    bad "+%B expected Chaos (got: $OUT)"
fi

# 5. 非法日期拒绝：99/99/2026 -> 非零退出 + "Invalid date"
if OUT="$("$DDATE_BIN" 99 99 2026 2>&1)"; then
    bad "invalid date unexpectedly exited zero (got: $OUT)"
else
    case "$OUT" in
        *"Invalid date"*) ok "invalid date rejected ($OUT)" ;;
        *) bad "invalid date wrong message (got: $OUT)" ;;
    esac
fi

# 6. 错误参数提示：-z -> 退出码 1 + "usage:"
if OUT="$("$DDATE_BIN" -z 2>&1)"; then
    bad "-z unexpectedly exited zero (got: $OUT)"
else
    RC=$?
    case "$OUT" in
        *"usage:"*)
            if [ "$RC" = "1" ]; then
                ok "-z prints usage with exit 1"
            else
                bad "-z usage exit code $RC, expected 1"
            fi
            ;;
        *) bad "-z missing usage message (got: $OUT)" ;;
    esac
fi

echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    echo "test_package FAILED"
    exit 1
fi
echo "test_package PASSED"
