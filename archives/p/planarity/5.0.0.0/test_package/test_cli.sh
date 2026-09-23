#!/data/service/hnp/bin/bash
# test_package/test_cli.sh — planarity 命令行工具的消费者测试（鸿蒙特有）
#
# 由 test_package/conanfile.py 的 test() 在 conanrun 环境下调用：
#   test_cli.sh <planarity 二进制绝对路径>
# 调用方传入安装树内的绝对路径（不依赖 PATH / VirtualRunEnv 的隐式行为）；
# 未传参时回退到 `command -v planarity`。
#
# 覆盖：-h 帮助/版本输出、安装树自带 samples 上的完整上游 -test 套件、
#       以及平面/非平面功能性出口码（K4 → 0，K3,3 → 1）。
#
# 注意：不使用 `mktemp -d` —— HMDFS 上 `umask 077 && mkdir` 产生的
# drwx--S--- 目录连创建者都不可写（E011/E129）；这里用默认 umask 的 mkdir。
set -u

fail=0
total=0
check() { # check <期望rc> <实际rc> <说明>
    total=$((total + 1))
    if [ "$1" -eq "$2" ]; then
        echo "  [PASS] $3 (rc=$2)"
    else
        echo "  [FAIL] $3 (期望 rc=$1，实际 rc=$2)"
        fail=$((fail + 1))
    fi
}

# 定位被测可执行文件：优先用调用方给的绝对路径
bin="${1:-}"
if [ -z "$bin" ] || [ ! -x "$bin" ]; then
    bin="$(command -v planarity 2>/dev/null || true)"
fi
if [ -z "$bin" ] || [ ! -x "$bin" ]; then
    echo "[FATAL] 未找到可执行的 planarity（参数='${1:-}'，PATH=$PATH）"
    exit 1
fi
bindir="$(cd "$(dirname "$bin")" && pwd)"
prefix="$(cd "$bindir/.." && pwd)"
samples="$prefix/share/doc/planarity/samples"
if [ ! -d "$samples" ]; then
    echo "[FATAL] 安装树缺少 samples 目录：$samples"
    exit 1
fi

base="${TMPDIR:-/tmp}"
if [ ! -d "$base" ] || [ ! -w "$base" ]; then
    base="."
fi
work="$base/planarity-cli-$$"
mkdir -p "$work" || { echo "无法创建测试目录 $work"; exit 1; }
trap 'rm -rf "$work"' EXIT

echo "== planarity CLI 消费者测试（二进制：$bin）=="

# 1) 帮助/版本
"$bin" -h > "$work/help.txt" 2>&1
check 0 $? "planarity -h 返回 0"
grep -q "Edge Addition Planarity Suite version 5.0.0.0" "$work/help.txt"
check 0 $? "planarity -h 输出含 'Edge Addition Planarity Suite version 5.0.0.0'"

# 2) 安装树自带 samples：完整跑一遍上游 -test 套件
"$bin" -test "$samples" > "$work/upstream-test.log" 2>&1
check 0 $? "planarity -test <安装树 samples> 返回 0"
grep -q "All tests have succeeded" "$work/upstream-test.log"
check 0 $? "上游 -test 输出含 'All tests have succeeded'"

# 3) 功能性出口码：平面图 0 / 非平面图 1
printf 'N=4\n0: 1 2 3 -1\n1: 0 2 3 -1\n2: 0 1 3 -1\n3: 0 1 2 -1\n' > "$work/K4.AdjList.txt"
printf 'N=6\n0: 3 4 5 -1\n1: 3 4 5 -1\n2: 3 4 5 -1\n3: 0 1 2 -1\n4: 0 1 2 -1\n5: 0 1 2 -1\n' > "$work/K33.AdjList.txt"

"$bin" -s -q -p "$work/K4.AdjList.txt" "$work/K4.embed" > "$work/k4.log" 2>&1
check 0 $? "planarity -s -q -p K4 → rc=0（平面）"
[ -s "$work/K4.embed" ]
check 0 $? "K4 平面嵌入输出文件非空"

"$bin" -s -q -p "$work/K33.AdjList.txt" "$work/K33.embed" > "$work/k33.log" 2>&1
check 1 $? "planarity -s -q -p K3,3 → rc=1（非平面）"

echo "CLI ASSERTIONS: $((total - fail))/$total"
if [ "$fail" -ne 0 ]; then
    echo "FAILED CLI assertions: $fail"
    exit 1
fi
echo "ALL CLI ASSERTIONS PASSED"
exit 0
