#!/bin/sh
# test_upstream_regression.sh — tidy 上游回归套件驱动（regression_testing/test.rb 的 POSIX sh 1:1 复刻）
#
# 平台无 Ruby/bundler，故按 test.rb 的用例语义以 sh 复刻编排：
#   每个用例 case-<name>@<exit>.<ext>：
#     tidy -lang en_us -f <res>.txt -config <conf> --tidy-mark no -o <res>.<ext> <case>
#   conf = 同名 case-<name>.conf，缺省回退 config_default.conf
#   通过 = tidy 退出码 == 期望退出码(@后数字)
#          && expects html diff 净（expects 缺失时：result 也缺失才视为匹配）
#          && expects txt  diff 净（expects txt 必须存在，与上游判据一致）
#   expects html / result html 均使用与输入用例相同的扩展名（与上游一致）
#
# 用法（真机执行，需上游源码树与 tidy 产物）：
#   TIDY_BIN=/path/to/tidy CASES_DIR=/path/to/regression_testing/cases \
#     sh test_upstream_regression.sh
set -u

TIDY_BIN=${TIDY_BIN:?need TIDY_BIN}
CASES_DIR=${CASES_DIR:?need CASES_DIR}

PASS=0
FAIL=0
WORK=$(mktemp -d)
PROG="$WORK/progress.txt"
FAILLOG="$WORK/failures.txt"
: > "$PROG"
: > "$FAILLOG"

for suite_root in "$CASES_DIR"/*-cases; do
    suite=$(basename "$suite_root" -cases)
    mkdir -p "$WORK/$suite-results"
    for f in "$suite_root"/case-*@*; do
        [ -f "$f" ] || continue
        case "$f" in
            *.html|*.xml|*.xhtml|*.htm) ;;
            *) continue ;;
        esac
        b=$(basename "$f")
        name=${b#case-}; name=${name%%@*}
        ec=${b#*@}; ec=${ec%%.*}
        ext=${b##*.}
        conf="$suite_root/case-$name.conf"
        [ -f "$conf" ] || conf="$suite_root/config_default.conf"
        if [ ! -f "$conf" ]; then
            FAIL=$((FAIL + 1))
            echo "$f NOCONF" >> "$PROG"
            continue
        fi
        rh="$WORK/$suite-results/case-$name.$ext"
        ro="$WORK/$suite-results/case-$name.txt"
        rm -f "$rh" "$ro"
        "$TIDY_BIN" -lang en_us -f "$ro" -config "$conf" --tidy-mark no -o "$rh" "$f" </dev/null >/dev/null 2>&1
        rc=$?
        exp_h="$CASES_DIR/$suite-expects/case-$name.$ext"
        st_h=""; st_o=""
        if [ -f "$exp_h" ]; then
            diff -ua "$exp_h" "$rh" >/dev/null 2>&1
            st_h=$?
        elif [ ! -f "$rh" ]; then
            st_h=0
        fi
        if [ -f "$CASES_DIR/$suite-expects/case-$name.txt" ]; then
            diff -ua "$CASES_DIR/$suite-expects/case-$name.txt" "$ro" >/dev/null 2>&1
            st_o=$?
        fi
        if [ "$rc" = "$ec" ] && [ "$st_h" = "0" ] && [ "$st_o" = "0" ]; then
            PASS=$((PASS + 1))
        else
            FAIL=$((FAIL + 1))
            echo "FAIL $f rc=$rc exp=$ec st_h=${st_h:-nil} st_o=${st_o:-nil}" >> "$FAILLOG"
        fi
        echo "$suite/$b rc=$rc" >> "$PROG"
    done
done

echo "upstream regression: pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ] || {
    echo "--- failures ---"
    cat "$FAILLOG"
    exit 1
}
