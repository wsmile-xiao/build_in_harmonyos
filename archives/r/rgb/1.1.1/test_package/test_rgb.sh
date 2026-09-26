#!/bin/sh
# test_rgb.sh — 真实运行 rgb 1.1.1 的 showrgb 二进制并断言行为（5 条）
#
# 由 test_package/conanfile.py test() 调用：
#   $1 = 打包后的 showrgb 绝对路径
#   $2 = rgb 包根目录（用于定位随包安装的默认颜色库 share/X11/rgb.txt）
#
# POSIX sh only（HMBS [shell_getcwd]：以注入的 SHELL 执行；toybox ash 拒绝
# set -eu，故不用 set/pipefail，每条断言自己捕获退出码并打印输出）。
# showrgb text 分支不链接任何 X 库，无需 LD_PRELOAD/LD_LIBRARY_PATH 补库。
#
# 上游输出格式（showrgb.c: printf("%3u %3u %3u\t\t%s\n", ...)），
# 因此 red 那一行是 "255   0   0\t\tred"。

SHOWRGB="$1"
PKG_ROOT="$2"

if [ -z "$SHOWRGB" ]; then
    echo "FAIL: showrgb binary path not provided"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_rgb.sh","discovered":5,"passedCount":0}'
    exit 1
fi
if [ ! -x "$SHOWRGB" ]; then
    echo "FAIL: $SHOWRGB not found or not executable"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_rgb.sh","discovered":5,"passedCount":0}'
    exit 1
fi

discovered=5
passed=0

echo "[shell] $0"
echo "[bin] $SHOWRGB"
echo "[pkg] ${PKG_ROOT:-}"
echo "[env] PATH=$PATH"

# ---------------------------------------------------------------- 1
echo "[test 1/$discovered] showrgb --version"
out=$("$SHOWRGB" --version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: --version exit=$rc (expect 0)"
elif ! echo "$out" | grep -q "rgb 1.1.1"; then
    echo "FAIL: --version output lacks upstream PACKAGE_STRING 'rgb 1.1.1'"
else
    echo "PASS: showrgb --version reports 'rgb 1.1.1'"
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 2
echo "[test 2/$discovered] showrgb --help"
out=$("$SHOWRGB" --help 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: --help exit=$rc (expect 0)"
else
    echo "PASS: showrgb --help exit=0"
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 3
# 无参运行：读取编译期烧进 RGB_DB 宏的默认库（conan 包内 share/X11/rgb，
# text 模式下 showrgb 会自动补 .txt 后缀）。这条断言同时证明
# `make install` 把 rgb.txt 放到了正确位置，且二进制真的解析了它。
echo "[test 3/$discovered] showrgb (default database, no args)"
DEFAULT_DB="$PKG_ROOT/share/X11/rgb.txt"
if [ ! -f "$DEFAULT_DB" ]; then
    echo "FAIL: packaged default database missing: $DEFAULT_DB"
    def_count=0
    has_red=0
else
    out=$("$SHOWRGB" 2>/dev/null)
    rc=$?
    def_count=$(printf '%s\n' "$out" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')
    has_red=$(printf '%s\n' "$out" | awk '$1==255 && $2==0 && $3==0 && $4=="red" {c++} END{print c+0}')
    echo "  exit=$rc entries=$def_count red_matches=$has_red"
    printf '%s\n' "$out" | head -3 | sed 's/^/  | /'
    if [ $rc -ne 0 ]; then
        echo "FAIL: default-database run exit=$rc"
    elif [ "$def_count" -lt 100 ]; then
        echo "FAIL: default database parsed only $def_count entries (expect >=100)"
    elif [ "$has_red" -eq 0 ]; then
        echo "FAIL: no '255 0 0 red' entry in default database output"
    else
        echo "PASS: default database -> $def_count entries, 'red' == 255 0 0"
        passed=$((passed + 1))
    fi
fi

# ---------------------------------------------------------------- 4
# 显式库路径（man 页约定：不带 .txt 后缀），指向本脚本自造的独立小库，
# 证明 dbname 参数与 .txt 后缀拼接逻辑真的生效（不依赖包内默认路径）。
echo "[test 4/$discovered] showrgb <explicit mini database>"
WORK=./_rgbtest.$$
rm -rf "$WORK"
mkdir -p "$WORK" 2>/dev/null
cat > "$WORK/mini.txt" <<'DBEOF'
255 0 0 agentred
0 255 0 agentgreen
0 0 255 agentblue
12 34 56 agentmixed
DBEOF
out=$("$SHOWRGB" "$WORK/mini" 2>&1)
rc=$?
echo "$out" | sed 's/^/  | /'
mini_count=$(printf '%s\n' "$out" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')
mini_ok=$(printf '%s\n' "$out" | awk '$1==255 && $2==0 && $3==0 && $4=="agentred" {c++} END{print c+0}')
if [ $rc -ne 0 ]; then
    echo "FAIL: explicit database run exit=$rc"
elif [ "$mini_count" -ne 4 ]; then
    echo "FAIL: explicit database parsed $mini_count entries (expect exactly 4)"
elif [ "$mini_ok" -eq 0 ]; then
    echo "FAIL: agentred 255 0 0 entry not round-tripped"
else
    echo "PASS: explicit database -> 4 entries round-tripped, agentred == 255 0 0"
    passed=$((passed + 1))
fi
rm -rf "$WORK"

# ---------------------------------------------------------------- 5
# 错误路径：不存在的库必须非零退出并给出上游错误消息。
echo "[test 5/$discovered] showrgb <nonexistent database>"
MISSING=./_rgbtest-absent-$$/no-such-db
err=$("$SHOWRGB" "$MISSING" 2>&1)
rc=$?
echo "$err" | sed 's/^/  | /'
if [ $rc -eq 0 ]; then
    echo "FAIL: nonexistent database exited 0 (expect non-zero)"
elif ! echo "$err" | grep -q "unable to open rgb database"; then
    echo "FAIL: expected upstream message 'unable to open rgb database'"
else
    echo "PASS: nonexistent database -> exit=$rc with upstream error message"
    passed=$((passed + 1))
fi

# ---------------------------------------------------------------- 汇总
if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_rgb.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed (default-db entries=$def_count)"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_rgb.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
