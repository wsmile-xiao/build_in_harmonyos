#!/bin/sh
# test_package/test.sh — urlview/1e 消费者行为测试：真跑包里的 urlview 二进制，逐条比对输出。
#
# 用法：sh test.sh <urlview 可执行绝对路径> <包根目录>
#   由 test_package/conanfile.py 的 test() 在 conanrun env 下驱动
#   （PATH 与 LD_LIBRARY_PATH 已带上包自身的 bin/ 与依赖 ncurses/6.5 的运行面）。
#
# 走的是 urlview.c:425 `if(getenv("URLVIEW_DEBUG") || !isatty(1))` 这条无头分支：
# 只抽取、把 URL 逐条打到 stdout、return 0 —— 不碰 /dev/tty、不开 curses 屏，
# 因此在无头构建机上可重复。下面每条期望值都是先在同一台机器上实测取回的
# （上游对这段没有任何自动化用例），不是照正则猜的。
#
# 断言计数由本脚本自己累加并在末尾打印 "urlview consumer assertions: N"；
# 任一条不符即 exit 1 ⇒ conanfile.py 的 self.run() 直接抛，等于"退出码"这一维也钉死。
set -u

URLVIEW=${1:?usage: test.sh <urlview-binary> <package-folder>}
PKG=${2:?usage: test.sh <urlview-binary> <package-folder>}

# 夹具与输出落在唯一临时目录里，绝不写进 archives/ 树：写进 test_package 目录会被
# git 当新文件收走，归档里混进运行时杂件是 CI 硬拦截项（R10）。
# 构建主机（鸿蒙 PC）的 /tmp 是**只读**的，mktemp 只能靠 TMPDIR；TMPDIR 缺失或不可写时
# 退回 $HOME/tmp —— 同样在 archives/ 之外，且拿不到目录就直接红牌退出，不静默降级。
WD=$(mktemp -d 2>/dev/null)
if [ ! -d "$WD" ]; then
    mkdir -p "$HOME/tmp" 2>/dev/null
    WD=$(mktemp -d "$HOME/tmp/urlview-test.XXXXXX" 2>/dev/null)
fi
if [ ! -d "$WD" ]; then
    echo "FATAL: mktemp -d failed (TMPDIR=${TMPDIR:-unset}, HOME=$HOME)" >&2
    exit 3
fi
trap 'rm -rf "$WD"' EXIT HUP INT TERM

# 每次调用都把 HOME 钉在这个空目录：urlview 启动时读 $HOME/.urlview，
# 构建机上这个文件在不在，会改写 REGEXP 与 COMMAND ⇒ 不隔离就没有确定性。
mkdir -p "$WD/home" || exit 3

checks=0
fails=0

note_fail() {
    echo "FAIL: $*" >&2
    fails=$((fails + 1))
}

# run_case <用例名> <期望 stdout 各行...> -- <输入各行...>
# 以「文件参数」形态调用 urlview，断言 rc==0 且 stdout（含 stderr 合并）逐字节等于期望。
run_case() {
    name=$1
    shift
    in_file="$WD/$name.in"
    exp_file="$WD/$name.exp"
    out_file="$WD/$name.out"
    : > "$in_file"
    : > "$exp_file"

    while [ "$1" != "--" ]; do
        printf '%s\n' "$1" >> "$exp_file"
        shift
    done
    shift
    while [ "$#" -gt 0 ]; do
        printf '%s\n' "$1" >> "$in_file"
        shift
    done

    env HOME="$WD/home" "$URLVIEW" "$in_file" > "$out_file" 2>&1
    rc=$?
    checks=$((checks + 1))
    if [ "$rc" -ne 0 ]; then
        note_fail "$name: urlview exited rc=$rc (expect 0)"
    fi
    checks=$((checks + 1))
    if ! cmp -s "$out_file" "$exp_file"; then
        note_fail "$name: stdout mismatch"
        echo "--- expected [$name] ---" >&2
        cat "$exp_file" >&2
        echo "--- got [$name] ---" >&2
        cat "$out_file" >&2
    fi
}

# ---- 10 次真运行 ----------------------------------------------------------
# 覆盖 6 种 scheme（http/https/ftp/gopher/gemini/mailto）、www2. 形态、同一行两 URL、
# 句末点号裁剪、括号包裹右括号裁剪、无 URL 空输出。
run_case one \
    'https://example.com/a' -- \
    'see https://example.com/a now'

