#!/data/service/hnp/bin/bash
# test_package/test_e2e.sh — cscope 15.9 完整消费者端到端用例（鸿蒙特有测试）
#
# 消费者场景：cscope 的真实消费通道是编辑器/IDE 的 Cscope 集成（vim/emacs
# 等生成的协议客户端），其查询全部经由 `cscope -d -L -<type> <pattern>`
# 行模式接口完成——跨文件符号、函数定义、被调函数、调用者与 #include
# 关系正是索引类工具最核心的消费面。
#
# 本用例在独立临时目录内对 e2e-probe/ 微型 C 工程（5 个源文件，含跨文件
# 调用与 #include 关系）走通完整链路，共 7 例：
#   1) 源文件清单 cscope.files → cscope -b 建交叉引用库
#   2) -0 符号查询（定义 + 调用点跨文件命中）
#   3) -1 函数定义查询
#   4) -2 被调函数查询
#   5) -3 调用者查询
#   6) -8 #include 关系查询
#   7) 修改源码后 cscope -b -u 增量重建，复查新符号入索引
#
# 逐例独立判定（TEST PASS / TEST FAIL），末尾输出 TEST SUMMARY；
# 任一用例失败以退出码 1 结束（被 conan test_package 捕获为测试失败）。
#
# 用法: bash test_e2e.sh   （在 conanrun 环境运行，PATH 含已安装 bin/）
set -u

srcdir=$(cd "$(dirname "$0")" && pwd)
fixture="$srcdir/e2e-probe"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/cscope-e2e-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

cp "$fixture/main.c" "$fixture/parser.c" "$fixture/parser.h" \
   "$fixture/util.c" "$fixture/util.h" "$WORK/"
cd "$WORK"

n_pass=0
n_fail=0
ok()  { n_pass=$((n_pass + 1)); echo "TEST PASS: $1"; }
bad() { n_fail=$((n_fail + 1)); echo "TEST FAIL: $1"; }

# 行模式查询（-d 不重建库；-L 行模式），输出落到 $1
q() {
    q_out="$1"; shift
    cscope -d -f cscope.out -L "$@" > "$q_out" 2>&1
}

echo "== cscope version =="
cscope -V 2>&1 || true
echo "== workdir: $WORK =="

# ---- 1/7 建库：cscope.files 清单 → cscope -b ----
printf '%s\n' main.c parser.c parser.h util.c util.h > cscope.files
if cscope -b -f cscope.out && [ -s cscope.out ]; then
    ok "1/7 交叉引用库构建（cscope.files 清单 → cscope -b -f cscope.out）"
else
    bad "1/7 交叉引用库构建（cscope.files 清单 → cscope -b -f cscope.out）"
fi

# ---- 2/7 符号查询 -0：tokenize 定义在 util.c、调用点在 parser.c ----
q q2.out -0 tokenize
echo "----- -0 tokenize -----"; cat q2.out
if grep -q "util.c" q2.out && grep -q "parser.c" q2.out; then
    ok "2/7 符号查询 -0 tokenize（定义 util.c + 调用点 parser.c 跨文件命中）"
else
    bad "2/7 符号查询 -0 tokenize（定义 util.c + 调用点 parser.c 跨文件命中）"
fi

# ---- 3/7 函数定义 -1：parse_twice 定义于 parser.c ----
q q3.out -1 parse_twice
echo "----- -1 parse_twice -----"; cat q3.out
if grep -q "parser.c" q3.out; then
    ok "3/7 函数定义查询 -1 parse_twice（命中 parser.c）"
else
    bad "3/7 函数定义查询 -1 parse_twice（命中 parser.c）"
fi

# ---- 4/7 被调函数 -2：parse_input 调用了 tokenize、checksum ----
q q4.out -2 parse_input
echo "----- -2 parse_input -----"; cat q4.out
if grep -q "tokenize" q4.out && grep -q "checksum" q4.out && grep -q "parser.c" q4.out; then
    ok "4/7 被调函数查询 -2 parse_input（列出其调用的 tokenize + checksum 调用点）"
else
    bad "4/7 被调函数查询 -2 parse_input（列出其调用的 tokenize + checksum 调用点）"
fi

# ---- 5/7 调用者 -3：tokenize 被 parse_input 调用（parser.c） ----
q q5.out -3 tokenize
echo "----- -3 tokenize -----"; cat q5.out
if grep -q "parser.c" q5.out; then
    ok "5/7 调用者查询 -3 tokenize（命中调用方 parser.c）"
else
    bad "5/7 调用者查询 -3 tokenize（命中调用方 parser.c）"
fi

# ---- 6/7 #include 关系 -8：util.h 被 parser.c 与 util.c 包含 ----
q q6.out -8 util.h
echo "----- -8 util.h -----"; cat q6.out
if grep -q "parser.c" q6.out && grep -q "util.c" q6.out; then
    ok "6/7 include 关系查询 -8 util.h（命中包含方 parser.c + util.c）"
else
    bad "6/7 include 关系查询 -8 util.h（命中包含方 parser.c + util.c）"
fi

# ---- 7/7 增量更新 -u：向 parser.c 追加新函数后重建，新符号入索引 ----
cat >> parser.c <<'EOF'

int parse_three(const char *src) {
    return parse_twice(src) + tokenize(src);
}
EOF
if cscope -b -u -f cscope.out; then
    q q7.out -0 parse_three
    echo "----- -u 后 -0 parse_three -----"; cat q7.out
    if grep -q "parser.c" q7.out; then
        ok "7/7 增量更新 cscope -b -u（新函数 parse_three 入索引，命中 parser.c）"
    else
        bad "7/7 增量更新 cscope -b -u（新函数 parse_three 入索引，命中 parser.c）"
    fi
else
    bad "7/7 增量更新 cscope -b -u（新函数 parse_three 入索引，命中 parser.c）"
fi

echo "TEST SUMMARY: $n_pass passed, $n_fail failed"
[ "$n_fail" -eq 0 ] || exit 1
exit 0
