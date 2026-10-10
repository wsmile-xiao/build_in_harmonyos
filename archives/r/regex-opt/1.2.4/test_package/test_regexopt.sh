#!/bin/sh
# test_regexopt.sh — 真实运行 regex-opt 1.2.4 打包二进制并断言行为（8 条）
#
# 由 test_package/conanfile.py test() 调用：
#   $1 = 打包后的 regex-opt 绝对路径
#
# POSIX sh only（HMBS [shell_getcwd]：以注入的 SHELL 执行；toybox ash 拒绝
# set -eu，故不用 set/pipefail，每条断言自己捕获退出码并打印输出）。
# regex-opt 为纯 C++ 工具（main.cc + libregex.a），不链接任何第三方库，
# 无需 LD_PRELOAD/LD_LIBRARY_PATH 补库；打包二进制已在 package() 按 E077
# 自签名，可直接执行。
#
# 期望输出通过本机 g++ 实测上游源码（v1.2.4）得到，与 bisqwit.iki.fi 的
# README 示例一致。

REGEXOPT="$1"

if [ -z "$REGEXOPT" ]; then
    echo "FAIL: regex-opt binary path not provided"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_regexopt.sh","discovered":8,"passedCount":0}'
    exit 1
fi
if [ ! -x "$REGEXOPT" ]; then
    echo "FAIL: $REGEXOPT not found or not executable"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_regexopt.sh","discovered":8,"passedCount":0}'
    exit 1
fi

discovered=8
passed=0

echo "[shell] $0"
echo "[bin] $REGEXOPT"
echo "[env] PATH=$PATH"

# run_opt <regexp> <expected-output> [<expected-rc>]
# 运行二进制并断言 stdout 精确等于期望输出、退出码等于期望（默认 0）。
run_opt() {
    _pattern=$1
    _expect=$2
    _want_rc=${3:-0}
    _out=$("$REGEXOPT" "$_pattern" 2>&1)
    _rc=$?
    if [ "$_rc" -ne "$_want_rc" ]; then
        echo "  FAIL: '$1' exit=$_rc (expect $_want_rc), out=[$_out]"
        return 1
    fi
    if [ "$_out" != "$_expect" ]; then
        echo "  FAIL: '$1' out=[$_out] (expect [$_expect])"
        return 1
    fi
    echo "  PASS: '$1' -> [$_out] (rc=$_rc)"
    return 0
}

# ---------------------------------------------------------------- 1
echo "[test 1/$discovered] xaz|xbz|xcz -> x[a-c]z"
if run_opt 'xaz|xbz|xcz' 'x[a-c]z'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 2
echo "[test 2/$discovered] aaa* -> a{2,}"
if run_opt 'aaa*' 'a{2,}'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 3
echo "[test 3/$discovered] (a?){3} -> a{0,3}"
if run_opt '(a?){3}' 'a{0,3}'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 4
echo "[test 4/$discovered] xyzyzxyzyz -> (?:x(?:yz){2}){2}"
if run_opt 'xyzyzxyzyz' '(?:x(?:yz){2}){2}'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 5
echo "[test 5/$discovered] a+|aa+ -> a+"
if run_opt 'a+|aa+' 'a+'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 6
echo "[test 6/$discovered] dxxxxb|dxxxb|dxxb|dxb -> dx{1,4}b"
if run_opt 'dxxxxb|dxxxb|dxxb|dxb' 'dx{1,4}b'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 7
echo "[test 7/$discovered] y|[yp]|[zx] -> [px-z]"
if run_opt 'y|[yp]|[zx]' '[px-z]'; then
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 8
# 错误路径：非法正则（未闭合的字符类）必须非零退出并打印 "Error:" 前缀。
echo "[test 8/$discovered] invalid '[abc' -> non-zero exit + Error:"
_out=$("$REGEXOPT" '[abc' 2>&1)
_rc=$?
echo "  out=[$_out] rc=$_rc"
if [ "$_rc" -eq 0 ]; then
    echo "  FAIL: invalid regexp exited 0 (expect non-zero)"
elif ! echo "$_out" | grep -q '^Error:'; then
    echo "  FAIL: invalid regexp output lacks 'Error:' prefix: [$_out]"
else
    echo "  PASS: invalid regexp -> rc=$_rc with 'Error:' prefix"
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 汇总
if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_regexopt.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_regexopt.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