run_case multi \
    'http://a.example/x' \
    'ftp://b.example/y' \
    'gemini://c.example/z' \
    'mailto:d@example.com' -- \
    'http://a.example/x' \
    'ftp://b.example/y' \
    'gemini://c.example/z' \
    'mailto:d@example.com'

# www2.example.org 这种「www 后紧跟数字」的形态必须整段抽出（含 host 前缀、不补 scheme）
run_case www \
    'www2.example.org/page' -- \
    'visit www2.example.org/page for info'

# gopher:// 与 gemini:// 同族，缺一条就会漏掉非 http 系的 scheme 表
run_case gopher \
    'gopher://g.example/1search' -- \
    'gopher://g.example/1search'

# 句末标点在默认 REGEXP 的收尾字符类里，必须被裁掉
run_case trim \
    'https://example.com/x' -- \
    'trailing period: https://example.com/x.'

# 同一行两个 URL：按出现顺序各出一条
run_case two \
    'https://one.example' \
    'https://two.example' -- \
    'two on one line https://one.example and https://two.example'

# 包裹在括号里时右括号也要裁掉
run_case paren \
    'https://example.com/p' -- \
    'link (https://example.com/p) ok'

# 负例：没有 URL 的输入必须什么都不输出（非 tty 分支直接 return 0）
run_case nourl -- \
    'no urls at all here'

# stdin 形态（`urlview -`）：上游 README 与 .builds 冒烟都走文件参数，
# 从标准输入读是另一条独立代码路径，单列。
printf '%s\n' 'stdin https://s.example/q end' > "$WD/stdin.in"
printf '%s\n' 'https://s.example/q' > "$WD/stdin.exp"
env HOME="$WD/home" "$URLVIEW" - < "$WD/stdin.in" > "$WD/stdin.out" 2>&1
rc=$?
checks=$((checks + 1))
if [ "$rc" -ne 0 ]; then
    note_fail "stdin: urlview exited rc=$rc (expect 0)"
fi
checks=$((checks + 1))
if ! cmp -s "$WD/stdin.out" "$WD/stdin.exp"; then
    note_fail "stdin: stdout mismatch"
    echo "--- expected [stdin] ---" >&2
    cat "$WD/stdin.exp" >&2
    echo "--- got [stdin] ---" >&2
    cat "$WD/stdin.out" >&2
fi

# 负例：文件不存在。上游语义是 warn 到 stderr 后继续、整体仍 rc=0，
# 这里把它当**特征**钉住（不是期望它失败），改了就该被发现。
env HOME="$WD/home" "$URLVIEW" "$WD/no-such-file" >/dev/null 2> "$WD/missing.err"
rc=$?
checks=$((checks + 1))
if [ "$rc" -ne 0 ]; then
    note_fail "missing-file: urlview exited rc=$rc (upstream warns and still exits 0)"
fi
checks=$((checks + 1))
if ! grep -q 'No such file or directory' "$WD/missing.err"; then
    note_fail "missing-file: stderr lacks the warn line"
    cat "$WD/missing.err" >&2
fi

# ---- 5 条安装面断言 ------------------------------------------------------
for rel in bin/urlview bin/url_handler.sh share/man/man1/urlview.1 etc/urlview.conf; do
    checks=$((checks + 1))
    if [ ! -f "$PKG/$rel" ]; then
        note_fail "missing installed file: $rel"
    fi
done

# url_handler.sh 的解释器必须是 /bin/sh：鸿蒙 PC 上没有 FHS 解释器
# （/bin/bash、/usr/bin/python3 一律 MISSING，只有 /bin/sh=toybox ash），
# 上游本身就是 #!/bin/sh，装成别的就跑不动。
checks=$((checks + 1))
shebang=$(head -n 1 "$PKG/bin/url_handler.sh")
if [ "$shebang" != '#!/bin/sh' ]; then
    note_fail "url_handler.sh shebang is [$shebang] (expect [#!/bin/sh])"
fi

# ---- 判决 ---------------------------------------------------------------
echo "urlview consumer assertions: $checks"
if [ "$fails" -ne 0 ]; then
    echo "urlview consumer tests: FAIL ($fails of $checks assertions)" >&2
    exit 1
fi
echo "urlview consumer tests: PASS ($checks assertions)"
